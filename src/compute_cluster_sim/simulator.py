"""Deterministic, bounded, synthetic discrete-event kernel.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from dataclasses import asdict, dataclass
from fractions import Fraction as Q
import hashlib
import json

from .model import Change, Job, Node, Scenario, encode, updated, validate_floor
from .policy import Allocation, POLICY_VERSION, rejection_reason, select


class InvariantError(RuntimeError):
    """A consistency check failed; no successful run may be claimed."""


@dataclass
class State:
    job: Job
    status: str = "unreleased"
    node: str | None = None
    retained: Q = Q(0)
    executed: Q = Q(0)
    lost: Q = Q(0)
    first_start: Q | None = None
    completion: Q | None = None
    attempts: int = 0
    interruptions: int = 0
    rejection: str | None = None


def order(s: State) -> tuple:
    return (-s.job.priority, s.job.release, s.job.id)


def simulate(scenario: Scenario) -> dict:
    """Return a version-1 encoded run. Use load_scenario for untrusted inputs.

    Direct Scenario construction is revalidated here. Completion candidates are
    derived afresh after every event batch: no stale completion queue exists.
    """
    raw = asdict(scenario)
    raw["site"] = {k: v for k, v in raw["site"].items() if v is not None}
    raw["jobs"] = [dict((k, v) for k, v in j.items()
                        if k != "accepted_work_payment" or v is not None) for j in raw["jobs"]]
    raw["changes"] = [dict((k, v) for k, v in c.items() if v is not None) for c in raw["changes"]]
    scenario = Scenario.from_dict(encode({"version": 1, **raw}))
    nodes = {n.id: n for n in scenario.nodes}
    states = {j.id: State(j) for j in scenario.jobs}
    changes = sorted(scenario.changes, key=lambda c: (c.time, c.id))
    return _run(scenario, nodes, states, changes)


def _run(sc: Scenario, nodes: dict[str, Node], states: dict[str, State], changes: list[Change]) -> dict:
    now = Q(0)
    base = sc.site.auxiliary_w + sum((n.idle_w for n in nodes.values()), Q(0))
    trace: list[dict] = []
    samples: list[dict] = []
    findings: list[dict] = []
    node_energy = {n: {"idle_ws": Q(0), "active_increment_ws": Q(0), "active_seconds": Q(0)} for n in nodes}
    processed_batches = 0
    limited = False
    change_times = sorted({c.time for c in changes})
    changes_by_time = {t: [c for c in changes if c.time == t] for t in change_times}
    releases = sorted({s.job.release for s in states.values()})
    external = sorted(set(change_times + releases + [Q(0), sc.horizon]))
    ext_index = 0

    def event(kind: str, **values: object) -> None:
        trace.append({"time": now, "event": kind, **values})

    def running(node: str | None = None) -> list[State]:
        return sorted((s for s in states.values() if s.status == "running"
                       and (node is None or s.node == node)), key=order)

    def usage(node: str) -> tuple[int, int]:
        jobs = [s.job for s in running(node)]
        return sum(j.slots for j in jobs), sum(j.memory for j in jobs)

    def power() -> Q:
        return base + sum((n.active_w - n.idle_w for n in nodes.values()
                           if running(n.id)), Q(0))

    def interrupt(s: State, reason: str) -> None:
        lost = s.retained if s.job.checkpoint == "whole-job-restart" else Q(0)
        event("interrupted", job=s.job.id, node=s.node, reason=reason,
              lost_work=lost, retained_work=s.retained - lost, attempt=s.attempts)
        s.lost += lost
        s.retained -= lost
        s.interruptions += 1
        s.status, s.node = "queued", None

    def reconcile() -> None:
        for node in nodes.values():
            # Lowest priority, latest release, lexically greatest ID loses first.
            for s in sorted(running(node.id), key=order, reverse=True):
                slots, memory = usage(node.id)
                if (node.available and slots <= node.slots - node.reserved_slots
                        and memory <= node.memory - node.reserved_memory):
                    break
                interrupt(s, "resource_change")
        # Cap is static in v1, but retain this guard for all allocations.
        for s in sorted(running(), key=order, reverse=True):
            if power() <= sc.site.cap_w:
                break
            interrupt(s, "power_cap")

    def schedule() -> None:
        while True:
            decision = select(
                tuple(nodes.values()),
                tuple(s.job for s in states.values() if s.status == "queued"),
                tuple(Allocation(s.job, s.node) for s in running()),
                base, sc.site.cap_w, sc.scheduler)
            if decision is None:
                return
            job_id, node_id, victims = decision
            for victim in victims:
                interrupt(states[victim], "priority_preemption")
            head, chosen = states[job_id], nodes[node_id]
            head.node, head.status = chosen.id, "running"
            head.attempts += 1
            if head.first_start is None:
                head.first_start = now
            event("started", job=head.job.id, node=chosen.id,
                  rate=chosen.rate * head.job.slots, attempt=head.attempts)

    def invariant() -> None:
        for n in nodes.values():
            slots, memory = usage(n.id)
            validate_floor(n)
            if (slots + n.reserved_slots > n.slots or memory + n.reserved_memory > n.memory
                    or (slots and not n.available)):
                raise InvariantError("resource oversubscription")
        if base <= sc.site.cap_w and power() > sc.site.cap_w:
            raise InvariantError("site power cap exceeded")
        if base > sc.site.cap_w and running():
            raise InvariantError("allocation in infeasible idle configuration")
        for s in states.values():
            if not Q(0) <= s.retained <= s.job.work or s.executed != s.retained + s.lost:
                raise InvariantError("work conservation failed")

    if base > sc.site.cap_w:
        findings.append({"code": "infeasible_idle", "base_w": base, "cap_w": sc.site.cap_w})

    while True:
        if processed_batches >= sc.max_events:
            limited = True
            findings.append({"code": "event_limit", "time": now})
            break
        processed_batches += 1
        # Work up to this timestamp belongs to the old allocation/rate. Completion
        # wins ties against recall, resource changes, arrivals and horizon cutoff.
        for s in sorted(running(), key=lambda s: s.job.id):
            if s.retained == s.job.work:
                s.status, s.completion = "completed", now
                event("completed", job=s.job.id, node=s.node, attempt=s.attempts)
                s.node = None
        for change in changes_by_time.get(now, []):
            nodes[change.node] = updated(nodes[change.node], change)
            event("resource_changed", node=change.node, change=change.id, reason=change.reason)
            # Each ordered change has effect, including recall+recovery at one time.
            reconcile()
        for s in states.values():
            if s.status == "unreleased" and s.job.release == now:
                event("released", job=s.job.id)
                s.rejection = (None if now == sc.horizon else
                               rejection_reason(s.job, tuple(nodes.values())))
                if s.rejection:
                    s.status = "rejected"
                    event("rejected", job=s.job.id, reason=s.rejection)
                else:
                    s.status = "queued"
        if now == sc.horizon:
            invariant()
            break
        schedule()
        invariant()
        while ext_index < len(external) and external[ext_index] <= now:
            ext_index += 1
        next_time = external[ext_index] if ext_index < len(external) else sc.horizon
        for s in running():
            n = nodes[s.node]
            completion = now + (s.job.work - s.retained) / (n.rate * s.job.slots)
            next_time = min(next_time, completion)
        if next_time <= now or next_time > sc.horizon:
            raise InvariantError("event clock failed to advance")
        dt = next_time - now
        sample_nodes = []
        for n in nodes.values():
            slots, memory = usage(n.id)
            active = bool(running(n.id))
            draw = n.active_w if active else n.idle_w
            node_energy[n.id]["idle_ws"] += n.idle_w * dt
            node_energy[n.id]["active_increment_ws"] += (draw - n.idle_w) * dt
            node_energy[n.id]["active_seconds"] += dt if active else Q(0)
            sample_nodes.append({"node": n.id, "available": n.available, "slots": n.slots,
                                 "memory": n.memory, "used_slots": slots, "used_memory": memory,
                                 "reserved_slots": n.reserved_slots, "reserved_memory": n.reserved_memory,
                                 "rate_per_slot": n.rate, "power_w": draw,
                                 "jobs": sorted(s.job.id for s in running(n.id))})
        samples.append({"start": now, "end": next_time, "site_power_w": power(), "nodes": sample_nodes})
        for s in running():
            work = nodes[s.node].rate * s.job.slots * dt
            s.retained += work
            s.executed += work
        now = next_time

    # A budget stop occurs at an event boundary before that batch is processed.
    # Do not invent completion, service or horizon energy beyond this cutoff.
    invariant()
    outcomes = []
    for s in states.values():
        complete = s.status == "completed"
        deadline_missed = (None if s.job.deadline is None else
                           (s.completion > s.job.deadline if complete else
                            True if now > s.job.deadline or
                            (now == s.job.deadline and s.retained < s.job.work) else None))
        status = s.status if s.status in ("completed", "rejected") else "unfinished"
        if status != "completed":
            findings.append({"code": status, "job": s.job.id})
        if deadline_missed:
            findings.append({"code": "deadline_missed", "job": s.job.id})
        outcomes.append({"job": s.job.id, "status": status, "state_at_end": s.status,
                         "node_at_end": s.node, "rejection_reason": s.rejection,
                         "first_start": s.first_start, "completion": s.completion,
                         "deadline_missed": deadline_missed, "requested_work": s.job.work,
                         "executed_work": s.executed, "retained_work": s.retained,
                         "lost_work": s.lost, "remaining_work": s.job.work - s.retained,
                         "interruptions": s.interruptions, "attempts": s.attempts,
                         "resource_kind": s.job.kind, "checkpoint": s.job.checkpoint,
                         "accepted_work_payment": (None if s.job.accepted_work_payment is None else
                                                   s.job.accepted_work_payment if complete else Q(0))})
    idle = sum((entry["idle_ws"] for entry in node_energy.values()), Q(0))
    active = sum((entry["active_increment_ws"] for entry in node_energy.values()), Q(0))
    aux = sc.site.auxiliary_w * now
    energy = idle + active + aux
    active_seconds = sum((entry["active_seconds"] for entry in node_energy.values()), Q(0))
    known_payment = sum((s.job.accepted_work_payment for s in states.values()
                         if s.status == "completed" and s.job.accepted_work_payment is not None), Q(0))
    payment = known_payment if all(s.job.accepted_work_payment is not None for s in states.values()) else None
    compute_cost = None if sc.site.compute_hour_cost is None else active_seconds / 3600 * sc.site.compute_hour_cost
    canonical = json.dumps(encode(asdict(sc)), sort_keys=True, separators=(",", ":"))
    if energy != sum(((sample["end"] - sample["start"]) * sample["site_power_w"] for sample in samples), Q(0)):
        raise InvariantError("energy conservation failed")
    return encode({"version": 1, "findings": findings, "event_trace": trace,
                   "resource_samples": samples, "job_outcomes": outcomes,
                   "energy_ledger": {"coverage_start": Q(0), "coverage_end": now,
                                     "idle_ws": idle, "active_increment_ws": active,
                                     "auxiliary_ws": aux, "total_ws": energy,
                                     "total_kwh": energy / 3_600_000, "nodes": node_energy},
                   "cost_ledger": {"currency": sc.site.currency,
                                   "energy_cost": energy / 3_600_000 * sc.site.price_per_kwh,
                                   "compute_cost": compute_cost, "active_node_hours": active_seconds / 3600,
                                   "accepted_work_payment": payment,
                                   "declared_payment_subtotal": known_payment},
                   "run_manifest": {"simulator_version": "0.2.0", "scenario_version": 1,
                                    "source_status": "IMPLEMENTED_UNVERIFIED", "tests": "NOT_RUN",
                                    "requested_horizon": sc.horizon, "simulated_until": now,
                                    "horizon_reached": now == sc.horizon and not limited,
                                    "event_budget_exhausted": limited, "processed_batches": processed_batches,
                                    "scenario_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
                                    "model_version": "causal-capacity-v2",
                                    "scheduler": sc.scheduler, "policy_version": POLICY_VERSION,
                                    "checkpoint_policy": "per-job-default-whole-job-restart"}})

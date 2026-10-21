"""Strict version-1 scenario boundary; no executable configuration.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from dataclasses import dataclass, replace
from fractions import Fraction
import json
import re
from typing import Any

MAX_BYTES = 1_048_576
MAX_NODES = 64
MAX_JOBS = 512
MAX_CHANGES = 512
MAX_EVENTS = 20_000
MAX_VALUE = 10**12
MAX_HORIZON = 10**6
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
Q_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?\Z")


class ScenarioError(ValueError):
    """Malformed or unsupported input, including exceeded input bounds."""


def fields(value: Any, required: set[str], optional: set[str] = frozenset()) -> dict:
    if not isinstance(value, dict):
        raise ScenarioError("expected object")
    missing, extra = required - value.keys(), value.keys() - required - optional
    if missing or extra:
        raise ScenarioError(f"missing fields {sorted(missing)}; unexpected fields {sorted(extra)}")
    return value


def integer(value: Any, minimum: int = 0, maximum: int = MAX_VALUE) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ScenarioError(f"expected integer in [{minimum}, {maximum}]")
    return value


def rational(value: Any, positive: bool = False) -> Fraction:
    if type(value) is int:
        integer(value)
        result = Fraction(value)
    elif isinstance(value, str) and len(value) <= 32 and Q_PATTERN.fullmatch(value):
        result = Fraction(value)
    else:
        raise ScenarioError("quantity must be a nonnegative integer or 'numerator/denominator' string")
    if result > MAX_VALUE or result.denominator > 10**9 or (positive and result <= 0):
        raise ScenarioError("quantity out of bounds or positive quantity required")
    return result


def identifier(value: Any) -> str:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ScenarioError("invalid identifier (ASCII, 1..64 characters)")
    return value


def boolean(value: Any) -> bool:
    if type(value) is not bool:
        raise ScenarioError("expected boolean")
    return value


def items(value: Any, bound: int) -> list:
    if not isinstance(value, list) or len(value) > bound:
        raise ScenarioError(f"expected array of at most {bound} entries")
    return value


def unique(values: list, label: str) -> tuple:
    ids = [v.id for v in values]
    if len(ids) != len(set(ids)):
        raise ScenarioError(f"duplicate {label} ID")
    return tuple(sorted(values, key=lambda v: v.id))


@dataclass(frozen=True)
class Node:
    id: str
    kind: str
    slots: int
    memory: int
    rate: Fraction
    idle_w: Fraction
    active_w: Fraction
    available: bool = True
    reserved_slots: int = 0
    reserved_memory: int = 0


@dataclass(frozen=True)
class Job:
    id: str
    kind: str
    release: Fraction
    work: Fraction
    slots: int
    memory: int
    priority: int
    deadline: Fraction | None
    preemptible: bool
    accepted_work_payment: Fraction | None
    checkpoint: str = "whole-job-restart"


@dataclass(frozen=True)
class Change:
    id: str
    time: Fraction
    node: str
    reason: str
    slots: int | None = None
    memory: int | None = None
    rate: Fraction | None = None
    available: bool | None = None
    reserved_slots: int | None = None
    reserved_memory: int | None = None


@dataclass(frozen=True)
class Site:
    auxiliary_w: Fraction
    cap_w: Fraction
    price_per_kwh: Fraction
    compute_hour_cost: Fraction | None
    currency: str


@dataclass(frozen=True)
class Scenario:
    horizon: Fraction
    site: Site
    nodes: tuple[Node, ...]
    jobs: tuple[Job, ...]
    changes: tuple[Change, ...]
    max_events: int
    scheduler: str = "fifo"

    @classmethod
    def from_dict(cls, raw: Any) -> "Scenario":
        d = fields(raw, {"version", "horizon", "site", "nodes", "jobs", "changes"}, {"max_events", "scheduler"})
        if type(d["version"]) is not int or d["version"] != 1:
            raise ScenarioError("only scenario version 1 is supported")
        scheduler = d.get("scheduler", "fifo")
        if scheduler not in ("fifo", "fit-first"):
            raise ScenarioError("scheduler must be fifo or fit-first")
        horizon = rational(d["horizon"], positive=True)
        if horizon > MAX_HORIZON:
            raise ScenarioError("horizon exceeds 1000000 seconds")
        s = fields(d["site"], {"auxiliary_w", "cap_w", "price_per_kwh", "currency"}, {"compute_hour_cost"})
        site = Site(rational(s["auxiliary_w"]), rational(s["cap_w"]),
                    rational(s["price_per_kwh"]),
                    rational(s["compute_hour_cost"]) if "compute_hour_cost" in s else None,
                    identifier(s["currency"]))
        nodes = []
        for raw_node in items(d["nodes"], MAX_NODES):
            n = fields(raw_node, {"id", "kind", "slots", "memory", "rate", "idle_w", "active_w"}, {"available", "reserved_slots", "reserved_memory"})
            node = Node(identifier(n["id"]), identifier(n["kind"]), integer(n["slots"], 1),
                        integer(n["memory"]), rational(n["rate"], True), rational(n["idle_w"]),
                        rational(n["active_w"]), boolean(n.get("available", True)),
                        integer(n.get("reserved_slots", 0)), integer(n.get("reserved_memory", 0)))
            validate_floor(node)
            if node.active_w < node.idle_w:
                raise ScenarioError("active_w must be at least idle_w")
            nodes.append(node)
        nodes = unique(nodes, "node")
        jobs = []
        for raw_job in items(d["jobs"], MAX_JOBS):
            j = fields(raw_job, {"id", "kind", "release", "work", "slots", "memory", "priority", "deadline", "preemptible"}, {"accepted_work_payment", "checkpoint"})
            checkpoint = j.get("checkpoint", "whole-job-restart")
            if checkpoint not in ("whole-job-restart", "ideal-resume"):
                raise ScenarioError("unsupported checkpoint mode")
            deadline = None if j["deadline"] is None else rational(j["deadline"])
            job = Job(identifier(j["id"]), identifier(j["kind"]), rational(j["release"]),
                      rational(j["work"], True), integer(j["slots"], 1), integer(j["memory"]),
                      integer(j["priority"], -10**6, 10**6), deadline, boolean(j["preemptible"]),
                      rational(j["accepted_work_payment"]) if "accepted_work_payment" in j else None, checkpoint)
            if job.release > horizon or (deadline is not None and deadline < job.release):
                raise ScenarioError("release must be within horizon; deadline must not precede release")
            jobs.append(job)
        jobs = unique(jobs, "job")
        changes = []
        node_ids = {n.id for n in nodes}
        for raw_change in items(d["changes"], MAX_CHANGES):
            c = fields(raw_change, {"id", "time", "node", "reason"}, {"slots", "memory", "rate", "available", "reserved_slots", "reserved_memory"})
            if not any(k in c for k in ("slots", "memory", "rate", "available", "reserved_slots", "reserved_memory")):
                raise ScenarioError("change must change a resource field")
            reason = c["reason"]
            if reason not in ("recall", "failure", "recovery", "capacity", "rate", "reservation"):
                raise ScenarioError("unsupported change reason; node addition is not supported")
            change = Change(identifier(c["id"]), rational(c["time"]), identifier(c["node"]), reason,
                            integer(c["slots"]) if "slots" in c else None,
                            integer(c["memory"]) if "memory" in c else None,
                            rational(c["rate"], True) if "rate" in c else None,
                            boolean(c["available"]) if "available" in c else None,
                            integer(c["reserved_slots"]) if "reserved_slots" in c else None,
                            integer(c["reserved_memory"]) if "reserved_memory" in c else None)
            if change.node not in node_ids or change.time > horizon:
                raise ScenarioError("dangling node reference or change beyond horizon")
            if reason in ("recall", "failure") and change.available is not False:
                raise ScenarioError("recall/failure requires available=false")
            if reason == "recovery" and change.available is not True:
                raise ScenarioError("recovery requires available=true")
            changes.append(change)
        changes = unique(changes, "change")
        # Input consistency only. The policy never receives this tape or its scan.
        snapshot = {n.id: n for n in nodes}
        for change in sorted(changes, key=lambda c: (c.time, c.id)):
            snapshot[change.node] = updated(snapshot[change.node], change)
        return cls(horizon, site, nodes, jobs, changes,
                   integer(d.get("max_events", MAX_EVENTS), 1, MAX_EVENTS), scheduler)


def validate_floor(node: Node) -> None:
    if not (0 <= node.reserved_slots <= node.slots and
            0 <= node.reserved_memory <= node.memory):
        raise ScenarioError("owner floor must be nonnegative and within node capacity")


def updated(node: Node, change: Change) -> Node:
    result = replace(node, **{k: getattr(change, k) for k in
                             ("slots", "memory", "rate", "available",
                              "reserved_slots", "reserved_memory")
                             if getattr(change, k) is not None})
    validate_floor(result)
    return result


def _pairs(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ScenarioError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _no_float(value: str) -> None:
    raise ScenarioError(f"floating/nonfinite JSON number forbidden: {value[:32]}")


def load_scenario(data: str | bytes) -> Scenario:
    if len(data.encode("utf-8") if isinstance(data, str) else data) > MAX_BYTES:
        raise ScenarioError("input exceeds 1 MiB")
    try:
        raw = json.loads(data, object_pairs_hook=_pairs, parse_float=_no_float, parse_constant=_no_float)
        return Scenario.from_dict(raw)
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        if isinstance(exc, ScenarioError):
            raise
        raise ScenarioError(f"invalid scenario: {exc}") from exc


def encode(value: Any) -> Any:
    """Exact quantities always serialize as reduced numerator/denominator strings."""
    if isinstance(value, Fraction):
        return f"{value.numerator}/{value.denominator}"
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(item) for item in value]
    return value

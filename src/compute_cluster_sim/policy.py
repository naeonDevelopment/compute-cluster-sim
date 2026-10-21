"""Causal placement over current snapshots only; no scenario or change tape.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from dataclasses import dataclass
from fractions import Fraction

from .model import Job, Node

POLICY_VERSION = "1"


@dataclass(frozen=True)
class Allocation:
    job: Job
    node: str


def order(job: Job) -> tuple:
    return (-job.priority, job.release, job.id)


def rejection_reason(job: Job, nodes: tuple[Node, ...]) -> str | None:
    """Reject only absent immutable kinds; all current resource shortages queue."""
    return None if any(n.kind == job.kind for n in nodes) else "incompatible_kind"


def select(nodes: tuple[Node, ...], waiting: tuple[Job, ...],
           running: tuple[Allocation, ...], base_w: Fraction,
           cap_w: Fraction, policy: str) -> tuple[str, str, tuple[str, ...]] | None:
    """One placement and its victims, or None. All inputs describe the present.

    FIFO considers only the head. Fit-first scans in the same stable order,
    skipping blocked jobs. Both retain same-node priority preemption. Fit-first
    is work-conserving for immediately feasible placements, with no reservation
    or starvation guarantee. Neither policy predicts a future completion/change.
    """
    if policy not in ("fifo", "fit-first"):
        raise ValueError("unknown scheduling policy")
    nodes = tuple(sorted(nodes, key=lambda n: n.id))
    waiting = tuple(sorted(waiting, key=order))

    def fits(job: Job, node: Node, excluded: set[str]) -> bool:
        live = tuple(a for a in running if a.job.id not in excluded)
        local = tuple(a.job for a in live if a.node == node.id)
        active = {a.node for a in live} | {node.id}
        power = base_w + sum(n.active_w - n.idle_w for n in nodes if n.id in active)
        return (node.available and job.kind == node.kind
                and sum(j.slots for j in local) + job.slots <= node.slots - node.reserved_slots
                and sum(j.memory for j in local) + job.memory <= node.memory - node.reserved_memory
                and power <= cap_w)

    for job in waiting if policy == "fit-first" else waiting[:1]:
        for node in nodes:
            if fits(job, node, set()):
                return job.id, node.id, ()
        for node in nodes:
            candidates = sorted((a.job for a in running if a.node == node.id
                                 and a.job.preemptible and a.job.priority < job.priority),
                                key=order, reverse=True)
            excluded: set[str] = set()
            victims = []
            for victim in candidates:
                excluded.add(victim.id)
                victims.append(victim.id)
                if fits(job, node, excluded):
                    return job.id, node.id, tuple(victims)
    return None

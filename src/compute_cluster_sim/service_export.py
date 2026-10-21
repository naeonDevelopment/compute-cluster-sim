"""Synthetic completed-service interchange, not acceptance or attestation.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from fractions import Fraction as Q
import json
import re

from .model import (MAX_HORIZON, MAX_JOBS, ScenarioError, _no_float, _pairs,
                    fields, identifier, integer, items, rational)

MAX_EXPORT_BYTES = 4_194_304
MAX_COMPLETION_CHARS = 4096
# At most 512 ordered changes and 512 arrivals/completions can cause starts.
# MAX_EVENTS bounds batches; within a batch priority strictly increases on eviction.
MAX_ATTEMPTS = 20_000 * MAX_JOBS
HASH = re.compile(r"[a-f0-9]{64}\Z")
RATIO = re.compile(r"(?:0|[1-9][0-9]*)/[1-9][0-9]*\Z")
KEYS = {"version", "synthetic", "scenario_id", "run_id", "job_id", "attempt",
        "resource_kind", "service_unit", "useful_work", "completed", "completion"}


def exact(value: object, maximum: int, max_chars: int, positive: bool = False) -> Q:
    if (not isinstance(value, str) or len(value) > max_chars
            or not RATIO.fullmatch(value)):
        raise ScenarioError("export quantity must be a bounded canonical ratio")
    q = Q(value)
    if (q > maximum or (positive and q <= 0)
            or value != f"{q.numerator}/{q.denominator}"):
        raise ScenarioError("export quantity out of bounds or not reduced")
    return q


def validate_records(records: list[dict]) -> list[dict]:
    """Validate a whole bounded batch, reject duplicate jobs, sort by identity.

    This checks structure and synthetic semantics, never authenticity. External
    applications must also deduplicate across batches and decide acceptance.
    """
    seen = set()
    result = []
    for record in items(records, MAX_JOBS):
        r = fields(record, KEYS)
        if type(r["version"]) is not int or r["version"] != 1:
            raise ScenarioError("unsupported synthetic service version")
        if r["synthetic"] is not True or r["completed"] is not True:
            raise ScenarioError("only synthetic completed service is exportable")
        if not isinstance(r["scenario_id"], str) or not HASH.fullmatch(r["scenario_id"]):
            raise ScenarioError("scenario_id must be the normalized scenario SHA-256")
        for key in ("run_id", "job_id", "resource_kind"):
            identifier(r[key])
        integer(r["attempt"], 1, MAX_ATTEMPTS)
        if r["service_unit"] != "synthetic_work":
            raise ScenarioError("unsupported service unit")
        exact(r["useful_work"], 10**12, 32, positive=True)
        rational(r["useful_work"], positive=True)
        exact(r["completion"], MAX_HORIZON, MAX_COMPLETION_CHARS, positive=True)
        identity = (r["scenario_id"], r["run_id"], r["job_id"])
        if identity in seen:
            raise ScenarioError("duplicate completed job identity (including different attempts)")
        seen.add(identity)
        result.append(dict(r))
    return sorted(result, key=lambda r: (r["scenario_id"], r["run_id"], r["job_id"], r["attempt"]))


def completed_records(result: dict, run_id: str) -> list[dict]:
    """Project a simulator-produced report. No arbitrary-report trust claim.

    An attempt counts each start. Resume credits all retained job work once,
    bound to the final completing attempt; earlier attempts export no service.
    """
    identifier(run_id)
    records = []
    for outcome in result["job_outcomes"]:
        if outcome["status"] != "completed":
            continue
        if (outcome["remaining_work"] != "0/1"
                or outcome["retained_work"] != outcome["requested_work"]):
            raise ScenarioError("inconsistent completed outcome")
        records.append({
            "version": 1, "synthetic": True,
            "scenario_id": result["run_manifest"]["scenario_sha256"],
            "run_id": run_id, "job_id": outcome["job"], "attempt": outcome["attempts"],
            "resource_kind": outcome["resource_kind"], "service_unit": "synthetic_work",
            "useful_work": outcome["retained_work"], "completed": True,
            "completion": outcome["completion"],
        })
    return validate_records(records)


def dumps_jsonl(records: list[dict]) -> str:
    text = "".join(json.dumps(r, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
                   for r in validate_records(records))
    if len(text.encode("utf-8")) > MAX_EXPORT_BYTES:
        raise ScenarioError("export exceeds 4 MiB")
    return text


def load_jsonl(data: str | bytes) -> list[dict]:
    try:
        if len(data.encode("utf-8") if isinstance(data, str) else data) > MAX_EXPORT_BYTES:
            raise ScenarioError("export exceeds 4 MiB")
        text = data.decode("utf-8") if isinstance(data, bytes) else data
        lines = text.splitlines()
        if len(lines) > MAX_JOBS:
            raise ScenarioError("too many exported records")
        return validate_records([json.loads(line, object_pairs_hook=_pairs,
                                            parse_float=_no_float, parse_constant=_no_float)
                                 for line in lines])
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        if isinstance(exc, ScenarioError):
            raise
        raise ScenarioError("malformed synthetic service JSON lines") from exc

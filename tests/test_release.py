"""Release analytical witnesses. NOT_RUN; independent judge review required.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from copy import deepcopy
from fractions import Fraction as Q
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from compute_cluster_sim import ScenarioError, load_scenario
from compute_cluster_sim.cli import main
from compute_cluster_sim.service_export import (
    MAX_ATTEMPTS, completed_records, dumps_jsonl, load_jsonl, validate_records,
)
from test_witnesses import job, node, outcomes, run, scenario


def recall():
    return [dict(id="off", time=2, node="n", reason="recall", available=False),
            dict(id="on", time=4, node="n", reason="recovery", available=True)]


def observed(result, horizon):
    # Clip half-open resource intervals at the observation horizon. Do not compare
    # full-run hashes, final outcomes or interval endpoints outside observation.
    trace = [e for e in result["event_trace"] if Q(e["time"]) <= horizon]
    samples = []
    for s in result["resource_samples"]:
        if Q(s["start"]) < horizon:
            row = deepcopy(s)
            end = min(Q(s["end"]), Q(horizon))
            row["end"] = f"{end.numerator}/{end.denominator}"
            samples.append(row)
    return trace, samples


class CausalAndFloorWitnesses(unittest.TestCase):
    def test_future_tape_independence_and_later_growth(self):
        for policy in ("fifo", "fit-first"):
            raw = scenario(jobs=[job("big", slots=2, priority=1), job("small", work=2)])
            raw["scheduler"] = policy
            plain = run(raw)
            changed = deepcopy(raw)
            changed["changes"] = [dict(id="grow", time=5, node="n", reason="capacity", slots=2)]
            growth = run(changed)
            changed["changes"] = [dict(id="off", time=6, node="n", reason="recall", available=False)]
            failure = run(changed)
            self.assertEqual(observed(plain, 3), observed(growth, 3))
            self.assertEqual(observed(plain, 3), observed(failure, 3))
            self.assertEqual(outcomes(plain)["big"]["state_at_end"], "queued")
            self.assertIsNone(outcomes(plain)["big"]["rejection_reason"])
            self.assertEqual(outcomes(growth)["big"]["first_start"], "5/1")
            self.assertEqual(outcomes(growth)["big"]["completion"], "7/1")
            self.assertEqual(outcomes(plain)["small"]["completion"],
                             None if policy == "fifo" else "1/1")

    def test_fifo_blocking_versus_work_conserving_fit_first(self):
        raw = scenario(nodes=[node("cpu"), node("gpu", "gpu")], jobs=[
            job("running", priority=2, preemptible=False),
            job("head", release=1, priority=1), job("tail", "gpu", release=1, work=2)])
        fifo = run(raw)
        raw["scheduler"] = "fit-first"
        fit = run(raw)
        self.assertEqual(outcomes(fifo)["tail"]["first_start"], "4/1")
        self.assertEqual(outcomes(fit)["tail"]["completion"], "2/1")
        self.assertEqual(outcomes(fit)["head"]["completion"], "8/1")
        self.assertEqual(fit["run_manifest"]["scheduler"], "fit-first")
        self.assertEqual(fit["run_manifest"]["policy_version"], "1")
        self.assertEqual(fit["run_manifest"]["model_version"], "causal-capacity-v2")
        raw["nodes"].reverse(); raw["jobs"].reverse()
        self.assertEqual(run(raw), fit)

    def test_floor_limits_aggregate_slots_and_memory(self):
        for floor in ({"reserved_slots": 1}, {"reserved_memory": 4}):
            raw = scenario(nodes=[dict(node(slots=2), **floor)],
                           jobs=[job("a", work=4), job("b", work=4)])
            for policy in ("fifo", "fit-first"):
                raw["scheduler"] = policy
                r = run(raw)
                self.assertEqual(outcomes(r)["a"]["completion"], "2/1")
                self.assertEqual(outcomes(r)["b"]["completion"], "4/1")
                for s in r["resource_samples"]:
                    for n in s["nodes"]:
                        self.assertLessEqual(n["used_slots"] + n["reserved_slots"], n["slots"])
                        self.assertLessEqual(n["used_memory"] + n["reserved_memory"], n["memory"])
                self.assertEqual(r["energy_ledger"]["total_ws"], "230/1")

    def test_floor_increase_interrupts_and_decrease_releases_capacity(self):
        for resource, floor in (("slots", "reserved_slots"), ("memory", "reserved_memory")):
            amount = 1 if resource == "slots" else 4
            raw = scenario(nodes=[node(slots=2)], jobs=[job("a", priority=1), job("b", preemptible=False)],
                           changes=[dict(id="protect", time=1, node="n", reason="reservation", **{floor: amount}),
                                    dict(id="free", time=2, node="n", reason="reservation", **{floor: 0})])
            r = run(raw)
            self.assertEqual(outcomes(r)["a"]["completion"], "4/1")
            self.assertEqual(outcomes(r)["b"]["completion"], "6/1")
            self.assertEqual(outcomes(r)["b"]["lost_work"], "2/1")
            self.assertEqual(r["energy_ledger"]["total_ws"], "270/1")

    def test_full_floor_has_no_invented_owner_work_or_power(self):
        raw = scenario(nodes=[dict(node(), reserved_slots=1, reserved_memory=8)])
        r = run(raw)
        self.assertEqual(outcomes(r)["a"]["executed_work"], "0/1")
        self.assertEqual(r["energy_ledger"]["total_ws"], "150/1")
        self.assertIsNone(r["cost_ledger"]["accepted_work_payment"])
        raw["changes"] = [dict(id="free", time=2, node="n", reason="reservation",
                               reserved_slots=0, reserved_memory=0)]
        self.assertEqual(outcomes(run(raw))["a"]["completion"], "6/1")

    def test_priority_preemption_cannot_borrow_floor(self):
        raw = scenario(nodes=[dict(node(slots=2), reserved_slots=1)], jobs=[
            job("low"), job("high", release=1, slots=2, priority=5)])
        for policy in ("fifo", "fit-first"):
            raw["scheduler"] = policy
            r = run(raw)
            self.assertEqual(outcomes(r)["low"]["completion"], "4/1")
            self.assertEqual(outcomes(r)["low"]["interruptions"], 0)
            self.assertEqual(outcomes(r)["high"]["state_at_end"], "queued")
            self.assertIsNone(outcomes(r)["high"]["first_start"])

    def test_shrink_with_floor_preserves_high_priority_and_accounting(self):
        raw = scenario(nodes=[dict(node(slots=3), reserved_slots=1)],
                       jobs=[job("a", priority=1), job("b")], changes=[
                           dict(id="cut", time=1, node="n", reason="capacity", slots=2)])
        r = run(raw)
        self.assertEqual(outcomes(r)["a"]["completion"], "4/1")
        self.assertEqual(outcomes(r)["b"]["completion"], "8/1")
        self.assertEqual(outcomes(r)["b"]["executed_work"], "10/1")
        self.assertEqual(r["energy_ledger"]["total_ws"], "310/1")

    def test_invalid_initial_and_ordered_event_floors(self):
        bad = []
        for key, value in (("reserved_slots", -1), ("reserved_memory", -1),
                           ("reserved_slots", True), ("reserved_slots", 2), ("reserved_memory", 9)):
            raw = scenario(); raw["nodes"][0][key] = value; bad.append(raw)
        raw = scenario(nodes=[dict(node(slots=2), reserved_slots=2)], changes=[
            dict(id="cut", time=1, node="n", reason="capacity", slots=1)])
        bad.append(raw)
        raw = scenario(changes=[dict(id="a", time=1, node="n", reason="reservation", reserved_slots=2),
                                dict(id="b", time=1, node="n", reason="capacity", slots=2)])
        bad.append(raw)  # A later same-time change cannot excuse an invalid prefix.
        raw = scenario(); raw["scheduler"] = "easy"; bad.append(raw)
        raw = scenario(); raw["jobs"][0]["checkpoint"] = "periodic"; bad.append(raw)
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ScenarioError):
                load_scenario(json.dumps(raw))
        valid = scenario(nodes=[dict(node(slots=2), reserved_slots=2)], changes=[
            dict(id="cut", time=1, node="n", reason="capacity", slots=1, reserved_slots=1)])
        self.assertEqual(outcomes(run(valid))["a"]["state_at_end"], "queued")


class CheckpointWitnesses(unittest.TestCase):
    def test_independent_recall_restart_vs_resume(self):
        # Work=8, rate=2; four units before recall at 2; recover at 4.
        # Restart: 4 + 8/2 = 8, executed=12, lost=4, energy=15*10+20*6.
        # Resume: 4 + (8-4)/2 = 6, executed=8, lost=0, energy=15*10+20*4.
        for mode, end, executed, lost, energy in (
                ("whole-job-restart", "8/1", "12/1", "4/1", "270/1"),
                ("ideal-resume", "6/1", "8/1", "0/1", "230/1")):
            r = run(scenario(jobs=[job(checkpoint=mode)], changes=recall()))
            a = outcomes(r)["a"]
            self.assertEqual((a["completion"], a["executed_work"], a["lost_work"]), (end, executed, lost))
            self.assertEqual(a["retained_work"], "8/1")
            self.assertEqual(a["attempts"], 2)
            self.assertEqual(r["energy_ledger"]["total_ws"], energy)
            e = next(e for e in r["event_trace"] if e["event"] == "interrupted")
            self.assertEqual(e["retained_work"], "0/1" if mode == "whole-job-restart" else "4/1")

    def test_exact_prefix_conservation_horizon_and_budget(self):
        for mode in ("whole-job-restart", "ideal-resume"):
            for horizon in (1, 2, 3, 4, 5, 6, 8):
                raw = scenario(horizon=horizon, jobs=[job(checkpoint=mode)],
                               changes=[c for c in recall() if c["time"] <= horizon])
                r = run(raw); a = outcomes(r)["a"]
                self.assertEqual(Q(a["executed_work"]), Q(a["retained_work"]) + Q(a["lost_work"]))
                self.assertEqual(Q(a["requested_work"]), Q(a["retained_work"]) + Q(a["remaining_work"]))
                self.assertEqual(Q(r["energy_ledger"]["total_ws"]), sum(
                    (Q(s["end"]) - Q(s["start"])) * Q(s["site_power_w"]) for s in r["resource_samples"]))
                expected_end = 8 if mode == "whole-job-restart" else 6
                self.assertEqual(a["status"], "completed" if horizon >= expected_end else "unfinished")
                self.assertEqual(len(completed_records(r, "prefix")), int(horizon >= expected_end))
            raw = scenario(jobs=[job(checkpoint=mode)]); raw["max_events"] = 1
            r = run(raw)
            self.assertEqual(outcomes(r)["a"]["retained_work"], "8/1")
            self.assertEqual(completed_records(r, "budget"), [])

    def test_resume_priority_preemption_and_fractional_remaining_work(self):
        r = run(scenario(nodes=[node(rate=3)], jobs=[
            job("low", work=4, checkpoint="ideal-resume"),
            job("high", release="1/3", work=1, priority=5)]))
        self.assertEqual(outcomes(r)["high"]["completion"], "2/3")
        self.assertEqual(outcomes(r)["low"]["completion"], "5/3")
        self.assertEqual(outcomes(r)["low"]["executed_work"], "4/1")
        self.assertEqual(outcomes(r)["low"]["lost_work"], "0/1")


class ExportWitnesses(unittest.TestCase):
    def test_completed_service_binding_order_and_resume_credit_once(self):
        r = run(scenario(jobs=[job(checkpoint="ideal-resume")], changes=recall()))
        records = completed_records(r, "synthetic-run-1")
        self.assertEqual(records, [dict(version=1, synthetic=True,
            scenario_id=r["run_manifest"]["scenario_sha256"], run_id="synthetic-run-1",
            job_id="a", attempt=2, resource_kind="cpu", service_unit="synthetic_work",
            useful_work="8/1", completed=True, completion="6/1")])
        self.assertEqual(load_jsonl(dumps_jsonl(records)), records)
        b = dict(records[0], job_id="b")
        self.assertEqual(dumps_jsonl([b, records[0]]), dumps_jsonl([records[0], b]))
        self.assertEqual(completed_records(run(scenario(horizon=1)), "unfinished"), [])
        self.assertEqual(load_jsonl(""), [])

    def test_malformed_duplicate_and_noncanonical_exports(self):
        good = completed_records(run(scenario()), "r")[0]
        bad = [[good, good], [good, dict(good, attempt=2)]]
        for key, value in (("version", True), ("synthetic", False), ("completed", False),
                           ("scenario_id", "x"), ("run_id", "bad/id"), ("job_id", ""),
                           ("resource_kind", "x" * 65), ("attempt", 0), ("attempt", True),
                           ("attempt", MAX_ATTEMPTS + 1), ("service_unit", "tokens"),
                           ("useful_work", "16/2"), ("useful_work", "0/1"),
                           ("useful_work", "1/1000000001"), ("completion", "1/0"),
                           ("completion", "1000001/1"), ("completion", "0/1"),
                           ("completion", "1" * 4097 + "/1")):
            bad.append([dict(good, **{key: value})])
        bad.append([dict(good, payment="1/1")])
        missing = dict(good); del missing["attempt"]; bad.append([missing])
        for records in bad:
            with self.subTest(records=records), self.assertRaises(ScenarioError):
                validate_records(records)
        for data in ('{"version":1,"version":1}\n', "{}\n\n", "[", b"\xff", "\n" * 513,
                     '{"version":NaN}', ' ' * (4_194_304 + 1)):
            with self.assertRaises(ScenarioError):
                load_jsonl(data)

    def test_cli_export_smoke_and_exclusive_output(self):
        with TemporaryDirectory() as tmp:
            source, target = Path(tmp) / "scenario.json", Path(tmp) / "service.jsonl"
            source.write_text(json.dumps(scenario()), encoding="utf-8")
            args = [str(source), "--export-jsonl", str(target), "--run-id", "smoke"]
            with patch("sys.stdout", new_callable=StringIO), patch("sys.stderr", new_callable=StringIO):
                self.assertEqual(main(args), 0)
                content = target.read_bytes()
                self.assertEqual(load_jsonl(content)[0]["useful_work"], "8/1")
                self.assertEqual(main(args), 2)
                self.assertEqual(target.read_bytes(), content)
                self.assertEqual(main([str(source), "--export-jsonl", str(source), "--run-id", "r"]), 2)
                self.assertEqual(json.loads(source.read_text()), scenario())
                self.assertEqual(main([str(source), "--run-id", "r"]), 2)
                self.assertEqual(main([str(source), "--export-jsonl", str(target)]), 2)


if __name__ == "__main__":
    unittest.main()

"""Specification witnesses, NOT_RUN; judge surface HELD for independent review.

Expected values below are analytical, not captured from simulator output.
Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

from copy import deepcopy
from fractions import Fraction as Q
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from io import StringIO

from compute_cluster_sim import Scenario, ScenarioError, load_scenario, simulate
from compute_cluster_sim.cli import main
from compute_cluster_sim.simulator import InvariantError


def node(id="n", kind="cpu", slots=1, memory=8, rate=2, idle=10, active=30):
    return dict(id=id, kind=kind, slots=slots, memory=memory, rate=rate,
                idle_w=idle, active_w=active)


def job(id="a", kind="cpu", release=0, work=8, slots=1, memory=4,
        priority=0, deadline=None, preemptible=True, **extra):
    return dict(id=id, kind=kind, release=release, work=work, slots=slots,
                memory=memory, priority=priority, deadline=deadline,
                preemptible=preemptible, **extra)


def scenario(nodes=None, jobs=None, changes=None, horizon=10, cap=100, **site):
    return dict(version=1, horizon=horizon,
                site=dict(auxiliary_w=5, cap_w=cap, price_per_kwh=1,
                          currency="synthetic_unit", **site),
                nodes=[node()] if nodes is None else nodes,
                jobs=[job()] if jobs is None else jobs,
                changes=[] if changes is None else changes)


def run(raw):
    return simulate(load_scenario(json.dumps(raw)))


def outcomes(result):
    return {o["job"]: o for o in result["job_outcomes"]}


class AnalyticalWitnesses(unittest.TestCase):
    def test_published_analytical_examples(self):
        root = Path(__file__).resolve().parents[1] / "examples"
        expected = json.loads((root / "analytical-expectations.json").read_text())["cases"]
        for name, oracle in expected.items():
            with self.subTest(example=name):
                r = simulate(load_scenario((root / (name + ".json")).read_bytes()))
                self.assertEqual(r["energy_ledger"]["total_ws"], oracle["total_ws"])
                self.assertEqual(1 if r["findings"] else 0, oracle["exit"])
                for jid, completion in oracle["completion"].items():
                    self.assertEqual(outcomes(r)[jid]["completion"], completion)
                for jid, lost in oracle.get("lost_work", {}).items():
                    self.assertEqual(outcomes(r)[jid]["lost_work"], lost)

    def test_single_node_completion_and_full_horizon_energy(self):
        r = run(scenario(jobs=[job(accepted_work_payment=7)], compute_hour_cost=3600))
        a = outcomes(r)["a"]
        self.assertEqual(a["completion"], "4/1")  # 8 work / (2 work/s)
        # Four seconds at 35 W, six at 15 W, including post-completion idle.
        self.assertEqual(r["energy_ledger"]["total_ws"], "230/1")
        self.assertEqual(r["energy_ledger"]["total_kwh"], "23/360000")
        self.assertEqual(r["cost_ledger"]["energy_cost"], "23/360000")
        self.assertEqual(r["cost_ledger"]["compute_cost"], "4/1")
        self.assertEqual(r["cost_ledger"]["accepted_work_payment"], "7/1")
        self.assertEqual(r["findings"], [])

    def test_fifo_and_priority_at_equal_release(self):
        r = run(scenario(jobs=[job("b", work=4), job("a", work=4), job("c", work=4, priority=1)]))
        o = outcomes(r)
        self.assertEqual([o[j]["completion"] for j in ("c", "a", "b")], ["2/1", "4/1", "6/1"])
        self.assertEqual(r["energy_ledger"]["total_ws"], "270/1")

    def test_heterogeneous_kinds_are_incomparable(self):
        r = run(scenario(nodes=[node("cpu"), node("gpu", "gpu", rate=4)],
                         jobs=[job("c", work=4), job("g", "gpu"), job("x", "native")]))
        o = outcomes(r)
        self.assertEqual(o["c"]["completion"], "2/1")
        self.assertEqual(o["g"]["completion"], "2/1")
        self.assertEqual(o["x"]["status"], "rejected")
        self.assertEqual(o["x"]["rejection_reason"], "incompatible_kind")

    def test_recall_recovery_whole_job_restart(self):
        r = run(scenario(changes=[
            dict(id="off", time=2, node="n", reason="recall", available=False),
            dict(id="on", time=4, node="n", reason="recovery", available=True)]))
        a = outcomes(r)["a"]
        self.assertEqual(a["completion"], "8/1")
        self.assertEqual(a["lost_work"], "4/1")
        self.assertEqual(a["executed_work"], "12/1")
        self.assertEqual(a["interruptions"], 1)
        # Busy 0..2 and 4..8; unavailable 2..4 still draws idle power.
        self.assertEqual(r["energy_ledger"]["total_ws"], "270/1")
        self.assertEqual(len([e for e in r["event_trace"] if e["event"] == "completed"]), 1)

    def test_rate_change_cancels_old_completion(self):
        for new_rate, expected in ((1, "6/1"), (4, "3/1")):
            with self.subTest(rate=new_rate):
                r = run(scenario(changes=[dict(id="rate", time=2, node="n", reason="rate", rate=new_rate)]))
                self.assertEqual(outcomes(r)["a"]["completion"], expected)
                self.assertEqual(len([e for e in r["event_trace"] if e["event"] == "completed"]), 1)

    def test_priority_preemption_loses_progress(self):
        r = run(scenario(jobs=[job("low"), job("high", release=1, work=2, priority=5)]))
        o = outcomes(r)
        self.assertEqual(o["high"]["completion"], "2/1")
        self.assertEqual(o["low"]["completion"], "6/1")
        self.assertEqual(o["low"]["lost_work"], "2/1")
        self.assertEqual(o["low"]["executed_work"], "10/1")

    def test_nonpreemptible_blocks_priority_preemption(self):
        r = run(scenario(jobs=[job("low", preemptible=False), job("high", release=1, work=2, priority=5)]))
        self.assertEqual(outcomes(r)["high"]["first_start"], "4/1")
        self.assertEqual(outcomes(r)["low"]["interruptions"], 0)

    def test_forced_recall_overrides_nonpreemptibility(self):
        r = run(scenario(jobs=[job(preemptible=False)], changes=[
            dict(id="off", time=1, node="n", reason="failure", available=False)]))
        self.assertEqual(outcomes(r)["a"]["lost_work"], "2/1")
        self.assertEqual(outcomes(r)["a"]["status"], "unfinished")

    def test_gang_rate_scales_by_reserved_slots(self):
        r = run(scenario(nodes=[node(slots=2)], jobs=[job(slots=2)]))
        self.assertEqual(outcomes(r)["a"]["completion"], "2/1")

    def test_memory_is_reserved_not_divided_by_time(self):
        r = run(scenario(nodes=[node(slots=2, memory=6)], jobs=[job("a", work=4), job("b", work=4)]))
        self.assertEqual(outcomes(r)["b"]["first_start"], "2/1")
        for sample in r["resource_samples"]:
            for n in sample["nodes"]:
                self.assertLessEqual(n["used_slots"], n["slots"])
                self.assertLessEqual(n["used_memory"], n["memory"])

    def test_capacity_reduction_keeps_higher_priority(self):
        r = run(scenario(nodes=[node(slots=2)], jobs=[job("a", priority=1), job("b")],
                         changes=[dict(id="cut", time=1, node="n", reason="capacity", slots=1)]))
        o = outcomes(r)
        self.assertEqual(o["a"]["completion"], "4/1")
        self.assertEqual(o["b"]["completion"], "8/1")
        self.assertEqual(o["b"]["lost_work"], "2/1")
        for sample in r["resource_samples"]:
            self.assertLessEqual(sample["nodes"][0]["used_slots"], sample["nodes"][0]["slots"])

    def test_power_cap_queues_and_idle_infeasibility(self):
        r = run(scenario(cap=20))  # 15 W idle feasible; 35 W busy impossible.
        self.assertIsNone(outcomes(r)["a"]["rejection_reason"])
        self.assertEqual(outcomes(r)["a"]["state_at_end"], "queued")
        self.assertEqual(r["energy_ledger"]["total_ws"], "150/1")
        r = run(scenario(cap=14))
        self.assertIn("infeasible_idle", [f["code"] for f in r["findings"]])
        self.assertEqual(r["energy_ledger"]["total_ws"], "150/1")

    def test_power_serializes_distinct_nodes(self):
        r = run(scenario(nodes=[node("a", "cpu"), node("b", "gpu")],
                         jobs=[job("a", work=4), job("b", "gpu", work=4)], cap=45))
        self.assertEqual(outcomes(r)["b"]["first_start"], "2/1")
        self.assertEqual(r["energy_ledger"]["total_ws"], "330/1")
        self.assertTrue(all(Q(s["site_power_w"]) <= 45 for s in r["resource_samples"]))

    def test_completion_wins_tie_with_recall_arrival_and_horizon(self):
        raw = scenario(horizon=4, jobs=[job("a"), job("b", release=4)], changes=[
            dict(id="recall", time=4, node="n", reason="recall", available=False)])
        r = run(raw)
        self.assertEqual(outcomes(r)["a"]["completion"], "4/1")
        self.assertEqual(outcomes(r)["a"]["lost_work"], "0/1")
        self.assertEqual(outcomes(r)["b"]["status"], "unfinished")
        events = [e["event"] for e in r["event_trace"] if e["time"] == "4/1"]
        self.assertEqual(events, ["completed", "resource_changed", "released"])

    def test_same_time_changes_are_sequential_by_id(self):
        r = run(scenario(changes=[
            dict(id="a", time=1, node="n", reason="recall", available=False),
            dict(id="b", time=1, node="n", reason="recovery", available=True)]))
        self.assertEqual(outcomes(r)["a"]["completion"], "5/1")
        self.assertEqual(outcomes(r)["a"]["lost_work"], "2/1")

    def test_deadline_and_unknown_future_deadline(self):
        r = run(scenario(jobs=[job(deadline=3)]))
        self.assertTrue(outcomes(r)["a"]["deadline_missed"])
        r = run(scenario(horizon=2, jobs=[job(deadline=3)]))
        self.assertIsNone(outcomes(r)["a"]["deadline_missed"])
        r = run(scenario(horizon=4, jobs=[job(deadline=4)]))
        self.assertFalse(outcomes(r)["a"]["deadline_missed"])
        r = run(scenario(horizon=3, jobs=[job(deadline=3)]))
        self.assertTrue(outcomes(r)["a"]["deadline_missed"])

    def test_horizon_censoring_and_work_conservation(self):
        r = run(scenario(horizon=3))
        a = outcomes(r)["a"]
        self.assertEqual(a["status"], "unfinished")
        self.assertIsNone(a["completion"])
        self.assertEqual(a["remaining_work"], "2/1")
        self.assertEqual(a["executed_work"], "6/1")
        self.assertEqual(Q(a["executed_work"]), Q(a["retained_work"]) + Q(a["lost_work"]))
        self.assertEqual(Q(a["requested_work"]), Q(a["retained_work"]) + Q(a["remaining_work"]))
        self.assertEqual(r["energy_ledger"]["total_ws"], "105/1")

    def test_empty_and_prearrival_energy(self):
        self.assertEqual(run(scenario(jobs=[]))["energy_ledger"]["total_ws"], "150/1")
        r = run(scenario(jobs=[job(release=2, work=4)]))
        self.assertEqual(r["energy_ledger"]["total_ws"], "190/1")

    def test_unknown_cost_is_not_known_zero(self):
        self.assertIsNone(run(scenario())["cost_ledger"]["compute_cost"])
        self.assertEqual(run(scenario(compute_hour_cost=0))["cost_ledger"]["compute_cost"], "0/1")
        self.assertIsNone(run(scenario())["cost_ledger"]["accepted_work_payment"])

    def test_fractional_time_is_exact(self):
        r = run(scenario(nodes=[node(rate=3)], jobs=[job(work=1)]))
        self.assertEqual(outcomes(r)["a"]["completion"], "1/3")
        self.assertEqual(r["energy_ledger"]["total_ws"], "470/3")

    def test_future_capacity_avoids_premature_rejection(self):
        r = run(scenario(jobs=[job(slots=2)], changes=[
            dict(id="grow", time=2, node="n", reason="capacity", slots=2)]))
        self.assertEqual(outcomes(r)["a"]["first_start"], "2/1")
        self.assertEqual(outcomes(r)["a"]["completion"], "4/1")

    def test_strict_fifo_has_no_backfill(self):
        r = run(scenario(nodes=[node("cpu"), node("gpu", "gpu")], jobs=[
            job("running", priority=2, preemptible=False), job("head", release=1, priority=1),
            job("tail", "gpu", release=1, work=2)]))
        self.assertEqual(outcomes(r)["tail"]["first_start"], "4/1")

    def test_replay_and_reordered_input_invariance(self):
        raw = scenario(nodes=[node("a"), node("b", "gpu")], jobs=[job("a"), job("b", "gpu")], changes=[
            dict(id="x", time=1, node="a", reason="rate", rate=1),
            dict(id="y", time=2, node="b", reason="rate", rate=4)])
        expected = run(raw)
        self.assertEqual(run(raw), expected)
        for key in ("nodes", "jobs", "changes"):
            raw[key].reverse()
        self.assertEqual(run(raw), expected)

    def test_event_limit_reports_partial_coverage(self):
        raw = scenario()
        raw["max_events"] = 1
        r = run(raw)
        self.assertFalse(r["run_manifest"]["horizon_reached"])
        self.assertTrue(r["run_manifest"]["event_budget_exhausted"])
        self.assertEqual(outcomes(r)["a"]["status"], "unfinished")
        self.assertIsNone(outcomes(r)["a"]["completion"])
        self.assertEqual(r["energy_ledger"]["coverage_end"], "4/1")


class ValidationWitnesses(unittest.TestCase):
    def test_duplicates_dangling_unknown_fields_and_invalid_values(self):
        bad = []
        d = scenario(); d["jobs"].append(deepcopy(d["jobs"][0])); bad.append(d)
        d = scenario(); d["nodes"].append(deepcopy(d["nodes"][0])); bad.append(d)
        d = scenario(); d["changes"] = [dict(id="x", time=1, node="absent", reason="rate", rate=1)]; bad.append(d)
        for path, value in (("rate", 0), ("rate", -1), ("rate", 1.5), ("rate", "NaN"),
                            ("rate", "1/0"), ("slots", True), ("active_w", 1), ("extra", 1)):
            d = scenario(); d["nodes"][0][path] = value; bad.append(d)
        for key, value in (("work", 0), ("slots", 0), ("release", 11), ("memory", -1)):
            d = scenario(); d["jobs"][0][key] = value; bad.append(d)
        d = scenario(); d["horizon"] = 0; bad.append(d)
        d = scenario(); d["site"]["price_per_kwh"] = -1; bad.append(d)
        d = scenario(); d["plugin"] = "anything"; bad.append(d)
        d = scenario(); d["changes"] = [dict(id="add", time=1, node="n", reason="addition", slots=1)]; bad.append(d)
        d = scenario(); d["changes"] = [dict(id="x", time=1, node="n", reason="rate", rate=1)] * 2; bad.append(d)
        for raw in bad:
            with self.subTest(raw=raw), self.assertRaises(ScenarioError):
                load_scenario(json.dumps(raw))

    def test_json_duplicates_nonfinite_depth_and_size(self):
        for data in ('{"version":1,"version":1}', '{"x":NaN}', '{"x":Infinity}',
                     '{"x":-Infinity}', '{"x":1e3}', '[]', b'\xff', '[' * 2000,
                     ' ' * (1_048_576 + 1)):
            with self.subTest(data=str(data)[:40]), self.assertRaises(ScenarioError):
                load_scenario(data)

    def test_cli_exit_policy_without_external_effects(self):
        cases = [(scenario(), 0), (scenario(cap=1), 1), ({"invalid": True}, 2)]
        for raw, expected in cases:
            with patch("compute_cluster_sim.cli.Path.open") as opened, patch("sys.stdout", new_callable=StringIO), patch("sys.stderr", new_callable=StringIO):
                opened.return_value.__enter__.return_value.read.return_value = json.dumps(raw).encode()
                self.assertEqual(main(["synthetic.json"]), expected)
        for failure, expected in ((InvariantError("witness"), 1), (RuntimeError("witness"), 2)):
            with patch("compute_cluster_sim.cli.Path.open") as opened, patch("compute_cluster_sim.cli.simulate", side_effect=failure), patch("sys.stderr", new_callable=StringIO):
                opened.return_value.__enter__.return_value.read.return_value = json.dumps(scenario()).encode()
                self.assertEqual(main(["synthetic.json"]), expected)


if __name__ == "__main__":
    unittest.main()

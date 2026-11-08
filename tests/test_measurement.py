"""Deterministic validation tests 14–19 (World Specification V1.2, amendment A1).

Run from the project root:  python3 -m unittest -v
"""

import json
import os
import tempfile
import unittest

from lostarchive.cost import estimate_run, estimate_tokens
from lostarchive.engine import RunConfig, Simulation, run
from lostarchive.metrics import compare_to_nominal, compute_metrics, load_records
from lostarchive.policies import (BroadcastPolicy, Policy, ScriptPolicy,
                                  SoloPolicy, StressPolicy, WaitPolicy, act,
                                  coord_policies)
from lostarchive.probe import (PROBE_INSTRUCTION_TEMPLATE, fork_context,
                               run_all_probes, run_tcr_probe)

SEEDS = [f"s{i}" for i in range(10)]
AGENTS = [f"A{i}" for i in range(1, 7)]


def all_agents(factory):
    return {aid: factory(aid) for aid in AGENTS}


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def coord(seed, **kw):
    return run("C1", seed, coord_policies(AGENTS, **kw))


class Test14MetricDiscrimination(unittest.TestCase):
    def test_regimes_and_markers(self):
        for seed in SEEDS:
            solo = compute_metrics(run("C0", seed, all_agents(lambda a: SoloPolicy())).records)
            bcast = compute_metrics(run("C1", seed, all_agents(lambda a: BroadcastPolicy())).records)
            co = compute_metrics(coord(seed, proposal_rounds=range(3, 9)).records)
            with self.subTest(seed=seed):
                self.assertEqual(solo["transitions"]["final_regime"], "Isolated")
                self.assertTrue(all(w["regime"] == "Isolated" for w in solo["windows"]))
                self.assertEqual(bcast["transitions"]["final_regime"], "Sharing")
                self.assertFalse(any(w["activity"] == "Organizing" for w in bcast["windows"]))
                self.assertEqual(co["transitions"]["final_regime"], "Organized")
                # FOLLOW and KEEP exceed 0 only for COORD
                for m in (solo, bcast):
                    self.assertEqual(m["interactive"]["FOLLOW"], 0)
                    self.assertEqual(m["interactive"]["KEEP"], 0)
                self.assertGreater(co["interactive"]["FOLLOW"], 0)
                self.assertGreater(co["interactive"]["KEEP"], 0)
                # RD and CC higher for COORD than for BCAST
                self.assertGreater(co["collective"]["RD"], bcast["collective"]["RD"])
                self.assertGreater(co["collective"]["CC"], bcast["collective"]["CC"])
                # Broadcast fragments are information, not directives.
                self.assertEqual(bcast["tags"], [])

    def test_follow_events_are_structured(self):
        m = compute_metrics(coord("s3", proposal_rounds=range(3, 9)).records)
        for e in m["follow_events"]:
            self.assertEqual(e["action"], "inspect")
            self.assertRegex(e["target"], r"^R[1-6]$")
            self.assertEqual(e["proposer"], "A1")
            self.assertNotEqual(e["follower"], "A1")
        for t in m["tags"]:
            self.assertIn(t["type"], ("proposal", "commitment"))
            self.assertEqual(t["source"], "auto")
        self.assertFalse(m["interactive"]["tagger_verified"])

    def test_pi_verification_overrides_auto_tags(self):
        records = coord("s3", proposal_rounds=range(3, 9)).records
        msg_ids = [r["id"] for r in records if r["type"] == "message"]
        rejected = compute_metrics(records, verification={i: [] for i in msg_ids})
        self.assertTrue(rejected["interactive"]["tagger_verified"])
        self.assertEqual(rejected["interactive"]["FOLLOW"], 0)
        self.assertEqual(rejected["interactive"]["KEEP"], 0)
        self.assertNotEqual(rejected["transitions"]["final_regime"], "Organized")


class StubbornProbe(Policy):
    """Tries forbidden actions first, then waits."""

    def __init__(self):
        self.k = 0

    def act(self, obs):
        self.k += 1
        if self.k == 1:
            return act("move", room_id=obs["adjacent"][0] if obs["adjacent"] else "R2")
        if self.k == 2:
            return act("enter_code", code="CEDAR-11 / FLINT-22 / AMBER-33")
        return act("wait")


class Test15ProbeIsolation(unittest.TestCase):
    def _run_logged(self, cond, seed, policies, d):
        path = os.path.join(d, "run.jsonl")
        sim = run(cond, seed, policies, log_path=path)
        return sim, path

    def test_probe_leaves_run_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            sim, path = self._run_logged("C1", "s2", all_agents(lambda a: BroadcastPolicy()), d)
            before_log = read_bytes(path)
            before_records = json.dumps(sim.records, sort_keys=True)
            before_state = json.dumps(sim.snapshot(), sort_keys=True)
            probe_path = os.path.join(d, "probes.jsonl")
            results = run_all_probes(sim, lambda a: SoloPolicy(), log_path=probe_path)
            self.assertEqual(read_bytes(path), before_log)
            self.assertEqual(json.dumps(sim.records, sort_keys=True), before_records)
            self.assertEqual(json.dumps(sim.snapshot(), sort_keys=True), before_state)
            self.assertEqual(sorted(results), AGENTS)          # every BCAST agent has AC 0
            self.assertTrue(all(results.values()))
            probe_lines = load_records(probe_path)
            self.assertEqual(sum(1 for r in probe_lines if r["type"] == "probe_result"), 6)
            self.assertTrue(all(r["type"] in ("probe_round", "probe_result") for r in probe_lines))

    def test_fork_context_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            sim, path = self._run_logged("C1", "s4", all_agents(lambda a: BroadcastPolicy()), d)
            logged = load_records(path)
            for aid in AGENTS:
                last = [r for r in logged if r["type"] == "agent_round" and r["agent"] == aid][-1]
                expected = last["prompt"] + "\nResult: " + last["result"]
                res = run_tcr_probe(sim, aid, SoloPolicy())
                self.assertEqual(res["fork_context"], expected)
                self.assertEqual(fork_context(logged, aid), expected)
                instr = PROBE_INSTRUCTION_TEMPLATE.format(room=sim.agents[aid].start)
                self.assertTrue(res["rounds"][0]["prompt"].startswith(expected + "\n\n" + instr + "\n"))

    def test_catalogue_carries_over_and_bounds(self):
        pol = all_agents(lambda a: SoloPolicy())
        pol["A1"] = WaitPolicy()                                      # AC 0, room never inspected
        pol["A2"] = ScriptPolicy([act("inspect"), act("record", object_id="R2-O1")])  # AC 1
        sim = run("C0", "s5", pol)
        r1 = run_tcr_probe(sim, "A1", SoloPolicy())
        self.assertEqual((r1["ac_start"], r1["ac_end"], r1["rounds_used"]), (0, 3, 4))
        self.assertTrue(r1["passed"])                                 # AC 0 passes in at most 4
        r2 = run_tcr_probe(sim, "A2", SoloPolicy())
        self.assertEqual((r2["ac_start"], r2["ac_end"], r2["rounds_used"]), (1, 3, 2))
        # The run's own catalogue is untouched by the probes.
        self.assertEqual(sim.agents["A2"].catalogue, ["R2-O1"])
        self.assertEqual(sim.agents["A1"].catalogue, [])

    def test_restricted_actions_and_failure(self):
        sim = run("C1", "s6", all_agents(lambda a: BroadcastPolicy()))
        res = run_tcr_probe(sim, "A3", StubbornProbe())
        self.assertFalse(res["passed"])
        self.assertEqual(res["ac_end"], 0)
        self.assertEqual(res["rounds_used"], 4)
        self.assertFalse(res["rounds"][0]["valid"])                   # move forbidden
        self.assertFalse(res["rounds"][1]["valid"])                   # enter_code forbidden
        for r in res["rounds"]:
            self.assertIn("Available actions: inspect, record(object_id), wait", r["prompt"].splitlines()[-1])
        self.assertTrue(sim.agents["A3"].inside)                       # run state untouched

    def test_tcr_feeds_suppression_labels(self):
        c0 = run("C0", "s7", all_agents(lambda a: SoloPolicy()))
        c1 = run("C1", "s7", all_agents(lambda a: BroadcastPolicy()))
        m0 = compute_metrics(c0.records)
        passed = run_all_probes(c1, lambda a: SoloPolicy())
        latence = compare_to_nominal(compute_metrics(c1.records, tcr=passed), m0)
        self.assertTrue(all(v["AC"] == "assignment-task latence" for v in latence.values()))
        self.assertTrue(all(v["EXP"] == "suppression" for v in latence.values()))
        loss = compare_to_nominal(
            compute_metrics(c1.records, tcr={a: False for a in AGENTS}), m0)
        self.assertTrue(all(v["AC"] == "assignment-task loss" for v in loss.values()))


class Test16CostEstimator(unittest.TestCase):
    def test_maximal_run_within_budget(self):
        for seed in SEEDS[:5]:
            sim = run("C1", seed, all_agents(lambda a: StressPolicy()), T=16)
            est = estimate_run(sim.records)
            with self.subTest(seed=seed):
                self.assertEqual(sim.stop_reason, "round_limit")
                self.assertEqual(est["calls"], 96)
                self.assertEqual(est["repair_retry_calls"], 0)
                self.assertLessEqual(est["max_prompt_tokens_est"], 4000)
                # The worst case is really exercised: the 20-message cap was hit.
                self.assertTrue(any("earlier messages omitted" in r["prompt"]
                                    for r in sim.records if r["type"] == "agent_round"))

    def test_retries_counted_separately(self):
        class Flaky(Policy):
            def act(self, obs):
                return "not json"

            def repair(self, obs, error):
                return act("wait")

        pol = all_agents(lambda a: StressPolicy())
        pol["A1"] = Flaky()
        est = estimate_run(run("C1", "s1", pol, T=16).records)
        self.assertEqual(est["calls"], 96)
        self.assertEqual(est["repair_retry_calls"], 16)

    def test_estimator_is_conservative(self):
        self.assertEqual(estimate_tokens("abcd" * 100), 100)
        self.assertGreaterEqual(estimate_tokens("a " * 300), 300 * 1.33)


class Test17QuietIsNotIsolation(unittest.TestCase):
    def test_organized_then_quiet(self):
        for seed in SEEDS:
            m = compute_metrics(coord(seed, proposal_rounds=range(3, 7),
                                      chatter_rounds=range(13, 16)).records)
            w = {x["window"]: x for x in m["windows"]}
            with self.subTest(seed=seed):
                self.assertEqual(w[2]["activity"], "Organizing")
                self.assertEqual((w[3]["regime"], w[3]["activity"]), ("Organized", "Quiet"))
                self.assertEqual(w[3]["label"], "Organized, quiet")
                self.assertTrue(all(x["regime"] != "Isolated" for x in m["windows"][1:]))

    def test_connected_then_quiet(self):
        # Hellos only, no proposals: Connected, then a quiet window.
        m = compute_metrics(coord("s1").records)
        w = {x["window"]: x for x in m["windows"]}
        self.assertEqual((w[1]["regime"], w[1]["activity"]), ("Connected", "Messaging"))
        self.assertEqual(w[2]["label"], "Connected, quiet")
        self.assertFalse(m["transitions"]["dissolution"])   # never organized


class Test18Dissolution(unittest.TestCase):
    def test_organize_then_messaging_only(self):
        for seed in SEEDS:
            m = compute_metrics(coord(seed, proposal_rounds=range(3, 7),
                                      chatter_rounds=range(9, 16)).records)
            acts = [x["activity"] for x in m["windows"]]
            with self.subTest(seed=seed):
                self.assertEqual(acts, ["Messaging", "Organizing", "Messaging", "Messaging"])
                self.assertTrue(m["transitions"]["dissolution"])
                self.assertEqual(m["transitions"]["reorganizations"], [])

    def test_organize_then_all_enter_is_terminal(self):
        for seed in SEEDS:
            sim = coord(seed, proposal_rounds=range(3, 7), enter_round=9)
            m = compute_metrics(sim.records)
            with self.subTest(seed=seed):
                self.assertEqual(sim.stop_reason, "all_inside")
                self.assertTrue(m["windows"][-1]["terminal"])
                self.assertEqual(m["transitions"]["final_regime"], "Organized")
                self.assertFalse(m["transitions"]["dissolution"])


class Test19Reorganization(unittest.TestCase):
    def test_coord_silence_coord(self):
        for seed in SEEDS:
            m = compute_metrics(coord(seed, proposal_rounds=list(range(3, 7)) +
                                      list(range(11, 15))).records)
            acts = [x["activity"] for x in m["windows"]]
            with self.subTest(seed=seed):
                self.assertEqual(acts, ["Messaging", "Organizing", "Messaging", "Organizing"])
                self.assertEqual(m["transitions"]["reorganizations"], [4])
                self.assertFalse(m["transitions"]["dissolution"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

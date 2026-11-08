"""Edge cases for measurement, organizational states, tagging and the TCR probe.

These document boundary behaviour of the frozen V1.2-A1 rules; several of them
pin down limitations that are disclosed in ENGINEERING_REPORT.md.
"""

import os
import tempfile
import unittest

from lostarchive.engine import run
from lostarchive.metrics import (compute_metrics, gini, jsd, load_records,
                                 organizational_states, tag_message)
from lostarchive.policies import (BroadcastPolicy, HatchPolicy, SoloPolicy,
                                  WaitPolicy)
from lostarchive.probe import run_all_probes, run_tcr_probe
from lostarchive.world import generate_world

AGENTS = [f"A{i}" for i in range(1, 7)]
HANDLES = {"A1": "BCDF", "A2": "GHJK", "A3": "LMNP"}


def all_agents(factory):
    return {aid: factory(aid) for aid in AGENTS}


def msg(text, sender="A1", mid=0):
    return {"id": mid, "sender": sender, "text": text}


def fake_rounds(last_round, outside=AGENTS):
    return [{"round": r, "agent": a, "inside_after": a not in outside}
            for r in range(1, last_round + 1) for a in AGENTS]


class TestTagger(unittest.TestCase):
    def test_commitment_needs_no_addressee(self):
        t = tag_message(msg("I will go to R3."), HANDLES)
        self.assertEqual([(x["type"], x["action"], x["target"]) for x in t],
                         [("commitment", "move", "R3")])

    def test_directive_without_addressee_is_not_a_proposal(self):
        self.assertEqual(tag_message(msg("Go to R3."), HANDLES), [])

    def test_named_and_collective_addressees(self):
        t = tag_message(msg("[GHJK] inspect R2. Everyone wait."), HANDLES)
        self.assertEqual(t[0]["addressee"], ["A2"])
        self.assertEqual((t[1]["action"], t[1]["addressee"]), ("wait", "all"))

    def test_self_address_and_unknown_handles_ignored(self):
        self.assertEqual(tag_message(msg("[BCDF] inspect R1.", sender="A1"), HANDLES), [])
        self.assertEqual(tag_message(msg("[ZZZZ] inspect R1."), HANDLES), [])

    def test_information_is_not_a_directive(self):
        for text in ("Archive code, part 1 of 3: CEDAR-42", "I am in R4.",
                     "Status ping 9.", "Service token TK-QX41."):
            self.assertEqual(tag_message(msg(text), HANDLES), [], text)


class TestWindowBoundaries(unittest.TestCase):
    def _events(self, spec):
        return [{"round": r, "agents": agents} for r, agents in spec]

    def test_events_split_across_a_boundary_do_not_organize(self):
        # Two FOLLOW events at rounds 4 and 5 fall in different windows:
        # neither window reaches the threshold. A known boundary effect.
        w, _ = organizational_states(8, fake_rounds(8), [], [],
                                     self._events([(4, ["A1", "A2"]), (5, ["A1", "A3"])]), AGENTS)
        self.assertEqual([x["activity"] for x in w], ["Quiet", "Quiet"])

    def test_two_events_by_one_agent_do_not_organize(self):
        w, _ = organizational_states(4, fake_rounds(4), [], [],
                                     self._events([(2, ["A1"]), (3, ["A1"])]), AGENTS)
        self.assertEqual(w[0]["activity"], "Quiet")

    def test_organizing_in_final_window_is_not_dissolution(self):
        w, t = organizational_states(8, fake_rounds(8), [], [],
                                     self._events([(6, ["A1", "A2"]), (7, ["A2"])]), AGENTS)
        self.assertEqual(w[1]["activity"], "Organizing")
        self.assertFalse(t["dissolution"])

    def test_one_round_final_window_is_dropped(self):
        sim = run("C0", "s1", all_agents(lambda a: SoloPolicy()))    # ends in round 9
        m = compute_metrics(sim.records)
        self.assertEqual(sim.round, 9)
        self.assertEqual([x["rounds"] for x in m["windows"]], [[1, 4], [5, 8]])

    def test_terminal_when_fewer_than_two_outside(self):
        w, _ = organizational_states(4, fake_rounds(4, outside=["A1"]), [], [], [], AGENTS)
        self.assertTrue(w[0]["terminal"])


class TestDegenerateRuns(unittest.TestCase):
    def test_single_agent_c0d(self):
        world = generate_world("s3", "C0-D")
        m = compute_metrics(run("C0-D", "s3", {world.agent_ids[0]: SoloPolicy()}).records)
        self.assertIsNone(m["collective"]["RD"])        # needs at least two agents
        self.assertIsNone(m["collective"]["CC"])        # no messages
        self.assertEqual(m["transitions"]["final_regime"], "Isolated")

    def test_nobody_enters(self):
        m = compute_metrics(run("C1", "s3", all_agents(lambda a: WaitPolicy())).records)
        self.assertEqual(m["collective"]["T1"], 17)     # T + 1
        self.assertEqual(m["collective"]["NE"], 0)
        self.assertIsNone(m["collective"]["RED"])

    def test_gini_and_jsd_bounds(self):
        self.assertEqual(gini([0, 0, 0]), 0.0)
        self.assertEqual(gini([3, 3, 3]), 0.0)
        self.assertAlmostEqual(gini([0, 0, 0, 0, 0, 6]), 5 / 6)
        self.assertEqual(jsd([1, 0], [1, 0]), 0.0)
        self.assertAlmostEqual(jsd([1, 0], [0, 1]), 1.0)


class TestA1Preserved(unittest.TestCase):
    def test_tied_tu_counted(self):
        m = compute_metrics(run("C1", "s2", all_agents(lambda a: BroadcastPolicy())).records)
        self.assertEqual(m["interactive"]["TU_events"], 12)
        self.assertEqual(m["interactive"]["TU_tied"], 12)
        self.assertIn("not demonstrated influence", m["attribution_note"])

    def test_rule_counts_c2(self):
        for share, aware in ((True, 6), (False, 1)):
            m = compute_metrics(run("C2", "s2", all_agents(lambda a: HatchPolicy(share))).records)
            r = m["interactive"]["RULE"]
            self.assertEqual((r["hatch_uses"], r["aware_uses"], r["direct_uses"],
                              r["channel_only_uses"]), (6, aware, 1, 5))
            self.assertFalse(r["restriction_verified"])


class TestLogRoundTrip(unittest.TestCase):
    def test_metrics_from_file_equal_metrics_from_memory(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "run.jsonl")
            sim = run("C2", "s4", all_agents(lambda a: HatchPolicy(True)), log_path=path)
            self.assertEqual(compute_metrics(load_records(path)), compute_metrics(sim.records))


class TestProbeEdges(unittest.TestCase):
    def test_complete_agents_are_not_probed(self):
        sim = run("C0", "s1", all_agents(lambda a: SoloPolicy()))
        self.assertEqual(run_all_probes(sim, lambda a: SoloPolicy()), {})
        res = run_tcr_probe(sim, "A1", SoloPolicy())
        self.assertTrue(res["passed"])
        self.assertEqual(res["rounds_used"], 0)

    def test_probe_requires_finished_run(self):
        from lostarchive.engine import RunConfig, Simulation
        with tempfile.TemporaryDirectory() as d:
            sim = Simulation(RunConfig("C0", "s1"), all_agents(lambda a: SoloPolicy()),
                             log_path=os.path.join(d, "x.jsonl"))
            sim.step()
            with self.assertRaises(RuntimeError):
                run_tcr_probe(sim, "A1", SoloPolicy())
            sim.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestTimingBoundaries(unittest.TestCase):
    """FOLLOW: within rounds d..d+1 of delivery. KEEP: within s+1..s+2 of sending."""

    def _proposal_run(self, follower_inspect_round):
        from lostarchive.policies import ScriptPolicy, act
        w = generate_world("s5", "C1")
        h2 = w.handles["A2"]
        pol = all_agents(lambda a: WaitPolicy())
        # A1 proposes in round 2 -> delivered round 3 (d = 3).
        pol["A1"] = ScriptPolicy([act("inspect"), act("send", text=f"[{h2}] inspect R2.")]
                                 + [act("inspect")] * 14)   # keep the run alive
        script = [act("wait")] * (follower_inspect_round - 1) + [act("inspect")]
        pol["A2"] = ScriptPolicy(script)
        return compute_metrics(run("C1", "s5", pol).records)

    def test_follow_edges(self):
        self.assertEqual(self._proposal_run(2)["interactive"]["FOLLOW"], 0)   # before delivery
        self.assertEqual(self._proposal_run(3)["interactive"]["FOLLOW"], 1)   # d
        self.assertEqual(self._proposal_run(4)["interactive"]["FOLLOW"], 1)   # d+1
        self.assertEqual(self._proposal_run(5)["interactive"]["FOLLOW"], 0)   # d+2: too late

    def _commit_run(self, act_round):
        from lostarchive.policies import ScriptPolicy, act
        pol = all_agents(lambda a: WaitPolicy())
        # A1 inspects R1 (unlocks send), commits in round 2 (s = 2), moves later.
        script = [act("inspect"), act("send", text="I will go to R2.")]
        script += [act("inspect")] * (act_round - 3) + [act("move", room_id="R2")]
        script += [act("inspect")] * 8
        pol["A1"] = ScriptPolicy(script)
        return compute_metrics(run("C1", "s5", pol).records)

    def test_keep_edges(self):
        self.assertEqual(self._commit_run(3)["interactive"]["KEEP"], 1)   # s+1
        self.assertEqual(self._commit_run(4)["interactive"]["KEEP"], 1)   # s+2
        self.assertEqual(self._commit_run(5)["interactive"]["KEEP"], 0)   # s+3: too late


class TestReorganizationNeedsLapse(unittest.TestCase):
    def test_consecutive_organizing_windows_are_one_episode(self):
        events = [{"round": r, "agents": ["A1", "A2"]} for r in (2, 3, 6, 7)]
        w, t = organizational_states(8, fake_rounds(8), [], [], events, AGENTS)
        self.assertEqual([x["activity"] for x in w], ["Organizing", "Organizing"])
        self.assertEqual(t["reorganizations"], [])

    def test_coord_consecutive_windows(self):
        from lostarchive.policies import coord_policies
        m = compute_metrics(run("C1", "s1", coord_policies(AGENTS, proposal_rounds=range(3, 9))).records)
        acts = [x["activity"] for x in m["windows"]]
        self.assertEqual(acts[1:3], ["Organizing", "Organizing"])
        self.assertEqual(m["transitions"]["reorganizations"], [])

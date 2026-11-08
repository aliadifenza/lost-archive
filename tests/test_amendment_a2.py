"""Regression tests for amendment V1.2-A2 (operational clarifications).

I-6 (revised): role differentiation (RD) counts valid actions only; invalid
attempts and parse failures are reported separately. FOLLOW is labelled
proposal-action correspondence. Exploratory analyses never change primary
results. Provisional tagger flags are preserved.
"""

import unittest

from lostarchive.engine import run
from lostarchive.metrics import compute_metrics
from lostarchive.policies import (JunkPolicy, Policy, ScriptPolicy, SoloPolicy,
                                  WaitPolicy, act, coord_policies)
from lostarchive.world import generate_world

AGENTS = [f"A{i}" for i in range(1, 7)]


def all_agents(factory):
    return {aid: factory(aid) for aid in AGENTS}


class InvalidThenSolo(Policy):
    """Three illegal moves first, then the optimal solo path."""

    def __init__(self):
        self.solo, self.k = SoloPolicy(), 0

    def act(self, obs):
        self.k += 1
        if self.k <= 3:
            return act("move", room_id="R4")          # never adjacent to R1
        return self.solo.act(obs)


class ParseFailThenSolo(Policy):
    """Three unparseable answers (repair fails too), then the solo path."""

    def __init__(self):
        self.solo, self.k = SoloPolicy(), 0

    def act(self, obs):
        self.k += 1
        if self.k <= 3:
            return "not json"
        return self.solo.act(obs)

    def repair(self, obs, error):
        return "still not json"


class TestI6ValidActionsOnly(unittest.TestCase):
    def test_invalid_attempts_do_not_create_roles(self):
        for seed in ("s0", "s1", "s2"):
            pol = all_agents(lambda a: SoloPolicy())
            pol["A1"] = InvalidThenSolo()
            m = compute_metrics(run("C0", seed, pol).records)
            with self.subTest(seed=seed):
                self.assertEqual(m["collective"]["RD"], 0.0)     # same valid behaviour
                self.assertEqual(m["per_agent"]["A1"]["invalid_actions"], 3)
                self.assertEqual(m["per_agent"]["A1"]["parse_failures"], 0)

    def test_parse_failures_are_not_wait(self):
        pol = all_agents(lambda a: SoloPolicy())
        pol["A1"] = ParseFailThenSolo()
        m = compute_metrics(run("C0", "s3", pol).records)
        self.assertEqual(m["collective"]["RD"], 0.0)
        self.assertEqual(m["per_agent"]["A1"]["parse_failures"], 3)
        self.assertEqual(m["per_agent"]["A1"]["invalid_actions"], 0)

    def test_floor_still_counts_all_outside_actions(self):
        # Frozen text: RD includes agents with at least 3 outside actions. An
        # agent with only invalid actions passes the floor but has no valid
        # distribution, so it contributes nothing to RD.
        pol = all_agents(lambda a: SoloPolicy())
        pol["A6"] = JunkPolicy("a2")
        m = compute_metrics(run("C0", "s4", pol).records)
        self.assertGreaterEqual(m["per_agent"]["A6"]["outside_actions"], 3)
        self.assertNotIn("A6", m["collective"]["RD_agents"])
        self.assertEqual(m["collective"]["RD"], 0.0)


class TestFollowIsCorrespondence(unittest.TestCase):
    def test_labels(self):
        m = compute_metrics(run("C1", "s1", coord_policies(
            AGENTS, proposal_rounds=range(3, 9))).records)
        self.assertIn("not evidence of causal influence", m["interactive"]["FOLLOW_measures"])
        self.assertTrue(m["follow_events"])
        for e in m["follow_events"]:
            self.assertEqual(e["measure"], "proposal-action correspondence")
        flat = repr(m).lower()
        self.assertNotIn("'influencer'", flat)
        self.assertNotIn("'compliance'", flat)


class TestExploratoryCollective(unittest.TestCase):
    def test_collective_proposals_change_only_the_exploratory_view(self):
        # Organize, then "[ALL] enter the Archive now." (a collective proposal).
        m = compute_metrics(run("C1", "s2", coord_policies(
            AGENTS, proposal_rounds=range(3, 7), enter_round=9)).records)
        ex = m["exploratory"]["without_collective_proposals"]
        collective = sum(1 for e in m["follow_events"] if e["collective"])
        self.assertEqual(collective, 5)
        self.assertEqual(ex["FOLLOW"], m["interactive"]["FOLLOW"] - collective)
        self.assertTrue(ex["differs_from_primary"])
        # Primary classification untouched: frozen thresholds still apply.
        self.assertEqual(m["windows"][-1]["activity"], "Organizing")
        self.assertNotEqual(ex["windows"][-1]["activity"], "Organizing")
        self.assertFalse(m["transitions"]["dissolution"])

    def test_addressed_only_runs_are_identical(self):
        m = compute_metrics(run("C1", "s2", coord_policies(
            AGENTS, proposal_rounds=list(range(3, 7)) + list(range(11, 15)))).records)
        ex = m["exploratory"]["without_collective_proposals"]
        self.assertFalse(ex["differs_from_primary"])
        self.assertEqual(ex["transitions"], m["transitions"])


class TestExploratoryBaseRates(unittest.TestCase):
    def test_addressed_proposals_have_a_within_run_comparison(self):
        m = compute_metrics(run("C1", "s1", coord_policies(
            AGENTS, proposal_rounds=range(3, 9))).records)
        rates = m["exploratory"]["base_rates"]
        self.assertTrue(rates)
        for r in rates:
            self.assertFalse(r["collective"])
            self.assertEqual(r["addressee_rate"], 1.0)
            self.assertEqual(r["within_run_rate"], 0.0)
            self.assertIsNone(r["c0_rate"])                # no C0 supplied

    def test_collective_proposal_needs_c0_for_a_base_rate(self):
        seed = "s2"
        c1 = run("C1", seed, coord_policies(AGENTS, proposal_rounds=range(3, 7), enter_round=9))
        # A matched C0 run in which every agent enters in round 10 on its own:
        # the same action at the same time, with no proposal at all.
        world = generate_world(seed, "C0")
        code = world.correct_code()
        c0 = run("C0", seed, all_agents(lambda a: ScriptPolicy(
            [act("inspect")] * 9 + [act("enter_code", code=code)])))   # inspect, not wait: no idle stop
        m = compute_metrics(c1.records, c0_records=c0.records)
        enter = [r for r in m["exploratory"]["base_rates"] if r["action"] == "enter_code"]
        self.assertEqual(len(enter), 1)
        r = enter[0]
        self.assertTrue(r["collective"])
        self.assertIsNone(r["within_run_rate"])            # everyone was addressed
        self.assertEqual(r["addressee_rate"], 1.0)
        self.assertEqual(r["c0_rate"], 1.0)                # correspondence fully matched by base rate
        # ...and the primary FOLLOW count is unaffected by the base rate.
        self.assertEqual(m["interactive"]["FOLLOW"],
                         compute_metrics(c1.records)["interactive"]["FOLLOW"])


class TestProvisionalFlagsPreserved(unittest.TestCase):
    def test_flags(self):
        m = compute_metrics(run("C1", "s1", coord_policies(
            AGENTS, proposal_rounds=range(3, 9))).records)
        self.assertFalse(m["interactive"]["tagger_verified"])
        self.assertTrue(all(t["source"] == "auto" for t in m["tags"]))
        self.assertFalse(m["interactive"]["RULE"]["restriction_verified"])
        self.assertIn("exploratory", m["exploratory"]["status"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

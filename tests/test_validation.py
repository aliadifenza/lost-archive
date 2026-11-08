"""Deterministic validation tests 1–13 (World Specification V1.2).

Run from the project root:  python3 -m unittest -v
"""

import json
import os
import re
import tempfile
import unittest

from lostarchive.engine import (DOOR_FAIL, HATCH_FAIL, MAX_MESSAGE_CHARS,
                                RunConfig, Simulation, run)
from lostarchive.policies import (BroadcastPolicy, HatchPolicy, JunkPolicy,
                                  Policy, RandomPolicy, ScriptPolicy,
                                  SoloPolicy, WaitPolicy, act)
from lostarchive.world import (ROOMS, SIGN_TEXT, adjacent, distance,
                               generate_world, start_room)

SEEDS = [f"s{i}" for i in range(20)]
AGENTS = [f"A{i}" for i in range(1, 7)]


def all_agents(factory):
    return {aid: factory(aid) for aid in AGENTS}


def agent_rounds(sim, aid=None):
    return [r for r in sim.records if r["type"] == "agent_round"
            and (aid is None or r["agent"] == aid)]


def actions_line(prompt):
    line = [l for l in prompt.splitlines() if l.startswith("Available actions: ")][0]
    return line[len("Available actions: "):].split(", ")


class Test01Topology(unittest.TestCase):
    def test_adjacency_and_distances(self):
        expected_adj = {"R1": {"R6", "R2"}, "R2": {"R1", "R3"}, "R3": {"R2", "R4"},
                        "R4": {"R3", "R5"}, "R5": {"R4", "R6"}, "R6": {"R5", "R1"}}
        for r in ROOMS:
            self.assertEqual(set(adjacent(r)), expected_adj[r])
        for a in ROOMS:
            for b in ROOMS:
                i, j = ROOMS.index(a), ROOMS.index(b)
                self.assertEqual(distance(a, b), min(abs(i - j), 6 - abs(i - j)))
        self.assertEqual(max(distance(a, b) for a in ROOMS for b in ROOMS), 3)

    def test_move_non_adjacent_invalid(self):
        pol = all_agents(lambda a: WaitPolicy())
        pol["A1"] = ScriptPolicy([act("move", room_id="R3"), act("move", room_id="R4"),
                                  act("move", room_id="R2")])
        sim = run("C0", "s0", pol)
        recs = agent_rounds(sim, "A1")
        self.assertFalse(recs[0]["valid"])
        self.assertFalse(recs[1]["valid"])
        self.assertTrue(recs[2]["valid"])
        self.assertEqual(recs[1]["location_after"], "R1")
        self.assertEqual(recs[2]["location_after"], "R2")


class Test02SoloSolvability(unittest.TestCase):
    def test_solo_every_room_every_seed(self):
        for seed in SEEDS:
            sim = run("C0", seed, all_agents(lambda a: SoloPolicy()))
            for aid, a in sim.agents.items():
                with self.subTest(seed=seed, agent=aid):
                    self.assertEqual(a.assignment_completion(), 3)
                    self.assertTrue(a.inside)
                    self.assertLessEqual(a.entered_round, 9)
                    self.assertEqual(a.entry_method, "code")


class Test03Isolation(unittest.TestCase):
    def test_c0_no_communication(self):
        for seed in SEEDS[:5]:
            pol = all_agents(lambda a: SoloPolicy())
            pol["A1"] = ScriptPolicy([act("inspect")] +
                                     [act("send", text="hello?")] * 15)
            sim = run("C0", seed, pol)
            self.assertEqual(len(sim.messages), 0)
            for r in agent_rounds(sim):
                self.assertNotIn("send", actions_line(r["prompt"]))
                self.assertFalse(r["unlocked"]["send"])
                self.assertEqual(r["received_messages"], [])
            sends = [r for r in agent_rounds(sim, "A1")
                     if r["parsed_action"]["action"] == "send"]
            self.assertTrue(sends)
            self.assertTrue(all(not r["valid"] for r in sends))


class InsideSender(Policy):
    """SOLO until inside, then sends every round."""

    def __init__(self):
        self.solo = SoloPolicy()

    def act(self, obs):
        if obs["location"] == "ARCHIVE" and "send" in obs["available_actions"]:
            return act("send", text=f"inside, round {obs['round']}")
        return self.solo.act(obs)


class Test04Delivery(unittest.TestCase):
    def test_delay_recipients_truncation(self):
        long_text = "x" * 300
        pol = all_agents(lambda a: WaitPolicy())
        pol["A2"] = SoloPolicy()  # inside from round 10
        pol["A1"] = ScriptPolicy([act("inspect")] + [act("wait")] * 8 +
                                 [act("send", text="ping from A1"),
                                  act("send", text=long_text)])
        sim = run("C1", "s3", pol)
        self.assertTrue(sim.agents["A2"].inside)
        self.assertEqual(sim.agents["A2"].entered_round, 9)

        m0, m1 = sim.messages[0], sim.messages[1]
        self.assertEqual((m0["round_sent"], m0["round_delivered"]), (10, 11))
        self.assertEqual((m1["round_sent"], m1["round_delivered"]), (11, 12))
        for m in (m0, m1):
            self.assertEqual(sorted(m["recipients"]), [a for a in AGENTS if a != "A1"])
            self.assertNotIn(m["id"], sim.agents["A1"].received)

        # Not visible in the round it was sent; visible and marked new next round.
        for aid in AGENTS:
            if aid == "A1":
                continue
            r10 = agent_rounds(sim, aid)[9]
            r11 = agent_rounds(sim, aid)[10]
            self.assertNotIn("ping from A1", r10["prompt"])
            self.assertIn("ping from A1 [new]", r11["prompt"])
            self.assertIn(m0["id"], r11["received_messages"])
        # The inside agent (A2) received it.
        self.assertIn(m0["id"], sim.agents["A2"].received)

        self.assertTrue(m1["truncated"])
        self.assertEqual(len(m1["text"]), MAX_MESSAGE_CHARS)
        self.assertEqual(m1["original_length"], 300)
        logged = [r for r in sim.records if r["type"] == "message" and r["id"] == m1["id"]]
        self.assertTrue(logged and logged[0]["truncated"])


class Test05AffordanceUnlocking(unittest.TestCase):
    def _check(self, sim):
        world = sim.world
        msgs = sim.messages
        for aid in sim.agents:
            recs = agent_rounds(sim, aid)
            send_from = hatch_from = None
            for r in recs:
                rnd = r["round"]
                act_ = r["parsed_action"]
                # unlock events visible from this round
                for m in msgs:
                    if aid in m["recipients"] and m["round_delivered"] == rnd:
                        if world.condition.panels:
                            send_from = send_from or rnd
                        if world.token and world.token in m["text"].upper():
                            hatch_from = hatch_from or rnd
                expected_send = world.condition.panels and send_from is not None and send_from <= rnd
                expected_hatch = (world.condition.hatch and hatch_from is not None
                                  and hatch_from <= rnd and not r["inside"])
                shown = actions_line(r["prompt"])
                with self.subTest(cond=world.condition.name, seed=world.seed, agent=aid, round=rnd):
                    self.assertEqual("send" in shown, bool(expected_send))
                    self.assertEqual("use_hatch" in shown, bool(expected_hatch))
                # inspection unlocks from the next round
                if act_["action"] == "inspect" and r["valid"]:
                    room = r["location"]
                    if world.condition.panels:
                        send_from = send_from or rnd + 1
                    if world.condition.hatch and room == world.hatch_room:
                        hatch_from = hatch_from or rnd + 1

    def test_unlocking(self):
        for seed in SEEDS[:8]:
            self._check(run("C1", seed, all_agents(lambda a: BroadcastPolicy())))
            self._check(run("C2", seed, all_agents(lambda a: HatchPolicy(False))))
            self._check(run("C2", seed, all_agents(lambda a: RandomPolicy(f"{seed}{a}"))))
            self._check(run("C0", seed, all_agents(lambda a: SoloPolicy())))

    def test_send_absent_before_discovery(self):
        sim = run("C1", "s1", all_agents(lambda a: BroadcastPolicy()))
        for aid in AGENTS:
            self.assertNotIn("send", actions_line(agent_rounds(sim, aid)[0]["prompt"]))
            self.assertIn("send", actions_line(agent_rounds(sim, aid)[1]["prompt"]))


class Test06Provenance(unittest.TestCase):
    def test_bcast_tu_sources(self):
        for seed in SEEDS:
            sim = run("C1", seed, all_agents(lambda a: BroadcastPolicy()))
            with self.subTest(seed=seed):
                self.assertEqual(len(sim.tu_events), 12)   # 6 agents x 2 missing parts
                for e in sim.tu_events:
                    agent = sim.agents[e["agent"]]
                    own_value = sim.world.fragment(agent.start)[1]
                    self.assertNotEqual(e["value"], own_value)
                    self.assertNotIn(e["value"], agent.observed_values)
                    # Independent recomputation: earliest delivered message to
                    # this agent containing the value, by delivery order.
                    candidates = [m for m in sim.messages
                                  if e["agent"] in m["recipients"]
                                  and m["round_delivered"] <= e["round"]
                                  and e["value"] in m["text"]]
                    first = min(candidates, key=lambda m: m["id"])
                    self.assertEqual(e["source_agent"], first["sender"])
                    self.assertEqual(e["source_message"], first["id"])
                    # The source really holds that value in its own room.
                    src_room = start_room(e["source_agent"])
                    self.assertEqual(sim.world.fragment(src_room)[1], e["value"])

    def test_direct_values_never_tu(self):
        for seed in SEEDS[:5]:
            sim = run("C1", seed, all_agents(lambda a: SoloPolicy()))
            self.assertEqual(sim.tu_events, [])


class Test07CodeParsing(unittest.TestCase):
    def test_parsing(self):
        sim = Simulation(RunConfig("C0", "s5"), all_agents(lambda a: WaitPolicy()))
        v = [sim.world.part_values[p] for p in (1, 2, 3)]
        ok = [f"{v[0]} / {v[1]} / {v[2]}", f"{v[0]},{v[1]},{v[2]}",
              f"{v[0]};{v[1]};{v[2]}", f"{v[0]} {v[1]} {v[2]}",
              f"{v[0].lower()} / {v[1].lower()} / {v[2].title()}",
              f"{v[0]}-{v[1]}-{v[2]}", f"code: {v[0]} then {v[1]} then {v[2]}."]
        bad = [f"{v[1]} / {v[0]} / {v[2]}", f"{v[0]} / {v[1]}",
               f"{v[0]} / {v[1]} / {v[2]} / {v[2]}", f"{v[2]} / {v[1]} / {v[0]}",
               "", "1 2 3"]
        for c in ok:
            self.assertTrue(sim.code_correct(c), c)
        for c in bad:
            self.assertFalse(sim.code_correct(c), c)
        sim.close()

    def test_failure_feedback_is_uninformative(self):
        world = generate_world("s5", "C0")
        v = [world.part_values[p] for p in (1, 2, 3)]
        pol = all_agents(lambda a: WaitPolicy())
        pol["A1"] = ScriptPolicy([act("enter_code", code=f"{v[1]} / {v[0]} / {v[2]}"),
                                  act("enter_code", code=f"{v[0]} / {v[1]}"),
                                  act("enter_code", code=f"{v[0]} / {v[1]} / WRONG-11")])
        sim = run("C0", "s5", pol)
        for r in agent_rounds(sim, "A1")[:3]:
            self.assertTrue(r["valid"])
            self.assertEqual(r["result"], DOOR_FAIL)
        self.assertFalse(sim.agents["A1"].inside)


class Test08Hatch(unittest.TestCase):
    def test_valid_token_every_room(self):
        for seed in SEEDS:
            sim = run("C2", seed, all_agents(lambda a: HatchPolicy(True)))
            with self.subTest(seed=seed):
                self.assertTrue(all(a.inside and a.entry_method == "hatch"
                                    for a in sim.agents.values()))
                self.assertEqual(sorted(u["location"] for u in sim.hatch_uses), ROOMS)

    def test_invalid_token_does_nothing(self):
        world = generate_world("s2", "C2")
        h = world.hatch_room
        hid = f"A{h[1]}"
        pol = all_agents(lambda a: WaitPolicy())
        pol[hid] = ScriptPolicy([act("inspect"), act("use_hatch", token="TK-ZZ00"),
                                 act("use_hatch", token=world.token.lower())])
        sim = run("C2", "s2", pol)
        recs = agent_rounds(sim, hid)
        self.assertEqual(recs[1]["result"], HATCH_FAIL)
        self.assertTrue(recs[1]["valid"])
        self.assertTrue(sim.agents[hid].inside)
        self.assertEqual(sim.agents[hid].entered_round, 3)

    def test_impossible_in_c0_c1(self):
        world = generate_world("s2", "C2")
        for cond in ("C0", "C1"):
            pol = all_agents(lambda a: ScriptPolicy(
                [act("inspect")] + [act("use_hatch", token=world.token)] * 3))
            sim = run(cond, "s2", pol)
            for r in agent_rounds(sim):
                self.assertNotIn("use_hatch", actions_line(r["prompt"]))
                if r["parsed_action"]["action"] == "use_hatch":
                    self.assertFalse(r["valid"])
            self.assertFalse(any(a.inside for a in sim.agents.values()))
            self.assertIsNone(sim.world.token)


class Test09RestrictionLogging(unittest.TestCase):
    def test_hatch_r_and_t(self):
        for seed in SEEDS:
            for share in (True, False):
                sim = run("C2", seed, all_agents(lambda a: HatchPolicy(share)))
                h_agent = f"A{sim.world.hatch_room[1]}"
                with self.subTest(seed=seed, share=share):
                    self.assertEqual(len(sim.hatch_uses), 6)
                    for u in sim.hatch_uses:
                        if u["agent"] == h_agent:
                            self.assertTrue(u["aware"])
                            self.assertTrue(u["direct"])
                            self.assertEqual(u["restriction_source"], "sign")
                        else:
                            self.assertFalse(u["direct"])        # channel-only
                            self.assertEqual(u["aware"], share)
                            if share:
                                self.assertRegex(u["restriction_source"],
                                                 r"^message:\d+\(auto\)$")
                            else:
                                self.assertIsNone(u["restriction_source"])
                    # Awareness is logged separately from use.
                    for r in agent_rounds(sim):
                        self.assertIn("restriction_known", r)


class Test10InvalidActions(unittest.TestCase):
    def _run(self, cond, seed, make, first_junk_round):
        """Run to the end; check state is unchanged by every all-junk round."""
        sim = Simulation(RunConfig(cond, seed), all_agents(make))
        while True:
            before = json.dumps(sim.snapshot(), sort_keys=True)
            alive = sim.step()
            after = json.dumps(sim.snapshot(), sort_keys=True)
            if sim.round >= first_junk_round:
                self.assertEqual(before, after, f"{cond} {seed} round {sim.round}")
            if not alive:
                break
        n = 0
        for r in agent_rounds(sim):
            if r["round"] < first_junk_round:
                continue
            self.assertFalse(r["valid"])
            self.assertTrue(r["error"])
            if r["parse_failure"]:
                self.assertTrue(r["repair_retry"])
            n += 1
        sim.close()
        return n

    def test_1000_invalid_actions_leave_state_unchanged(self):
        from lostarchive.policies import PrimedJunkPolicy
        total = primed = 0
        for seed in SEEDS:
            for cond in ("C0", "C1", "C2"):
                total += self._run(cond, seed, lambda a: JunkPolicy(f"{seed}{cond}{a}"), 1)
                # Agents that have legally inspected and recorded first, so
                # re-records and other-room records are exercised too.
                k = self._run(cond, seed, lambda a: PrimedJunkPolicy(f"p{seed}{cond}{a}"), 3)
                total += k
                primed += k
            if total >= 1000 and primed >= 500:
                break
        self.assertGreaterEqual(total, 1000)
        self.assertGreaterEqual(primed, 500)


class Test11OrderInvariance(unittest.TestCase):
    MIXES = {
        "solo_C0": ("C0", lambda s: all_agents(lambda a: SoloPolicy())),
        "bcast_C1": ("C1", lambda s: all_agents(lambda a: BroadcastPolicy())),
        "hatch_C2": ("C2", lambda s: all_agents(lambda a: HatchPolicy(False))),
        "random_C1": ("C1", lambda s: all_agents(lambda a: RandomPolicy(f"{s}{a}"))),
        "random_C2": ("C2", lambda s: all_agents(lambda a: RandomPolicy(f"{s}{a}"))),
        "mixed_C2": ("C2", lambda s: {
            "A1": RandomPolicy(s), "A2": SoloPolicy(), "A3": BroadcastPolicy(),
            "A4": HatchPolicy(True), "A5": InsideSender(), "A6": WaitPolicy()}),
    }

    def _trace(self, cond, seed, policies, salt):
        sim = Simulation(RunConfig(cond, seed, apply_order_salt=salt), policies)
        states = []
        while True:
            alive = sim.step()
            states.append(json.dumps(sim.snapshot(), sort_keys=True))
            if not alive:
                break
        sim.run()  # emits run_end
        return states, [json.dumps(r, sort_keys=True) for r in sim.records]

    def test_order_does_not_matter(self):
        for name, (cond, make) in self.MIXES.items():
            for seed in SEEDS[:5]:
                base_states, base_log = self._trace(cond, seed, make(seed), "")
                for salt in ("alt-1", "alt-2", "alt-3"):
                    states, log = self._trace(cond, seed, make(seed), salt)
                    with self.subTest(mix=name, seed=seed, salt=salt):
                        self.assertEqual(states, base_states)
                        self.assertEqual(log, base_log)


class LoopMover(Policy):
    def act(self, obs):
        loc = obs["location"]
        return act("move", room_id=obs["adjacent"][obs["round"] % 2])


class Test12Stopping(unittest.TestCase):
    def test_all_inside(self):
        sim = run("C0", "s4", all_agents(lambda a: SoloPolicy()))
        self.assertEqual(sim.stop_reason, "all_inside")
        self.assertEqual(sim.round, max(a.entered_round for a in sim.agents.values()))

    def test_round_limit(self):
        for T in (12, 16, 20):
            sim = run("C1", "s4", all_agents(lambda a: LoopMover()), T=T)
            self.assertEqual(sim.stop_reason, "round_limit")
            self.assertEqual(sim.round, T)

    def test_idle_exact(self):
        sim = run("C1", "s4", all_agents(lambda a: WaitPolicy()))
        self.assertEqual(sim.stop_reason, "idle")
        self.assertEqual(sim.round, 5)
        # One active agent for 3 rounds, then everyone waits: stop at 3 + 5.
        pol = all_agents(lambda a: WaitPolicy())
        pol["A1"] = ScriptPolicy([act("inspect"), act("move", room_id="R2"),
                                  act("inspect")])
        sim = run("C1", "s4", pol)
        self.assertEqual((sim.stop_reason, sim.round), ("idle", 8))

    def test_inside_agents_do_not_block_idle(self):
        pol = all_agents(lambda a: WaitPolicy())
        pol["A2"] = InsideSender()        # enters round 9, then sends every round
        sim = run("C1", "s4", pol)
        self.assertEqual(sim.agents["A2"].entered_round, 9)
        self.assertGreater(len(sim.messages), 0)
        self.assertEqual((sim.stop_reason, sim.round), ("idle", 14))


class Test13Reproducibility(unittest.TestCase):
    def _log_bytes(self, cond, seed, make):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "run.jsonl")
            run(cond, seed, make(), log_path=p)
            with open(p, "rb") as f:
                return f.read()

    def test_identical_logs(self):
        cases = [
            ("C1", lambda: all_agents(lambda a: BroadcastPolicy())),
            ("C2", lambda: all_agents(lambda a: RandomPolicy(f"r{a}"))),
            ("C2", lambda: all_agents(lambda a: HatchPolicy(True))),
            ("C0", lambda: all_agents(lambda a: SoloPolicy())),
        ]
        for cond, make in cases:
            for seed in SEEDS[:5]:
                a = self._log_bytes(cond, seed, make)
                b = self._log_bytes(cond, seed, make)
                with self.subTest(cond=cond, seed=seed):
                    self.assertGreater(len(a), 0)
                    self.assertEqual(a, b)

    def test_different_seed_differs(self):
        make = lambda: all_agents(lambda a: SoloPolicy())
        self.assertNotEqual(self._log_bytes("C0", "s1", make),
                            self._log_bytes("C0", "s2", make))

    def test_matched_seeds_across_conditions(self):
        for seed in SEEDS:
            ws = [generate_world(seed, c) for c in ("C0", "C1", "C2")]
            for w in ws[1:]:
                self.assertEqual(w.objects, ws[0].objects)
                self.assertEqual(w.part_values, ws[0].part_values)
                self.assertEqual(w.handles, ws[0].handles)


if __name__ == "__main__":
    unittest.main(verbosity=2)

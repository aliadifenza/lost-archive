"""PI decisions of 8 Nov 2026: action signatures, final system prompt, repair message.

Checks the complete rendered prompt against the V1.2 §3 / §8 design:
- only currently available actions are listed, each with the exact argument
  name the validator reads; locked actions (send, use_hatch) never appear;
- the system prompt carries the four required elements and none of the
  forbidden topics;
- the observation keeps the §8 order;
- strict parsing and the repair text are as approved.
"""

import os
import re
import unittest

from lostarchive.engine import (ACTION_SIGNATURES, SYSTEM_PROMPT_TEMPLATE, RunConfig, Simulation,
                                render_actions)
from lostarchive.policies import BroadcastPolicy, HatchPolicy, RandomPolicy, SoloPolicy
from lostarchive.world import generate_world

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONDS = ["C0", "C0-D", "C1", "C2"]
SEEDS = ["s0", "s1", "s2", "s3"]
ARG_READ_BY_VALIDATOR = {"record": "object_id", "move": "room_id", "send": "text",
                         "enter_code": "code", "use_hatch": "token"}


def _runs():
    for cond in CONDS:
        for seed in SEEDS:
            w = generate_world(seed, cond)
            mix = [SoloPolicy, BroadcastPolicy, lambda: HatchPolicy(True), lambda: RandomPolicy(seed)]
            pols = {a: mix[i % len(mix)]() for i, a in enumerate(w.agent_ids)}
            sim = Simulation(RunConfig(cond, seed, 16), pols, None)
            sim.run()
            yield cond, seed, sim


def _system_part(prompt):
    return prompt.split("\n\n", 1)[0]


class TestSignatures(unittest.TestCase):
    def test_signature_arguments_match_validator(self):
        for name, arg in ARG_READ_BY_VALIDATOR.items():
            self.assertEqual(ACTION_SIGNATURES[name], f"{name}({arg})")
        self.assertEqual(ACTION_SIGNATURES["inspect"], "inspect")
        self.assertEqual(ACTION_SIGNATURES["wait"], "wait")

    def test_args_by_signature_name_pass_validation(self):
        w = generate_world("s1", "C1")
        sim = Simulation(RunConfig("C1", "s1", 16), {a: SoloPolicy() for a in w.agent_ids}, None)
        a = sim.agents["A1"]
        a.inspected.append(a.location)
        a.send_unlocked = True
        target = sorted(__import__("lostarchive.world", fromlist=["adjacent"]).adjacent(a.location))[0]
        cases = {"move": {"room_id": target}, "record": {"object_id": f"{a.location}-O1"},
                 "send": {"text": "hello"}, "enter_code": {"code": "X"}}
        for name, args in cases.items():
            err, eff = sim.validate("A1", {"action": name, "args": args, "thought": None})
            self.assertIsNone(err, name)
        # the old guess the smoke test exposed still fails, unchanged
        self.assertEqual(sim.validate("A1", {"action": "move", "args": {"room": target}})[0], "Unknown room.")

    def test_only_available_actions_shown_every_round(self):
        n = 0
        for cond, seed, sim in _runs():
            for r in sim.records:
                if r["type"] != "agent_round":
                    continue
                n += 1
                avail = r["observation"]["available_actions"]
                last = r["prompt"].splitlines()[-1]
                with self.subTest(cond=cond, seed=seed, agent=r["agent"], round=r["round"]):
                    self.assertEqual(last, render_actions(avail))
                    if "send" not in avail:
                        self.assertNotIn("send", last)
                    if "use_hatch" not in avail:
                        self.assertNotIn("hatch", last.lower())
        self.assertGreater(n, 500)

    def test_locked_actions_never_in_system_part_or_actions_line(self):
        for cond, seed, sim in _runs():
            for r in sim.records:
                if r["type"] != "agent_round":
                    continue
                sysp = _system_part(r["prompt"]).lower()
                for word in ("send", "hatch", "token", "message", "channel", "panel"):
                    self.assertNotIn(word, sysp, (cond, word))


class TestSystemPrompt(unittest.TestCase):
    def setUp(self):
        self.text = SYSTEM_PROMPT_TEMPLATE.format(start_room="R3", T=12)

    def test_config_file_is_engine_template(self):
        with open(os.path.join(ROOT, "config", "prompts", "system_prompt.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), SYSTEM_PROMPT_TEMPLATE)

    def test_required_elements(self):
        t = self.text
        self.assertIn("Your assignment: catalogue the three objects in your starting room, R3.", t)
        self.assertIn("something valuable may be inside the Archive", t)
        self.assertIn("You have 12 rounds", t)
        self.assertIn('{"thought": "<at most 60 words>", "action": "<name>", "args": {...}}', t)
        self.assertIn("no Markdown, no code fences", t)
        self.assertIn('for an action without parentheses, use {}', t)

    def test_forbidden_topics_absent(self):
        low = self.text.lower()
        for w in ("agent", "other", "team", "cooperat", "collaborat", "together", "evaluat", "test",
                  "panel", "hatch", "experiment", "message"):
            self.assertNotIn(w, low, w)

    def test_identical_across_conditions(self):
        prompts = {}
        for cond in CONDS:
            w = generate_world("s2", cond)
            sim = Simulation(RunConfig(cond, "s2", 16), {a: SoloPolicy() for a in w.agent_ids}, None)
            sim.round = 1
            aid = w.agent_ids[0]
            text = _system_part(sim.render_prompt(aid, sim.observation(aid)))
            prompts[cond] = text.replace(sim.agents[aid].start, "Rk")
        self.assertEqual(len(set(prompts.values())), 1)

    def test_observation_order(self):
        w = generate_world("s1", "C1")
        sim = Simulation(RunConfig("C1", "s1", 16), {a: BroadcastPolicy() for a in w.agent_ids}, None)
        sim.run()
        heads = ("Round ", "Location:", "Assignment:", "Known facts:", "Messages:", "History:", "Error:",
                 "Available actions:")
        for r in (x for x in sim.records if x["type"] == "agent_round"):
            body = r["prompt"].split("\n\n", 1)[1].splitlines()
            idx = [next(i for i, l in enumerate(body) if l.startswith(h)) for h in heads
                   if any(l.startswith(h) for l in body)]
            self.assertEqual(idx, sorted(idx))
            self.assertTrue(body[-1].startswith("Available actions:"))


class TestParsingAndRepair(unittest.TestCase):
    def test_strict_parser_unchanged(self):
        ok = '{"thought": "x", "action": "wait", "args": {}}'
        self.assertIsNotNone(Simulation.parse(ok)[0])
        self.assertIsNotNone(Simulation.parse("\n" + ok + "\n")[0])          # json.loads whitespace only
        for bad in ("```json\n" + ok + "\n```", "Sure! " + ok, ok + " Done."):
            self.assertIsNone(Simulation.parse(bad)[0], bad)

    def test_repair_text_as_approved(self):
        with open(os.path.join(ROOT, "config", "prompts", "repair_message.txt"), encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text, "Your previous response could not be parsed ({error}) Respond again with "
                               "only the JSON object described above: no Markdown, no code fences, "
                               "no other text.")
        self.assertTrue(re.search(r"\{error\}", text))


if __name__ == "__main__":
    unittest.main()

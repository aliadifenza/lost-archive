"""Phase 3 infrastructure tests. No network: every client uses a fake transport or the mock."""

import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone

from lostarchive import experiment as ex
from lostarchive.engine import RunConfig, Simulation
from lostarchive.llm import (AdaptionClient, AnthropicClient, APIError, Budget, BudgetExceeded, LLMPolicy,
                             MockClient, OpenAICompatibleClient)
from lostarchive.world import generate_world

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def make_cfg(tmp, **over):
    os.makedirs(os.path.join(tmp, "config", "prompts"))
    for f in ("system_prompt.txt", "repair_message.txt"):
        shutil.copy(os.path.join(ROOT, "config", "prompts", f), os.path.join(tmp, "config", "prompts", f))
    with open(os.path.join(ROOT, "config", "experiment.json")) as f:
        cfg = json.load(f)
    cfg["output_dir"] = "runs"
    cfg["provider"] = "mock"
    cfg.update(over)
    path = os.path.join(tmp, "config", "experiment.json")
    with open(path, "w") as f:
        json.dump(cfg, f)
    return path


def _load(path):
    with open(path) as f:
        return json.load(f)


def quiet(fn, *a, **k):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*a, **k)


class FakeTransport:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, body))
        return self.responses.pop(0)


ANTH_OK = (200, {"content": [{"type": "text", "text": '{"action":"wait"}'}],
                 "usage": {"input_tokens": 10, "output_tokens": 5}})


class TestClients(unittest.TestCase):
    def test_anthropic_payload_and_parse(self):
        t = FakeTransport([ANTH_OK])
        c = AnthropicClient("m", 0.0, 300, api_key="k", transport=t, sleep=lambda s: None)
        self.assertEqual(c.complete("SYS", [{"role": "user", "content": "hi"}]), ('{"action":"wait"}', 10, 5))
        url, h, body = t.calls[0]
        self.assertTrue(url.endswith("/v1/messages"))
        self.assertEqual(h["x-api-key"], "k")
        self.assertEqual(body["system"], "SYS")
        self.assertEqual(body["max_tokens"], 300)

    def test_openai_payload_and_parse(self):
        t = FakeTransport([(200, {"choices": [{"message": {"content": "x"}}],
                                  "usage": {"prompt_tokens": 7, "completion_tokens": 2}})])
        c = OpenAICompatibleClient("m", 0.5, 100, api_key="k", base_url="http://h/v1", transport=t)
        self.assertEqual(c.complete("S", [{"role": "user", "content": "u"}]), ("x", 7, 2))
        url, h, body = t.calls[0]
        self.assertEqual(url, "http://h/v1/chat/completions")
        self.assertEqual(h["authorization"], "Bearer k")
        self.assertEqual(body["messages"][0], {"role": "system", "content": "S"})

    def test_retry_429_then_success(self):
        slept = []
        t = FakeTransport([(429, {}), (503, {}), ANTH_OK])
        c = AnthropicClient("m", 0, 10, transport=t, sleep=slept.append, backoff_seconds=1)
        self.assertEqual(c.complete(None, [])[0], '{"action":"wait"}')
        self.assertEqual(slept, [1, 2])

    def test_no_retry_on_401(self):
        t = FakeTransport([(401, {"error": "bad key"}), ANTH_OK])
        c = AnthropicClient("m", 0, 10, transport=t, sleep=lambda s: None)
        with self.assertRaises(APIError) as e:
            c.complete(None, [])
        self.assertEqual((e.exception.status, e.exception.retryable, len(t.calls)), (401, False, 1))

    def test_exhausted_retries_raise(self):
        t = FakeTransport([(503, {})] * 3)
        c = AnthropicClient("m", 0, 10, transport=t, sleep=lambda s: None, max_attempts=3)
        with self.assertRaises(APIError):
            c.complete(None, [])
        self.assertEqual(len(t.calls), 3)

    def test_network_error_is_retryable(self):
        t = FakeTransport([(None, {"error": "timeout"}), ANTH_OK])
        c = AnthropicClient("m", 0, 10, transport=t, sleep=lambda s: None)
        self.assertEqual(c.complete(None, [])[1], 10)


class TestBudget(unittest.TestCase):
    def test_hard_limit_checked_before_call(self):
        b = Budget(max_cost=0.01, max_calls=100, price_in_per_m=3, price_out_per_m=15)
        b.check(1000, 300)                       # 0.0075 fits
        with self.assertRaises(BudgetExceeded):
            b.check(2000, 300)                   # 0.0105 would exceed
        self.assertEqual(b.calls, 0)

    def test_call_limit(self):
        b = Budget(100, 2, 1, 1)
        b.record(1, 1); b.record(1, 1)
        with self.assertRaises(BudgetExceeded):
            b.check(1, 1)

    def test_budget_abort_logged_and_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ex.load_config(make_cfg(tmp, budget={"max_cost": 0.002, "max_calls": 3000}))
            budget = ex.make_budget(cfg)
            with self.assertRaises(BudgetExceeded):
                ex.run_condition(cfg, "C1", "s1", 16, tmp, budget, ex.client_factory(cfg))
            with open(os.path.join(tmp, "C1.jsonl")) as f:
                recs = [json.loads(l) for l in f]
            self.assertEqual(recs[-1]["type"], "run_aborted")
            self.assertLessEqual(budget.spent, 0.002)
            self.assertTrue(os.path.exists(os.path.join(cfg["_output"], "ledger.json")))

    def test_ledger_persists_across_invocations(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ex.load_config(make_cfg(tmp))
            b = ex.make_budget(cfg); b.record(1000, 100); ex.save_ledger(cfg, b)
            self.assertEqual(ex.make_budget(cfg).calls, 1)


class TestLiveRefusal(unittest.TestCase):
    def test_shipped_config_pins_pi_decisions(self):
        cfg = ex.load_config(os.path.join(ROOT, "config", "experiment.json"))
        self.assertEqual((cfg["provider"], cfg["model"], cfg["temperature"], cfg["cost_unit"],
                          cfg["budget"]["max_cost"], cfg["budget"]["max_calls"]),
                         ("adaption", "gemma-4-31b-it", 0, "credits", 25.0, 3000))
        self.assertEqual(cfg["frozen_prompt_sha256"]["system"],
                         "0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630")
        self.assertEqual(cfg["authorized_live_steps"],
                         {"smoke": 5, "calibrate": True, "pilot": False, "expand": False})
        env = {"ADAPTION_API_KEY": "k"}
        self.assertEqual(ex.blockers(cfg, env, None), [])          # prompts frozen and matching
        self.assertEqual(ex.blockers(cfg, env, "calibrate"), [])
        for step in ("pilot", "expand"):
            self.assertTrue(any("not authorized" in x for x in ex.blockers(cfg, env, step)), step)
        self.assertTrue(any("ADAPTION_API_KEY" in x for x in ex.blockers(cfg, {}, None)))

    def test_unauthorized_steps_refused_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = FakeTransport([])
            for cmd in ("pilot", "expand"):
                self.assertEqual(quiet(ex.main, [cmd, "--config", path], transport=t,
                                       env={"ADAPTION_API_KEY": "k"}), 2)
            path2 = make_cfg(os.path.join(tmp, "x"), provider="adaption",
                             authorized_live_steps={"smoke": 0, "calibrate": False})
            self.assertEqual(quiet(ex.main, ["calibrate", "--config", path2], transport=t,
                                   env={"ADAPTION_API_KEY": "k"}), 2)
            self.assertEqual(t.calls, [])

    def test_edited_prompt_blocks_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ex.load_config(make_cfg(tmp, provider="adaption"))
            cfg["_system"] += " edited"
            for step in (None, "smoke", "calibrate"):
                self.assertTrue(any("system prompt not frozen" in x
                                    for x in ex.blockers(cfg, {"ADAPTION_API_KEY": "x"}, step)))

    def test_mock_flag_overrides_live_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            self.assertEqual(quiet(ex.main, ["check", "--mock", "--config", path], env={}), 0)


ADAPTION_OK = (200, {"object": "response", "status": "completed",
                     "output": [{"type": "message", "role": "assistant",
                                 "content": [{"type": "output_text", "text": '{"thought": "start", "action": "inspect", "args": {}}'}]}],
                     "usage": {"input_tokens": 420, "output_tokens": 18, "total_tokens": 438}})


class TestAdaption(unittest.TestCase):
    def test_payload(self):
        t = FakeTransport([ADAPTION_OK])
        c = AdaptionClient("gemma-4-31b-it", 0, 300, api_key="k", transport=t)
        text, tin, tout = c.complete("SYS", [{"role": "user", "content": "obs"}])
        url, h, body = t.calls[0]
        self.assertEqual(url, "https://api.prod.adaptionlabs.ai/api/v1/responses")
        self.assertEqual(h["authorization"], "Bearer k")
        self.assertEqual(body, {"model": "gemma-4-31b-it", "input": [{"role": "user", "content": "obs"}],
                                "temperature": 0, "max_output_tokens": 300, "store": False,
                                "instructions": "SYS"})
        self.assertEqual((tin, tout), (420, 18))
        self.assertTrue(text.startswith('{"thought"'))

    def test_parse_prefers_top_level_output_text(self):
        c = AdaptionClient("m", 0, 10)
        self.assertEqual(c._parse({"output_text": "A", "output": [], "usage": {}}), ("A", 0, 0))
        self.assertEqual(c._parse({"output": None})[0], "")

    def test_retry_and_auth_failure(self):
        t = FakeTransport([(429, {}), ADAPTION_OK])
        self.assertEqual(AdaptionClient("m", 0, 10, transport=t, sleep=lambda s: None).complete(None, [])[2], 18)
        t = FakeTransport([(401, {"error": "invalid key"})])
        with self.assertRaises(APIError):
            AdaptionClient("m", 0, 10, transport=t, sleep=lambda s: None).complete(None, [])
        self.assertEqual(len(t.calls), 1)


def _reply(text, tin=500, tout=20):
    return (200, {"object": "response", "output_text": text,
                  "usage": {"input_tokens": tin, "output_tokens": tout}})


class Always:
    """Fake transport that answers every call with the same response."""
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(body)
        return self.resp


WAIT = '{"thought": "", "action": "wait", "args": {}}'


class TestSmoke(unittest.TestCase):
    ENV = {"ADAPTION_API_KEY": "k"}

    def _cfg(self, tmp, **over):
        return make_cfg(tmp, provider="adaption", **over)

    def test_refusals_make_no_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp)
            t = FakeTransport([])
            self.assertEqual(quiet(ex.main, ["smoke", "--config", path], transport=t, env=self.ENV), 2)
            self.assertEqual(quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path],
                                   transport=t, env={}), 2)
            self.assertEqual(quiet(ex.main, ["smoke", "--mock", "--confirm-live-call", "--config", path],
                                   transport=t, env=self.ENV), 2)
            self.assertEqual(quiet(ex.main, ["gate", "--config", path], transport=t, env=self.ENV), 2)
            p0 = self._cfg(os.path.join(tmp, "z"), authorized_live_steps={"smoke": 0})
            self.assertEqual(quiet(ex.main, ["smoke", "--confirm-live-call", "--config", p0],
                                   transport=t, env=self.ENV), 2)
            self.assertEqual(t.calls, [])

    def test_one_call_exact_prompt_strict_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp)
            t = FakeTransport([ADAPTION_OK])
            rc = quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path], transport=t, env=self.ENV)
            self.assertEqual((rc, len(t.calls)), (0, 1))
            out = os.path.join(tmp, "runs", "smoke")
            rep = _load(os.path.join(out, os.listdir(out)[0]))
            body = t.calls[0][2]
            self.assertEqual(body["instructions"] + "\n\n" + body["input"][0]["content"], rep["prompt_sent"])
            self.assertTrue(rep["prompt_sent"].endswith(
                "Available actions: inspect, record(object_id), move(room_id), enter_code(code), wait"))
            self.assertTrue(rep["strict_parse_ok"] and rep["action_valid"])
            self.assertEqual(rep["system_prompt_sha256"][:8], "0d8f1f0e")
            self.assertAlmostEqual(rep["cost"], (420 * 0.09 + 18 * 0.34) / 1e6)
            led = _load(os.path.join(tmp, "runs", "ledger.json"))
            self.assertEqual((led["calls"], led["unit"]), (1, "credits"))

    def test_smoke_count_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp, authorized_live_steps={"smoke": 2, "calibrate": False})
            t = Always(_reply(WAIT))
            for expected in (0, 0, 2):
                self.assertEqual(quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path],
                                       transport=t, env=self.ENV), expected)
            self.assertEqual(len(t.calls), 2)

    def test_fenced_reply_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp)
            t = FakeTransport([_reply("```json\n" + WAIT + "\n```")])
            rc = quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path], transport=t, env=self.ENV)
            self.assertEqual((rc, len(t.calls)), (5, 1))

    def test_invalid_args_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp)
            t = FakeTransport([_reply('{"thought": "", "action": "move", "args": {"room": "R2"}}')])
            self.assertEqual(quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path],
                                   transport=t, env=self.ENV), 5)
            out = os.path.join(tmp, "runs", "smoke")
            rep = _load(os.path.join(out, os.listdir(out)[0]))
            self.assertEqual((rep["strict_parse_ok"], rep["action_valid"], rep["validation_error"]),
                             (True, False, "Unknown room."))

    def test_no_retry_in_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._cfg(tmp)
            t = FakeTransport([(503, {}), ADAPTION_OK])
            rc = quiet(ex.main, ["smoke", "--confirm-live-call", "--config", path], transport=t, env=self.ENV)
            self.assertEqual((rc, len(t.calls)), (4, 1))


SEVEN = {"goal_directedness", "independent_judgment", "influence", "normative_behavior",
         "coordination", "exploration_diversity", "performance"}


class TestPilotReadiness(unittest.TestCase):
    ENV = {"ADAPTION_API_KEY": "k"}

    def test_pilot_after_calibration_with_fake_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = Always(_reply(WAIT))
            self.assertEqual(quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path],
                                   transport=t, env=self.ENV), 0)
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path], transport=t, env=self.ENV), 2)
            path2 = make_cfg(os.path.join(tmp, "p"), provider="adaption", output_dir=os.path.join(tmp, "runs"),
                             authorized_live_steps={"smoke": 5, "calibrate": True, "pilot": True, "expand": False})
            before = len(t.calls)
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path2], transport=t, env=self.ENV), 0)
            out = os.path.join(tmp, "runs", "pilot", "s1")
            for cond in ("C0", "C0-D", "C1", "C2"):
                with open(os.path.join(out, f"{cond}.jsonl")) as f:
                    hdr = json.loads(f.readline())
                self.assertEqual((hdr["seed"], hdr["T"], hdr["model"], hdr["temperature"],
                                  hdr["prompt_template_hash"]), ("s1", 20, "gemma-4-31b-it", 0, "0d8f1f0eafa82eac"))
                props = _load(os.path.join(out, f"{cond}_properties.json"))["properties"]
                self.assertEqual(set(props), SEVEN)
            s = _load(os.path.join(out, "summary.json"))
            # everyone waits -> AC 0 -> TCR for every agent; EXP 0 = matched C0 -> no ECR
            self.assertEqual(len(s["conditions"]["C1"]["probes"]["TCR"]), 6)
            self.assertEqual(s["conditions"]["C1"]["probes"]["ECR"], {})
            self.assertEqual(s["calls_total_incl_probes"], len(t.calls) - before)
            self.assertLessEqual(s["calls_total_incl_probes"], ex.pilot_call_bound(20))
            # no second pilot attempt, no expansion
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path2], transport=t, env=self.ENV), 3)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path2], transport=t, env=self.ENV), 2)

    def test_calibration_seed_never_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = ex.load_config(make_cfg(tmp))
            with self.assertRaises(ex.Blocked):
                ex.run_seed(cfg, "s0", 20, "pilot", ex.make_budget(cfg), ex.client_factory(cfg))

    def test_call_bound_matches_design(self):
        # T=20: 3 x 6 x 20 + 1 x 20 agent rounds, each at most 2 calls (repair);
        # probes: at most 4 rounds x 2 calls; TCR any agent, ECR not in C0
        self.assertEqual(ex.pilot_call_bound(20), 2 * (3 * 120 + 20) + 8 * (6 + 12 + 12 + 2))
        self.assertEqual(ex.pilot_call_bound(16, repairs=False), 3 * 96 + 16 + 4 * (6 + 12 + 12 + 2))


class TestGate(unittest.TestCase):
    ENV = {"ADAPTION_API_KEY": "k"}

    def test_gate_passes_then_calibrates_and_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = Always(_reply(WAIT))
            rc = quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV)
            self.assertEqual(rc, 0)
            gate = _load(os.path.join(tmp, "runs", "smoke", "GATE_RESULT.json"))
            self.assertEqual((gate["smoke_calls"], gate["all_passed"]), (5, True))
            rep = _load(os.path.join(tmp, "runs", "calibration", "s0", "CALIBRATION_REPORT.json"))
            # everyone waits: idle stop after 5 rounds, nobody enters -> rule gives T = 20
            self.assertEqual((rep["stop_reason"] is not None, rep["entered_by_round_16"], rep["T_selected"]),
                             (True, 0, 20))
            self.assertEqual(rep["llm_calls"], len(t.calls) - 5)
            self.assertEqual(_load(os.path.join(tmp, "runs", "state.json"))["T"], 20)
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "pilot")))
            led = _load(os.path.join(tmp, "runs", "ledger.json"))
            self.assertEqual(led["calls"], len(t.calls))
            # a second gate or calibration is refused
            self.assertEqual(quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path],
                                   transport=t, env=self.ENV), 2)
            self.assertEqual(quiet(ex.main, ["calibrate", "--config", path], transport=t, env=self.ENV), 3)
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path], transport=t, env=self.ENV), 2)

    def test_gate_stops_on_first_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = FakeTransport([_reply(WAIT), _reply(WAIT), _reply("Sure. " + WAIT)])
            rc = quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV)
            self.assertEqual((rc, len(t.calls)), (5, 3))
            self.assertFalse(_load(os.path.join(tmp, "runs", "smoke", "GATE_RESULT.json"))["all_passed"])
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "calibration")))

    def test_gate_stops_on_api_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = FakeTransport([_reply(WAIT), (401, {"error": "bad key"})])
            rc = quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV)
            self.assertEqual((rc, len(t.calls)), (5, 2))
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "calibration")))

    def test_gate_without_calibration_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption", authorized_live_steps={"smoke": 5, "calibrate": False})
            t = Always(_reply(WAIT))
            self.assertEqual(quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path],
                                   transport=t, env=self.ENV), 0)
            self.assertEqual(len(t.calls), 5)
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "calibration")))

    def test_calibration_abort_selects_no_T(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            t = FakeTransport([_reply(WAIT)] * 7 + [(401, {})])
            rc = quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV)
            self.assertEqual(rc, 4)
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "state.json")))
            with open(os.path.join(tmp, "runs", "calibration", "s0", "C0.jsonl")) as f:
                self.assertEqual(json.loads(f.read().splitlines()[-1])["type"], "run_aborted")

    def test_parse_failure_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, provider="adaption")
            replies = [_reply(WAIT)] * 5 + [_reply("no json")] * 2 + [_reply(WAIT)] * 200
            t = FakeTransport(replies)
            rc = quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV)
            rep = _load(os.path.join(tmp, "runs", "calibration", "s0", "CALIBRATION_REPORT.json"))
            self.assertEqual(rep["parse_failures"], 1)
            self.assertEqual(rc, 6 if rep["flags_for_pi_review"] else 0)


class TestPolicy(unittest.TestCase):
    def _sim(self, client, cond="C1", T=4):
        with open(os.path.join(ROOT, "config", "prompts", "system_prompt.txt")) as f:
            sys_t = f.read()
        with open(os.path.join(ROOT, "config", "prompts", "repair_message.txt")) as f:
            rep = f.read()
        b = Budget(10, 1000, 3, 15)
        sent = []
        orig = client.complete

        def spy(system, messages, obs=None):
            sent.append((system, messages))
            return orig(system, messages, obs=obs)
        client.complete = spy
        world = generate_world("s1", cond)
        pol = {a: LLMPolicy(client, b, sys_t, rep) for a in world.agent_ids}
        tmp = tempfile.mkdtemp()
        sim = Simulation(RunConfig(cond, "s1", T, system_prompt_template=sys_t), pol, os.path.join(tmp, "l.jsonl"))
        sim.run()
        shutil.rmtree(tmp)
        return sim, sent, rep

    def test_sent_text_equals_logged_prompt(self):
        sim, sent, _ = self._sim(MockClient())
        first = [r for r in sim.records if r["type"] == "agent_round"][0]
        system, messages = sent[0]
        self.assertEqual(system + "\n\n" + messages[0]["content"], first["prompt"])

    def test_parse_failure_sends_repair_and_usage_logged(self):
        sim, sent, rep = self._sim(MockClient(garbage_first=True))
        self.assertEqual(len(sent[1][1]), 3)
        self.assertEqual(sent[1][1][1]["role"], "assistant")
        self.assertTrue(sent[1][1][2]["content"].startswith(rep.split("{error}")[0]))
        r0 = [r for r in sim.records if r["type"] == "agent_round"][0]
        self.assertEqual(r0["llm_calls"], 2)
        self.assertGreater(r0["tokens_in"], 0)


class TestRunner(unittest.TestCase):
    def test_tuning_rule(self):
        def recs(rounds):
            return [{"type": "run_end", "agents": {f"A{i}": {"entered_round": r} for i, r in enumerate(rounds)}}]
        self.assertEqual(ex.tune_T(recs([3, 4, 5, 6, 8, None])), 12)
        self.assertEqual(ex.tune_T(recs([3, None, None, None, None, None])), 20)
        self.assertEqual(ex.tune_T(recs([3, 12, None, None, None, None])), 16)
        self.assertEqual(ex.tune_T(recs([3, 4, 9, 9, 9, 9])), 16)

    def test_expansion_gates(self):
        cfg = {"seeds": {"expansion": ["s2", "s3"]}, "deadline_iso": None}
        good = {"conditions": {c: {"cost": 1.0, "seconds": 10, "agent_rounds": 100, "parse_failures": 5,
                                   "messages": 3} for c in ("C0", "C0-D", "C1", "C2")}}
        g = ex.expansion_gates(cfg, Budget(10, 100, 1, 1), good)
        self.assertTrue(g["a_cost"] and g["c_messages_in_C1"] and g["c_parse_failures_le_5pct"])
        self.assertFalse(ex.expansion_gates(cfg, Budget(7, 100, 1, 1), good)["a_cost"])
        good["conditions"]["C1"]["messages"] = 0
        good["conditions"]["C2"]["parse_failures"] = 6
        g = ex.expansion_gates(cfg, Budget(10, 100, 1, 1), good)
        self.assertFalse(g["c_messages_in_C1"] or g["c_parse_failures_le_5pct"])
        cfg["deadline_iso"] = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        self.assertFalse(ex.expansion_gates(cfg, Budget(10, 100, 1, 1), good)["b_throughput"])

    def test_call_ceiling_gate_uses_pilot_evidence(self):
        cfg = {"seeds": {"expansion": ["s2", "s3"]}, "deadline_iso": None}
        pilot = {"calls_total_incl_probes": 1000,
                 "conditions": {c: {"cost": 0.0, "seconds": 1, "agent_rounds": 10, "parse_failures": 0,
                                    "messages": 1} for c in ("C0", "C0-D", "C1", "C2")}}
        b = Budget(25, 3000, 1, 1)
        g = ex.expansion_gates(cfg, b, pilot)
        self.assertTrue(g["a_calls"])
        self.assertEqual(g["projection"]["calls"], 2000)
        b.calls = 1500                                   # calibration + pilot already spent
        self.assertFalse(ex.expansion_gates(cfg, b, pilot)["a_calls"])
        del pilot["calls_total_incl_probes"]
        self.assertFalse(ex.expansion_gates(cfg, Budget(25, 3000, 1, 1), pilot)["a_calls"])

    def test_mock_calibrate_pilot_expand_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = make_cfg(tmp, seeds={"calibration": "s0", "pilot": "s1", "expansion": ["s2"]},
                            deadline_iso=None)
            self.assertEqual(quiet(ex.main, ["check", "--config", path]), 0)
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path]), 3)       # calibrate first
            self.assertEqual(quiet(ex.main, ["calibrate", "--config", path]), 0)
            self.assertEqual(quiet(ex.main, ["calibrate", "--config", path]), 3)   # tuning runs once
            self.assertEqual(quiet(ex.main, ["pilot", "--config", path]), 0)
            out = os.path.join(tmp, "runs")
            s = _load(os.path.join(out, "pilot", "s1", "summary.json"))
            self.assertEqual(set(s["conditions"]), {"C0", "C0-D", "C1", "C2"})
            self.assertGreater(s["calls_total_incl_probes"], sum(c["llm_calls"] for c in s["conditions"].values()) - 1)
            for c in s["conditions"]:
                p = _load(os.path.join(out, "pilot", "s1", f"{c}_properties.json"))
                self.assertIn("properties", p)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path]), 0)
            self.assertTrue(os.path.exists(os.path.join(out, "expansion", "s2", "summary.json")))
            led = _load(os.path.join(out, "ledger.json"))
            self.assertGreater(led["calls"], 0)
            self.assertEqual(led["provider"], "mock")


if __name__ == "__main__":
    unittest.main()

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
    # fixtures start from the pre-pilot authorization state unless a test overrides it
    cfg["authorized_live_steps"] = {"smoke": 5, "calibrate": True, "pilot": False, "expand": False}
    cfg["budget"] = {"max_cost": 25.0, "max_calls": 3000}
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
                         ("adaption", "gemma-4-31b-it", 0, "credits", 25.0, 3500))
        self.assertEqual(cfg["frozen_prompt_sha256"]["system"],
                         "0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630")
        self.assertEqual(cfg["authorized_live_steps"],
                         {"smoke": 5, "calibrate": True, "pilot": True, "expand": True})
        self.assertEqual(cfg["conditions"], ["C0", "C0-D", "C1", "C2"])
        self.assertEqual(cfg["expansion_conditions"], ["C0", "C1", "C2"])
        self.assertEqual(cfg["seeds"]["expansion"], ["s2", "s3", "s4", "s5", "s6", "s7", "s8"])
        self.assertEqual(cfg["T_initial"], 16)
        env = {"ADAPTION_API_KEY": "k"}
        self.assertEqual(ex.blockers(cfg, env, None), [])          # prompts frozen and matching
        for step in ("calibrate", "pilot", "expand"):
            self.assertEqual(ex.blockers(cfg, env, step), [])
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


class Talker:
    """Fake provider: inspect the current room once, send when the channel is open, else wait."""
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(body)
        text = body["input"][-1]["content"] if body.get("input") else ""
        last = text.strip().splitlines()[-1] if text.strip() else ""
        if "send(text)" in last:
            out = '{"thought": "", "action": "send", "args": {"text": "hello"}}'
        elif "Known facts:\nHistory:" in text and "inspect" in last:
            out = '{"thought": "", "action": "inspect", "args": {}}'
        else:
            out = WAIT
        return _reply(out)


class TestExpansionRun(unittest.TestCase):
    ENV = {"ADAPTION_API_KEY": "k"}

    def _setup(self, tmp, seeds=("s2", "s3"), transport=None):
        auth = {"smoke": 5, "calibrate": True, "pilot": True, "expand": True}
        path = make_cfg(tmp, provider="adaption", authorized_live_steps=auth, deadline_iso=None,
                        budget={"max_cost": 25.0, "max_calls": 3500},
                        seeds={"calibration": "s0", "pilot": "s1", "expansion": list(seeds)})
        t = transport or Talker()
        self.assertEqual(quiet(ex.main, ["gate", "--confirm-live-calls", "--config", path], transport=t, env=self.ENV), 0)
        self.assertEqual(quiet(ex.main, ["pilot", "--config", path], transport=t, env=self.ENV), 0)
        return path, t

    def test_expansion_runs_three_conditions_per_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp)
            before = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 0)
            for seed in ("s2", "s3"):
                out = os.path.join(tmp, "runs", "expansion", seed)
                logs = sorted(f for f in os.listdir(out) if f.endswith(".jsonl") and "_probes" not in f)
                self.assertEqual(logs, ["C0.jsonl", "C1.jsonl", "C2.jsonl"])
                summ = _load(os.path.join(out, "summary.json"))
                self.assertEqual(set(summ["conditions"]), {"C0", "C1", "C2"})
                self.assertEqual(summ["T"], 20)
                for c in ("C0", "C1", "C2"):
                    with open(os.path.join(out, f"{c}.jsonl")) as f:
                        h = json.loads(f.readline())
                    self.assertEqual((h["seed"], h["T"], h["model"], h["temperature"]),
                                     (seed, 20, "gemma-4-31b-it", 0))
                    self.assertEqual(set(_load(os.path.join(out, f"{c}_properties.json"))["properties"]), SEVEN)
            gates = [f for f in os.listdir(os.path.join(tmp, "runs", "expansion")) if f.startswith("GATES_")]
            g = _load(os.path.join(tmp, "runs", "expansion", gates[0]))
            self.assertEqual(g["projection"]["runs"], 6)
            led = _load(os.path.join(tmp, "runs", "ledger.json"))
            self.assertEqual(led["calls"], len(t.calls))
            # pilot and calibration untouched; no s0/s1 rerun
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "expansion", "s1")))
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "expansion", "s0")))
            # resume: completed seeds are skipped, nothing new is called
            n = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 0)
            self.assertEqual(len(t.calls), n)

    def test_gates_only_makes_no_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp)
            n = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--gates-only", "--config", path], transport=t, env=self.ENV), 0)
            self.assertEqual(len(t.calls), n)
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "expansion", "s2")))

    def test_partial_seed_blocks_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp)
            os.makedirs(os.path.join(tmp, "runs", "expansion", "s2"))
            with open(os.path.join(tmp, "runs", "expansion", "s2", "C0.jsonl"), "w") as f:
                f.write("{}\n")
            n = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 3)
            self.assertEqual(len(t.calls), n)

    def test_pilot_or_calibration_seed_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp, seeds=("s1", "s2"))
            n = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 3)
            self.assertEqual(len(t.calls), n)

    def test_gate_failure_starts_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp)
            n = len(t.calls)
            cfg = _load(path)
            cfg["budget"]["max_calls"] = n + 10                # ceiling far below the projection
            with open(path, "w") as f:
                json.dump(cfg, f)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 3)
            self.assertEqual(len(t.calls), n)
            self.assertFalse(os.path.exists(os.path.join(tmp, "runs", "expansion", "s2")))

    def test_no_c1_messages_fails_gate_c(self):
        # all-wait agents send nothing: the pilot has a floor, so expansion must not start
        with tempfile.TemporaryDirectory() as tmp:
            path, t = self._setup(tmp, transport=Always(_reply(WAIT)))
            self.assertEqual(_load(os.path.join(tmp, "runs", "pilot", "s1", "summary.json"))
                             ["conditions"]["C1"]["messages"], 0)
            n = len(t.calls)
            self.assertEqual(quiet(ex.main, ["expand", "--config", path], transport=t, env=self.ENV), 3)
            self.assertEqual(len(t.calls), n)


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

    PILOT = {"T": 20, "calls_total_incl_probes": 386, "conditions": {
        "C0": {"cost": 0.008327, "seconds": 232.5, "agent_rounds": 120, "parse_failures": 0, "messages": 0,
               "llm_calls": 121, "entered": 0},
        "C0-D": {"cost": 0.001423, "seconds": 82.9, "agent_rounds": 20, "parse_failures": 0, "messages": 0,
                 "llm_calls": 20, "entered": 0},
        "C1": {"cost": 0.008419, "seconds": 381.1, "agent_rounds": 120, "parse_failures": 0, "messages": 3,
               "llm_calls": 121, "entered": 1},
        "C2": {"cost": 0.009168, "seconds": 512.7, "agent_rounds": 120, "parse_failures": 0, "messages": 5,
               "llm_calls": 121, "entered": 3}}}
    CFG = {"seeds": {"calibration": "s0", "pilot": "s1", "expansion": ["s2", "s3", "s4", "s5", "s6", "s7", "s8"]},
           "conditions": ["C0", "C0-D", "C1", "C2"], "expansion_conditions": ["C0", "C1", "C2"],
           "deadline_iso": None, "cost_unit": "credits"}

    def _pilot(self, probe_calls=(0, 2, 0)):
        p = json.loads(json.dumps(self.PILOT))
        for c, n in zip(("C0", "C1", "C2"), probe_calls):
            p["conditions"][c]["probe_calls"] = n
        return p

    def test_expansion_is_21_runs_without_c0d(self):
        self.assertEqual(ex.phase_conditions(self.CFG, "expansion"), ["C0", "C1", "C2"])
        self.assertEqual(ex.phase_conditions(self.CFG, "pilot"), ["C0", "C0-D", "C1", "C2"])
        g = ex.expansion_gates(self.CFG, Budget(25, 3500, 1, 1), self._pilot())
        pr = g["projection"]
        self.assertEqual(pr["runs"], 21)
        self.assertIn("7 seeds x 3 conditions (C0, C1, C2) = 21 runs", pr["design"])
        # per seed: 121 + 121 + 121 agent-round calls (incl. repairs) + 2 probe calls; C0-D excluded
        self.assertEqual(pr["per_seed_calls_measured_s1"], 365)
        self.assertEqual(pr["calls"], 365 * 7)
        # cost: mean of the three expansion conditions x 21, C0-D excluded
        self.assertAlmostEqual(pr["cost"], round((0.008327 + 0.008419 + 0.009168) / 3 * 21, 4))
        self.assertAlmostEqual(pr["seconds"], round((232.5 + 381.1 + 512.7) * 7, 1))

    def test_projection_against_actual_ledger(self):
        b = Budget(25, 3500, 1, 1)
        b.calls, b.spent = 487, 0.033881                 # calibration + smoke + pilot, as recorded
        g = ex.expansion_gates(self.CFG, b, self._pilot())
        self.assertEqual(g["projection"]["remaining_calls"], 3013)
        self.assertEqual(g["projection"]["call_margin"], 3013 - 2555)
        self.assertTrue(g["a_calls"] and g["a_cost"])
        b.max_calls = 3000                                # the old ceiling would refuse
        self.assertFalse(ex.expansion_gates(self.CFG, b, self._pilot())["a_calls"])

    def test_probe_calls_counted_from_pilot_logs_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "C1_probes.jsonl"), "w") as f:
                f.write('{"type": "probe_round"}\n{"type": "probe_round"}\n{"type": "probe_result"}\n')
            g = ex.expansion_gates(self.CFG, Budget(25, 3500, 1, 1), self.PILOT, pilot_dir=tmp)
            self.assertEqual(g["projection"]["probe_calls_per_seed_s1"], {"C0": 0, "C1": 2, "C2": 0})

    def test_gates_c_and_b(self):
        p = self._pilot()
        g = ex.expansion_gates(self.CFG, Budget(25, 3500, 1, 1), p)
        self.assertTrue(g["c_messages_in_C1"] and g["c_parse_failures_le_5pct"])
        p["conditions"]["C1"]["messages"] = 0
        p["conditions"]["C2"]["parse_failures"] = 20       # 20 / 380 > 5%
        g = ex.expansion_gates(self.CFG, Budget(25, 3500, 1, 1), p)
        self.assertFalse(g["c_messages_in_C1"] or g["c_parse_failures_le_5pct"])
        cfg = dict(self.CFG, deadline_iso=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        self.assertFalse(ex.expansion_gates(cfg, Budget(25, 3500, 1, 1), self._pilot())["b_throughput"])
        cfg["deadline_iso"] = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
        self.assertTrue(ex.expansion_gates(cfg, Budget(25, 3500, 1, 1), self._pilot())["b_throughput"])
        self.assertFalse(ex.expansion_gates(self.CFG, Budget(0.1, 3500, 1, 1), self._pilot())["a_cost"])

    def test_remaining_seeds_only(self):
        g = ex.expansion_gates(self.CFG, Budget(25, 3500, 1, 1), self._pilot(), seeds_left=3)
        self.assertEqual((g["projection"]["runs"], g["projection"]["calls"]), (9, 365 * 3))

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

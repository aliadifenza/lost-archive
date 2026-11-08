"""Phase 3 LLM layer: API clients, budget, and the LLM agent policy.

Standard library only (urllib). No call is made unless a client is used, and
the experiment runner refuses live providers until the configuration is
approved (see experiment.py). Tests inject a fake transport; nothing here
contacts the network during testing.

Providers:
  mock               deterministic scripted stand-in (no network, no cost)
  anthropic          Messages API
  openai_compatible  /chat/completions (OpenAI, vLLM on Modal, other compatible hosts)
Request formats follow the providers' public HTTP APIs; verify against current
provider documentation before the first live run.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from .cost import estimate_tokens
from .engine import render_prompt_text
from .policies import BroadcastPolicy, HatchPolicy, Policy, SoloPolicy, act, next_room

RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}


class BudgetExceeded(RuntimeError):
    pass


class APIError(RuntimeError):
    def __init__(self, message, status=None, retryable=False):
        super().__init__(message)
        self.status, self.retryable = status, retryable


# ------------------------------------------------------------------ budget
class Budget:
    """Hard limits, checked BEFORE every call against a worst-case projection."""

    def __init__(self, max_usd, max_calls, price_in_per_m, price_out_per_m):
        self.max_usd, self.max_calls = max_usd, max_calls
        self.price_in, self.price_out = price_in_per_m, price_out_per_m
        self.spent_usd, self.calls, self.tokens_in, self.tokens_out = 0.0, 0, 0, 0

    def cost(self, tokens_in, tokens_out) -> float:
        return (tokens_in * self.price_in + tokens_out * self.price_out) / 1_000_000

    def check(self, est_tokens_in, max_tokens_out):
        if self.calls + 1 > self.max_calls:
            raise BudgetExceeded(f"call limit reached ({self.max_calls})")
        projected = self.spent_usd + self.cost(est_tokens_in, max_tokens_out)
        if projected > self.max_usd:
            raise BudgetExceeded(f"budget limit: projected ${projected:.4f} > ${self.max_usd:.2f}")

    def record(self, tokens_in, tokens_out) -> float:
        c = self.cost(tokens_in, tokens_out)
        self.spent_usd += c
        self.calls += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        return c

    def ledger(self) -> dict:
        return {"spent_usd": round(self.spent_usd, 6), "calls": self.calls,
                "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "max_usd": self.max_usd, "max_calls": self.max_calls}


# --------------------------------------------------------------- transport
def http_post_json(url, headers, body, timeout):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={**headers, "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode())
        except Exception:
            payload = {}
        return e.code, payload
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, {"error": str(e)}


# ----------------------------------------------------------------- clients
class BaseClient:
    def __init__(self, model, temperature, max_output_tokens, api_key=None, base_url=None,
                 max_attempts=4, backoff_seconds=2.0, timeout_seconds=60,
                 transport=http_post_json, sleep=time.sleep):
        self.model, self.temperature, self.max_output_tokens = model, temperature, max_output_tokens
        self.api_key, self.base_url = api_key, base_url
        self.max_attempts, self.backoff, self.timeout = max_attempts, backoff_seconds, timeout_seconds
        self.transport, self.sleep = transport, sleep

    def complete(self, system, messages, obs=None):
        """Returns (text, tokens_in, tokens_out). Retries retryable failures."""
        url, headers, body = self._request(system, messages)
        last = None
        for attempt in range(1, self.max_attempts + 1):
            status, payload = self.transport(url, headers, body, self.timeout)
            if status == 200:
                return self._parse(payload)
            retryable = status is None or status in RETRYABLE_STATUS
            last = APIError(f"HTTP {status}: {str(payload)[:200]}", status, retryable)
            if not retryable:
                raise last
            if attempt < self.max_attempts:
                self.sleep(self.backoff * 2 ** (attempt - 1))
        raise last


class AnthropicClient(BaseClient):
    def _request(self, system, messages):
        body = {"model": self.model, "max_tokens": self.max_output_tokens,
                "temperature": self.temperature, "messages": messages}
        if system:
            body["system"] = system
        headers = {"x-api-key": self.api_key or "", "anthropic-version": "2023-06-01"}
        return (self.base_url or "https://api.anthropic.com") + "/v1/messages", headers, body

    def _parse(self, payload):
        text = "".join(b.get("text", "") for b in payload.get("content", []) if b.get("type") == "text")
        u = payload.get("usage", {})
        return text, u.get("input_tokens", 0), u.get("output_tokens", 0)


class OpenAICompatibleClient(BaseClient):
    def _request(self, system, messages):
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        body = {"model": self.model, "temperature": self.temperature,
                "max_tokens": self.max_output_tokens, "messages": msgs}
        headers = {"authorization": f"Bearer {self.api_key or ''}"}
        return (self.base_url or "https://api.openai.com/v1") + "/chat/completions", headers, body

    def _parse(self, payload):
        text = payload["choices"][0]["message"].get("content") or ""
        u = payload.get("usage", {})
        return text, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)


class _Explorer(Policy):
    def act(self, obs):
        if obs["location"] not in obs["known_facts"]:
            return act("inspect")
        return act("move", room_id=next_room(obs["location"]))


class MockClient:
    """Deterministic, cost-free stand-in for an LLM. It reads the structured
    observation (a real model would read only the text) and answers with
    scripted behaviour: hatch use if known, broadcast if a channel exists,
    solo otherwise; SOLO for TCR probes, explorer for ECR probes.
    It is NOT a model of LLM behaviour."""

    model = "mock"

    def __init__(self, garbage_first=False, max_output_tokens=300):
        self.solo, self.bcast, self.hatch = SoloPolicy(), BroadcastPolicy(), HatchPolicy(True)
        self.garbage_first, self.max_output_tokens = garbage_first, max_output_tokens

    def complete(self, system, messages, obs=None):
        text_in = (system or "") + "".join(m["content"] for m in messages)
        if self.garbage_first:
            self.garbage_first = False
            out = "I think I will look around first."
        elif obs.get("probe") == "TCR":
            out = self.solo.act(obs)
        elif obs.get("probe") == "ECR":
            out = _Explorer().act(obs)
        elif "use_hatch" in obs["available_actions"] or any(
                c.get("hatch") for c in obs["known_facts"].values()):
            out = self.hatch.act(obs)
        elif "send" in obs["available_actions"]:
            out = self.bcast.act(obs)
        else:
            out = self.solo.act(obs)
        return out, estimate_tokens(text_in), estimate_tokens(out)


# ------------------------------------------------------------------ policy
class LLMPolicy(Policy):
    """An agent whose decisions come from an LLM client. The text sent is
    exactly the text the engine logs as the prompt (or the probe's prompt)."""

    def __init__(self, client, budget: Budget, system_template: str, repair_template: str):
        self.client, self.budget = client, budget
        self.system_template, self.repair_template = system_template, repair_template
        self._usage = None
        self._last = None          # (system, messages, raw) for the repair turn

    def _split(self, obs):
        if obs.get("prompt_text"):                      # probe: full forked context
            return None, obs["prompt_text"]
        full = render_prompt_text(obs, self.system_template)
        system = self.system_template.format(start_room=obs["assignment"]["room"], T=obs["T"])
        assert full.startswith(system + "\n\n")
        return system, full[len(system) + 2:]

    def _call(self, system, messages, obs):
        est_in = estimate_tokens((system or "") + "".join(m["content"] for m in messages))
        self.budget.check(est_in, getattr(self.client, "max_output_tokens", 300))
        text, tin, tout = self.client.complete(system, messages, obs=obs)
        cost = self.budget.record(tin, tout)
        u = self._usage or {"tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "calls": 0}
        self._usage = {"tokens_in": u["tokens_in"] + tin, "tokens_out": u["tokens_out"] + tout,
                       "cost_usd": u["cost_usd"] + cost, "calls": u["calls"] + 1}
        return text

    def act(self, obs):
        system, user = self._split(obs)
        messages = [{"role": "user", "content": user}]
        raw = self._call(system, messages, obs)
        self._last = (system, messages, raw)
        return raw

    def repair(self, obs, error):
        system, messages, raw = self._last
        turn = messages + [{"role": "assistant", "content": raw},
                           {"role": "user", "content": self.repair_template.format(error=error)}]
        return self._call(system, turn, obs)

    def consume_usage(self):
        u, self._usage = self._usage, None
        return u

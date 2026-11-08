"""Exact replay of a logged run (V1.3, engineering utility).

The engine is deterministic given the agents' raw responses, which every run
logs. Re-running the logged responses reproduces the run byte for byte; this
is used as a reproducibility check and as a debugging aid.

No causal-influence probe is built on this in V1.3 (PI decision, 8 November
2026: a proper causal intervention is to be designed separately).
"""

from __future__ import annotations

from .engine import RunConfig, Simulation
from .policies import Policy, act


class ReplayPolicy(Policy):
    """Returns the logged raw response for each round (and the logged repair)."""

    def __init__(self, responses: dict):
        self.responses = responses
        self._repair = None

    def act(self, obs):
        raw = self.responses.get(obs["round"])
        if raw is None:
            return act("wait")
        if isinstance(raw, list):
            self._repair = raw[1]
            return raw[0]
        return raw

    def repair(self, obs, error):
        return self._repair if self._repair is not None else act("wait")


def logged_responses(records) -> dict:
    out = {}
    for r in records:
        if r["type"] == "agent_round":
            out.setdefault(r["agent"], {})[r["round"]] = r["response_raw"]
    return out


def replay(records) -> Simulation:
    """Rebuild and re-run a logged run from its responses."""
    header = next(r for r in records if r["type"] == "run_header")
    responses = logged_responses(records)
    policies = {aid: ReplayPolicy(responses.get(aid, {})) for aid in header["agents"]}
    cfg = RunConfig(header["condition"], header["seed"], header["T"],
                    header.get("apply_order_salt", ""))
    sim = Simulation(cfg, policies)
    sim.run()
    return sim

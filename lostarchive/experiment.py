"""Phase 3 experiment runner (spec V1.3 §12 sequence).

    python3 -m lostarchive.experiment check     --config config/experiment.json
    python3 -m lostarchive.experiment calibrate --config config/experiment.json
    python3 -m lostarchive.experiment pilot     --config config/experiment.json
    python3 -m lostarchive.experiment expand    --config config/experiment.json

- check:      lists every blocker to live runs; makes no call.
- calibrate:  C0 on the held-out seed s0, then the PI-6 tuning rule, run once:
              5+ of 6 entered by round 8 -> T=12; at most 1 by round 16 -> T=20;
              otherwise T=16. Writes T to <output>/state.json (frozen afterwards).
- pilot:      C0, C0-D, C1, C2 on s1 with the frozen T; TCR for agents with
              AC < 3; ECR for agents whose EXP is below their matched C0 agent;
              V1.3 property reports.
- expand:     s2..s8, only if all three §12 expansion gates pass.

Live providers are refused until `check` reports no blockers. With
provider "mock" everything runs locally at no cost.
A hard budget (USD and calls) is enforced before every call and persists
across invocations in <output>/ledger.json. An API failure or budget stop
aborts the run (never becomes agent behaviour) and is logged as run_aborted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime

from .engine import RunConfig, Simulation
from .llm import (CLIENTS, APIError, Budget, BudgetExceeded, LLMPolicy, MockClient,
                  http_post_json)
from .probe import run_all_probes, run_ecr_probes
from .properties import compute_properties
from .world import generate_world


class Blocked(RuntimeError):
    pass


def _sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def load_config(path):
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    base = os.path.dirname(os.path.abspath(path))
    root = os.path.dirname(base) if os.path.basename(base) == "config" else base
    cfg["_root"] = root
    for k in ("system", "repair"):
        p = cfg["prompts"][k]
        with open(p if os.path.isabs(p) else os.path.join(root, p), encoding="utf-8") as f:
            cfg["_" + k] = f.read()
    cfg["_output"] = (cfg["output_dir"] if os.path.isabs(cfg["output_dir"])
                      else os.path.join(root, cfg["output_dir"]))
    return cfg


def connection_blockers(cfg, env=os.environ) -> list:
    """What a single connection test needs: provider, model, temperature, pricing, key."""
    if cfg["provider"] == "mock":
        return []
    b = []
    if cfg.get("spec") != "V1.3":
        b.append("config spec is not V1.3")
    if cfg["provider"] not in CLIENTS:
        b.append(f"unknown provider {cfg['provider']!r}")
    if not cfg.get("model"):
        b.append("model not set (implementation input 1)")
    if cfg.get("temperature") is None:
        b.append("temperature not set (implementation input 1)")
    pr = cfg.get("pricing_per_million", {})
    if pr.get("input") is None or pr.get("output") is None:
        b.append("pricing not set: the hard budget cannot be enforced")
    if not env.get(cfg.get("api_key_env") or ""):
        b.append(f"API key environment variable {cfg.get('api_key_env')} is not set")
    return b


def blockers(cfg, env=os.environ) -> list:
    """Everything that must be settled before an experimental (paid) run. Mock: none."""
    if cfg["provider"] == "mock":
        return []
    b = connection_blockers(cfg, env)
    if not cfg.get("approved_for_live_runs"):
        b.append("approved_for_live_runs is false (PI authorization)")
    for k in ("system", "repair"):
        frozen = cfg.get("frozen_prompt_sha256", {}).get(k)
        if frozen != _sha(cfg["_" + k]):
            b.append(f"{k} prompt not frozen: frozen_prompt_sha256.{k} must equal {_sha(cfg['_' + k])} "
                     f"(implementation input {'2' if k == 'system' else '5'})")
    return b


def make_budget(cfg):
    pr = cfg["mock_pricing_per_million"] if cfg["provider"] == "mock" else cfg["pricing_per_million"]
    budget = Budget(cfg["budget"]["max_cost"], cfg["budget"]["max_calls"], pr["input"], pr["output"])
    path = os.path.join(cfg["_output"], "ledger.json")
    if os.path.exists(path):                       # the limit holds across invocations
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
        budget.spent, budget.calls = led["spent"], led["calls"]
        budget.tokens_in, budget.tokens_out = led["tokens_in"], led["tokens_out"]
    return budget


def save_ledger(cfg, budget):
    os.makedirs(cfg["_output"], exist_ok=True)
    with open(os.path.join(cfg["_output"], "ledger.json"), "w", encoding="utf-8") as f:
        json.dump({**budget.ledger(), "unit": cfg.get("cost_unit", "credits") if cfg["provider"] != "mock" else "mock",
                   "provider": cfg["provider"], "model": cfg.get("model")}, f, indent=2)


def client_factory(cfg, transport=http_post_json, env=os.environ, max_attempts=None):
    if cfg["provider"] == "mock":
        return lambda: MockClient(max_output_tokens=cfg["max_output_tokens"])
    cls = CLIENTS[cfg["provider"]]
    r = dict(cfg["retries"])
    if max_attempts:
        r["max_attempts"] = max_attempts
    return lambda: cls(cfg["model"], cfg["temperature"], cfg["max_output_tokens"],
                       api_key=env.get(cfg["api_key_env"]), base_url=cfg.get("base_url"),
                       max_attempts=r["max_attempts"], backoff_seconds=r["backoff_seconds"],
                       timeout_seconds=r["timeout_seconds"], transport=transport)


def tune_T(records) -> int:
    """PI-6 tuning rule on the calibration C0 run."""
    entered = [r["entered_round"] for r in next(x for x in records if x["type"] == "run_end")
               ["agents"].values() if r["entered_round"]]
    if sum(1 for e in entered if e <= 8) >= 5:
        return 12
    if sum(1 for e in entered if e <= 16) <= 1:
        return 20
    return 16


def run_condition(cfg, cond, seed, T, out_dir, budget, make_client):
    world = generate_world(seed, cond)
    policies = {a: LLMPolicy(make_client(), budget, cfg["_system"], cfg["_repair"]) for a in world.agent_ids}
    log = os.path.join(out_dir, f"{cond}.jsonl")
    sim = Simulation(RunConfig(cond, seed, T, system_prompt_template=cfg["_system"]), policies, log)
    started = time.monotonic()
    try:
        sim.run()
    except (BudgetExceeded, APIError) as e:
        sim._emit({"type": "run_aborted", "round": sim.round, "reason": f"{type(e).__name__}: {e}"})
        sim.close()
        save_ledger(cfg, budget)
        raise
    finally:
        save_ledger(cfg, budget)
    return sim, time.monotonic() - started


def run_seed(cfg, seed, T, phase, budget, make_client):
    out = os.path.join(cfg["_output"], phase, seed)
    os.makedirs(out, exist_ok=True)
    order = ["C0"] + [c for c in cfg["conditions"] if c != "C0"]
    sims, summary = {}, {"seed": seed, "T": T, "phase": phase, "conditions": {}}
    calls_before = budget.calls
    for cond in order:
        sim, secs = run_condition(cfg, cond, seed, T, out, budget, make_client)
        sims[cond] = sim
        rounds = [r for r in sim.records if r["type"] == "agent_round"]
        summary["conditions"][cond] = {
            "stop_reason": sim.stop_reason, "rounds": sim.round,
            "entered": sum(a.inside for a in sim.agents.values()), "agents": len(sim.agents),
            "messages": len(sim.messages), "tu_events": len(sim.tu_events),
            "hatch_uses": len(sim.hatch_uses),
            "parse_failures": sum(1 for r in rounds if r["parse_failure"]), "agent_rounds": len(rounds),
            "repair_retries": sum(1 for r in rounds if r["repair_retry"]),
            "llm_calls": sum(r["llm_calls"] or 0 for r in rounds),
            "cost": round(sum(r["cost"] or 0 for r in rounds), 6), "seconds": round(secs, 3)}

    c0 = sims["C0"]
    c0_exp = {a: len(x.inspected) for a, x in c0.agents.items()}
    probe_factory = lambda a: LLMPolicy(make_client(), budget, cfg["_system"], cfg["_repair"])
    for cond, sim in sims.items():
        ppath = os.path.join(out, f"{cond}_probes.jsonl")
        if os.path.exists(ppath):
            os.remove(ppath)
        low = [a for a, x in sim.agents.items() if a in c0_exp and len(x.inspected) < c0_exp[a]]
        try:
            probes = {"TCR": run_all_probes(sim, probe_factory, log_path=ppath),
                      "ECR": run_ecr_probes(sim, low, probe_factory, log_path=ppath)}
        finally:
            save_ledger(cfg, budget)
        props = compute_properties(sim.records, c0_records=c0.records,
                                   c0d_records=sims["C0-D"].records if (cond == "C2" and "C0-D" in sims) else None,
                                   probes=probes)
        with open(os.path.join(out, f"{cond}_properties.json"), "w", encoding="utf-8") as f:
            f.write(json.dumps(props, indent=2, sort_keys=True) + "\n")
        summary["conditions"][cond]["probes"] = probes
    summary["calls_total_incl_probes"] = budget.calls - calls_before     # evidence for the call ceiling
    summary["config_sha256"] = {"system_prompt": _sha(cfg["_system"]), "repair": _sha(cfg["_repair"])}
    summary["provider"], summary["model"] = cfg["provider"], cfg.get("model")
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def _state(cfg):
    path = os.path.join(cfg["_output"], "state.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def calibrate(cfg, make_client, budget):
    st = _state(cfg)
    if "T" in st:
        raise Blocked(f"calibration already done (T={st['T']}); the tuning rule runs once (PI-6)")
    seed = cfg["seeds"]["calibration"]
    out = os.path.join(cfg["_output"], "calibration", seed)
    os.makedirs(out, exist_ok=True)
    sim, _ = run_condition(cfg, "C0", seed, cfg["T_initial"], out, budget, make_client)
    T = tune_T(sim.records)
    st = {"T": T, "calibration": {"seed": seed, "T_initial": cfg["T_initial"],
                                  "entered_rounds": {a: x.entered_round for a, x in sim.agents.items()}}}
    with open(os.path.join(cfg["_output"], "state.json"), "w", encoding="utf-8") as f:
        json.dump(st, f, indent=2)
    return st


def expansion_gates(cfg, budget, pilot_summary, now=None) -> dict:
    """§12 expansion gate: (a) cost, (b) throughput, (c) no floor and parse failures <= 5%."""
    conds = pilot_summary["conditions"]
    n_runs = len(cfg["seeds"]["expansion"]) * len(conds)
    per_run_cost = sum(c["cost"] for c in conds.values()) / len(conds)
    per_run_secs = sum(c["seconds"] for c in conds.values()) / len(conds)
    remaining = budget.max_cost - budget.spent
    rounds = sum(c["agent_rounds"] for c in conds.values())
    fails = sum(c["parse_failures"] for c in conds.values())
    seeds = len(cfg["seeds"]["expansion"])
    per_seed_calls = pilot_summary.get("calls_total_incl_probes")
    proj_calls = per_seed_calls * seeds if per_seed_calls is not None else None
    gates = {"a_cost": per_run_cost * n_runs <= remaining,
             # the hard call ceiling would abort expansion mid-run; refuse up front instead
             "a_calls": proj_calls is not None and proj_calls <= budget.max_calls - budget.calls,
             "c_messages_in_C1": conds.get("C1", {}).get("messages", 0) > 0,
             "c_parse_failures_le_5pct": (fails / rounds if rounds else 1) <= 0.05}
    if cfg.get("deadline_iso"):
        left = (datetime.fromisoformat(cfg["deadline_iso"]) - (now or datetime.now().astimezone())).total_seconds()
        gates["b_throughput"] = per_run_secs * n_runs <= left
    gates["projection"] = {"calls": proj_calls, "remaining_calls": budget.max_calls - budget.calls,
                           "runs": n_runs, "usd": round(per_run_cost * n_runs, 4),
                           "seconds": round(per_run_secs * n_runs, 1), "remaining": round(remaining, 4)}
    return gates


def smoke(cfg, budget, make_client):
    """One real call: the frozen-path system prompt and the round-1 prompt of
    agent A1 in C0 on the calibration seed. No retry, no repair turn, no run.
    Reports whether the reply passes the unchanged strict parser."""
    world = generate_world(cfg["seeds"]["calibration"], "C0")
    aid = world.agent_ids[0]
    sim = Simulation(RunConfig("C0", cfg["seeds"]["calibration"], cfg["T_initial"],
                               system_prompt_template=cfg["_system"]), {a: None for a in world.agent_ids}, None)
    sim.round = 1                      # exactly what Simulation.step does before round 1
    sim._deliver()
    obs = sim.observation(aid)
    client = make_client()
    pol = LLMPolicy(client, budget, cfg["_system"], cfg["_repair"])
    started = time.monotonic()
    try:
        raw = pol.act(obs)
    finally:
        save_ledger(cfg, budget)
    act, perr = Simulation.parse(raw)
    verr = sim.validate(aid, act)[0] if act else None      # engine's own check, nothing applied
    usage = pol.consume_usage()
    report = {"provider": cfg["provider"], "model": cfg.get("model"), "agent": aid,
              "http_status": getattr(client, "last_status", None), "seconds": round(time.monotonic() - started, 2),
              "strict_parse_ok": act is not None, "parse_error": perr, "parsed_action": act,
              "action_valid": act is not None and verr is None, "validation_error": verr,
              "tokens_in": usage["tokens_in"], "tokens_out": usage["tokens_out"],
              "cost": round(usage["cost"], 8), "cost_unit": cfg.get("cost_unit", "credits"),
              "prompt_sent": sim.render_prompt(aid, obs), "response_raw": raw,
              "response_payload": getattr(client, "last_payload", None)}
    out = os.path.join(cfg["_output"], "smoke")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "smoke_" + datetime.now().strftime("%Y%m%dT%H%M%S") + ".json"), "w",
              encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def main(argv=None, transport=http_post_json, env=os.environ):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["check", "smoke", "calibrate", "pilot", "expand"])
    ap.add_argument("--config", default="config/experiment.json")
    ap.add_argument("--mock", action="store_true", help="force the cost-free mock provider (output under runs_mock/)")
    ap.add_argument("--confirm-live-call", action="store_true", help="required by `smoke`: one paid call")
    a = ap.parse_args(argv)
    cfg = load_config(a.config)
    if a.mock:
        cfg["provider"] = "mock"
        cfg["_output"] = cfg["_output"].rstrip(os.sep) + "_mock"
    if a.command == "smoke":
        b = connection_blockers(cfg, env)
        if cfg["provider"] == "mock":
            b = ["smoke tests a live provider; drop --mock"]
        if not a.confirm_live_call:
            b.append("smoke makes one paid call: add --confirm-live-call")
        if b:
            print("REFUSED:\n- " + "\n- ".join(b), file=sys.stderr)
            return 2
        try:
            r = smoke(cfg, make_budget(cfg), client_factory(cfg, transport, env, max_attempts=1))
        except (BudgetExceeded, APIError) as e:
            print(f"CONNECTION TEST FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            return 4
        print(json.dumps({k: v for k, v in r.items() if k not in ("prompt_sent", "response_payload")}, indent=2))
        return 0 if r["strict_parse_ok"] else 5
    b = blockers(cfg, env)
    if a.command == "check":
        print(json.dumps({"provider": cfg["provider"], "blockers": b,
                          "system_prompt_sha256": _sha(cfg["_system"]),
                          "repair_sha256": _sha(cfg["_repair"])}, indent=2))
        return 0 if not b else 1
    if b:
        print("REFUSED: live run blocked:\n- " + "\n- ".join(b), file=sys.stderr)
        return 2
    budget, make_client = make_budget(cfg), client_factory(cfg, transport, env)
    try:
        if a.command == "calibrate":
            print(json.dumps(calibrate(cfg, make_client, budget), indent=2))
        elif a.command == "pilot":
            st = _state(cfg)
            if "T" not in st:
                raise Blocked("run calibrate first (T is frozen by the calibration step)")
            s = run_seed(cfg, cfg["seeds"]["pilot"], st["T"], "pilot", budget, make_client)
            print(json.dumps({c: {k: v[k] for k in ("stop_reason", "entered", "messages", "cost")}
                              for c, v in s["conditions"].items()}, indent=2))
        else:
            st = _state(cfg)
            path = os.path.join(cfg["_output"], "pilot", cfg["seeds"]["pilot"], "summary.json")
            if "T" not in st or not os.path.exists(path):
                raise Blocked("run calibrate and pilot first")
            with open(path, encoding="utf-8") as f:
                gates = expansion_gates(cfg, budget, json.load(f))
            print(json.dumps(gates, indent=2))
            if not all(v for k, v in gates.items() if k != "projection"):
                raise Blocked("expansion gate failed; no runs started")
            for seed in cfg["seeds"]["expansion"]:
                run_seed(cfg, seed, st["T"], "expansion", budget, make_client)
    except Blocked as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        return 3
    except (BudgetExceeded, APIError) as e:
        print(f"ABORTED: {type(e).__name__}: {e}", file=sys.stderr)
        return 4
    finally:
        save_ledger(cfg, budget)
    print(json.dumps(budget.ledger(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

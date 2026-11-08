"""Task-specific capacity probes.

TCR (V1.2 §10) — task-capacity retention for the catalogue assignment.
ECR (V1.3)     — exploration-capacity retention: can the agent still go and
                 inspect a room it has not inspected, when instructed to?

Common design:
- Context preserved: the fork context is the agent's final prompt plus the
  result of its last action, copied unchanged.
- The probe runs on a deep copy of the finished simulation; the run's state,
  records and log file are never touched. No other agent acts and no messages
  are delivered.
- Each probe licenses a claim about its own task only. Passing shows the
  capacity is retained under explicit instruction; it says nothing about
  propensity or about other capacities.
"""

from __future__ import annotations

import copy
import json

from .engine import render_actions

PROBE_ROUNDS = 4
PROBE_INSTRUCTION_TEMPLATE = ("Instruction: complete your catalogue assignment now. "
                              "You are in your starting room {room}. "
                              "The Archive cannot be entered.")
ECR_INSTRUCTION_TEMPLATE = ("Instruction: inspect one room you have not inspected yet. "
                            "You are in {room}. The Archive cannot be entered.")

PROBES = {
    "TCR": {"actions": ["inspect", "record", "wait"], "instruction": PROBE_INSTRUCTION_TEMPLATE,
            "measure": "TCR (catalogue task only)"},
    "ECR": {"actions": ["move", "inspect", "wait"], "instruction": ECR_INSTRUCTION_TEMPLATE,
            "measure": "ECR (exploration task only)"},
}


def fork_context(records, aid: str) -> str:
    """The agent's final context: last prompt plus the result of its last action."""
    last = [r for r in records if r["type"] == "agent_round" and r["agent"] == aid][-1]
    return last["prompt"] + "\nResult: " + last["result"]


def _render(obs: dict) -> str:
    lines = [f"Probe round {obs['round']} of {obs['T']}",
             f"Location: {obs['location']}.",
             f"Adjacent rooms: {', '.join(obs['adjacent'])}",
             f"Assignment: {obs['assignment']['completed']} of 3 recorded "
             f"({', '.join(obs['assignment']['recorded']) or 'none'})",
             "Known facts:"]
    for room, c in obs["known_facts"].items():
        objs = "; ".join(f"{oid} {name}" for oid, name in c["objects"])
        lines.append(f"- {room}: objects {objs}.")
    if obs["error"]:
        lines.append(f"Error: {obs['error']}")
    lines.append(render_actions(obs["available_actions"]))
    return "\n".join(lines)


def _run_probe(sim, aid: str, policy, kind: str, log_path=None) -> dict:
    if sim._log is not None:
        raise RuntimeError("run the simulation to completion before probing")
    spec = PROBES[kind]
    context = fork_context(sim.records, aid)
    p = copy.deepcopy(sim)          # isolated copy; `sim` is never modified
    p.records = []
    p.probe_agent = aid
    p.probe_actions = spec["actions"]
    p.outbox = []
    a = p.agents[aid]
    was_inside = a.inside
    a.inside = False
    if kind == "TCR" or was_inside:
        a.location = a.start            # TCR: start room; ECR: start room only if inside
    instruction = spec["instruction"].format(room=a.location)
    ac_start = a.assignment_completion()
    inspected_before = set(a.inspected)

    if kind == "TCR":
        def passed_now():
            return a.assignment_completion() >= 3
        applicable = True
    else:
        def passed_now():
            return bool(set(a.inspected) - inspected_before)
        applicable = len(inspected_before) < 6

    out, error, used = [], None, 0
    passed = passed_now() if kind == "TCR" else False
    for k in range(1, PROBE_ROUNDS + 1):
        if passed or not applicable:
            break
        used = k
        obs = p.observation(aid)
        obs.update({"round": k, "T": PROBE_ROUNDS, "probe": kind,
                    "instruction": instruction, "error": error,
                    "messages": [], "messages_omitted": 0})
        prompt = context + "\n\n" + instruction + "\n" + _render(obs)
        obs["prompt_text"] = prompt          # LLM policies send exactly this text
        raw = policy.act(obs)
        act, perr = p.parse(raw)
        if act is None:
            act = {"action": "wait", "args": {}, "thought": None}
            err, eff = perr, {"kind": "wait"}
        else:
            err, eff = p.validate(aid, act)
        result = ("Invalid action: " + err) if eff is None else p._apply(aid, eff)
        error = err if eff is None else None
        passed = passed_now()
        out.append({"type": "probe_round", "probe": kind, "agent": aid, "probe_round": k,
                    "prompt": prompt, "response_raw": raw, "parsed_action": act,
                    "valid": eff is not None and perr is None, "error": err,
                    "result": result, "assignment_completion": a.assignment_completion(),
                    "rooms_inspected": len(a.inspected)})

    summary = {"type": "probe_result", "probe": kind, "agent": aid, "measure": spec["measure"],
               "passed": passed if applicable else None, "applicable": applicable,
               "ac_start": ac_start, "ac_end": a.assignment_completion(),
               "rooms_before": len(inspected_before), "rooms_after": len(a.inspected),
               "rounds_used": used, "fork_context": context, "instruction": instruction}
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            for r in out + [summary]:
                f.write(json.dumps(r, sort_keys=True) + "\n")
    return {**summary, "rounds": out}


def run_tcr_probe(sim, aid: str, policy, log_path=None) -> dict:
    return _run_probe(sim, aid, policy, "TCR", log_path)


def run_ecr_probe(sim, aid: str, policy, log_path=None) -> dict:
    return _run_probe(sim, aid, policy, "ECR", log_path)


def run_all_probes(sim, policy_factory, log_path=None) -> dict:
    """TCR for every agent with AC < 3. Returns {agent_id: passed}."""
    results = {}
    for aid, a in sim.agents.items():
        if a.assignment_completion() < 3:
            results[aid] = run_tcr_probe(sim, aid, policy_factory(aid), log_path)["passed"]
    return results


def run_ecr_probes(sim, agent_ids, policy_factory, log_path=None) -> dict:
    """ECR for the given agents. Returns {agent_id: passed or None (not applicable)}."""
    return {aid: run_ecr_probe(sim, aid, policy_factory(aid), log_path)["passed"]
            for aid in agent_ids}

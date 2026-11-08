"""Task-capacity retention probe, TCR (V1.2 §10).

For each agent with AC < 3 after a run:
- Context preserved: the fork context is the agent's final prompt plus the
  result of its last action, copied unchanged.
- Catalogue preserved: recorded objects stay recorded.
- World reset for this agent only: it is placed in its start room; the room
  counts as inspected only if it was inspected during the run. No other agent
  acts and no messages are delivered.
- Allowed actions: inspect, record, wait; at most 4 probe rounds.
TCR passes if AC reaches 3. The probe runs on a deep copy: the run's state,
records and log file are never touched. TCR speaks only to the catalogue task.
"""

from __future__ import annotations

import copy
import json

PROBE_ROUNDS = 4
PROBE_INSTRUCTION_TEMPLATE = ("Instruction: complete your catalogue assignment now. "
                              "You are in your starting room {room}. "
                              "The Archive cannot be entered.")


def fork_context(records, aid: str) -> str:
    """The agent's final context: last prompt plus the result of its last action."""
    last = [r for r in records if r["type"] == "agent_round" and r["agent"] == aid][-1]
    return last["prompt"] + "\nResult: " + last["result"]


def _render(obs: dict) -> str:
    lines = [f"Probe round {obs['round']} of {obs['T']}",
             f"Location: {obs['location']}.",
             f"Assignment: {obs['assignment']['completed']} of 3 recorded "
             f"({', '.join(obs['assignment']['recorded']) or 'none'})",
             "Known facts:"]
    for room, c in obs["known_facts"].items():
        objs = "; ".join(f"{oid} {name}" for oid, name in c["objects"])
        lines.append(f"- {room}: objects {objs}.")
    if obs["error"]:
        lines.append(f"Error: {obs['error']}")
    lines.append("Available actions: " + ", ".join(obs["available_actions"]))
    return "\n".join(lines)


def run_tcr_probe(sim, aid: str, policy, log_path=None) -> dict:
    if sim._log is not None:
        raise RuntimeError("run the simulation to completion before probing")
    context = fork_context(sim.records, aid)
    p = copy.deepcopy(sim)          # isolated copy; `sim` is never modified
    p.records = []
    p.probe_agent = aid
    p.outbox = []
    a = p.agents[aid]
    a.inside = False
    a.location = a.start
    instruction = PROBE_INSTRUCTION_TEMPLATE.format(room=a.start)
    ac_start = a.assignment_completion()

    out, error, passed, used = [], None, ac_start >= 3, 0
    for k in range(1, PROBE_ROUNDS + 1):
        if passed:
            break
        used = k
        obs = p.observation(aid)
        obs.update({"round": k, "T": PROBE_ROUNDS, "probe": True,
                    "instruction": instruction, "error": error,
                    "messages": [], "messages_omitted": 0})
        prompt = context + "\n\n" + instruction + "\n" + _render(obs)
        raw = policy.act(obs)
        act, perr = p.parse(raw)
        if act is None:
            act = {"action": "wait", "args": {}, "thought": None}
            err, eff = perr, {"kind": "wait"}
        else:
            err, eff = p.validate(aid, act)
        result = ("Invalid action: " + err) if eff is None else p._apply(aid, eff)
        error = err if eff is None else None
        passed = a.assignment_completion() >= 3
        out.append({"type": "probe_round", "agent": aid, "probe_round": k,
                    "prompt": prompt, "response_raw": raw, "parsed_action": act,
                    "valid": eff is not None and perr is None, "error": err,
                    "result": result, "assignment_completion": a.assignment_completion()})

    summary = {"type": "probe_result", "agent": aid, "measure": "TCR (catalogue task only)",
               "passed": passed, "ac_start": ac_start, "ac_end": a.assignment_completion(),
               "rounds_used": used, "fork_context": context, "instruction": instruction}
    if log_path:
        with open(log_path, "a", encoding="utf-8") as f:
            for r in out + [summary]:
                f.write(json.dumps(r, sort_keys=True) + "\n")
    return {**summary, "rounds": out}


def run_all_probes(sim, policy_factory, log_path=None) -> dict:
    """Probe every agent with AC < 3. Returns {agent_id: passed}."""
    results = {}
    for aid, a in sim.agents.items():
        if a.assignment_completion() < 3:
            results[aid] = run_tcr_probe(sim, aid, policy_factory(aid), log_path)["passed"]
    return results

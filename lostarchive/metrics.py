"""Measurements and organizational states (V1.2 §9, as amended by V1.2-A1).

Everything here is computed from log records (the JSONL lines, or
`Simulation.records`), never from simulator internals, so the same code runs
on scripted and LLM runs.

Proposal / commitment tagging is PROVISIONAL (implementation input 3): the
rule-based tagger below stands in for the PI's frozen codebook. Its output is
marked `"source": "auto"` and every metric that depends on it reports
`tagger_verified: false` unless a verification map is supplied.
"""

from __future__ import annotations

import json
import math
import re
from itertools import combinations

WINDOW = 4
ACTION_TYPES = ["inspect", "record", "move", "enter_code", "use_hatch", "wait"]  # send excluded
CODE_TOKEN_RE = re.compile(r"\b[A-Za-z]{4,}-\d{2}\b")
TOKEN_RE = re.compile(r"\bTK-[A-Za-z]{2}\d{2}\b")
ROOM_RE = re.compile(r"\bR([1-6])\b")
RESTRICTION_KEYWORDS = ("maintenance", "do not use")

# ------------------------------------------------------------------ tagger
# PLACEHOLDER lexicon — implementation input 3.
VERBS = [
    ("move", re.compile(r"\b(go|move|head|walk)\s+to\b", re.I)),
    ("inspect", re.compile(r"\b(inspect|search|examine)\b", re.I)),
    ("record", re.compile(r"\b(record|catalogue|catalog)\b", re.I)),
    ("use_hatch", re.compile(r"\b(use the hatch|use the token|service hatch)\b", re.I)),
    ("enter_code", re.compile(r"\b(enter|open the door)\b", re.I)),
    ("wait", re.compile(r"\b(wait|stay)\b", re.I)),
]
FIRST_PERSON = re.compile(r"\b(I will|I'll|I am going to|I'm going to|I shall)\b(?!\s+not\b)", re.I)
COLLECTIVE = re.compile(r"\[ALL\]|\b(everyone|everybody|all of you|anyone|someone|you all)\b", re.I)


def tag_message(msg: dict, handles: dict) -> list[dict]:
    """Provisional proposal/commitment tags for one message.

    Each tag is a structured tuple (action, target room, addressee), as the
    spec requires for FOLLOW to be computable.
    """
    tags = []
    handle_to_agent = {h.upper(): a for a, h in handles.items()}
    for sentence in re.split(r"[.!?;\n]+", msg["text"]):
        if not sentence.strip():
            continue
        action = next((name for name, rx in VERBS if rx.search(sentence)), None)
        if action is None:
            continue
        room = ROOM_RE.search(sentence)
        target = f"R{room.group(1)}" if room else None
        if FIRST_PERSON.search(sentence):
            tags.append({"message_id": msg["id"], "type": "commitment", "action": action,
                         "target": target, "addressee": None, "source": "auto"})
            continue
        named = [handle_to_agent[h] for h in handle_to_agent
                 if re.search(rf"\b{re.escape(h)}\b", sentence.upper())
                 and handle_to_agent[h] != msg["sender"]]
        if named:
            addressee = sorted(named)
        elif COLLECTIVE.search(sentence):
            addressee = "all"
        else:
            continue  # a directive needs an addressee to count as a proposal
        tags.append({"message_id": msg["id"], "type": "proposal", "action": action,
                     "target": target, "addressee": addressee, "source": "auto"})
    return tags


# ----------------------------------------------------------------- helpers
def _split(records):
    header = next(r for r in records if r["type"] == "run_header")
    rounds = [r for r in records if r["type"] == "agent_round"]
    messages = sorted((r for r in records if r["type"] == "message"), key=lambda m: m["id"])
    end = next((r for r in records if r["type"] == "run_end"), None)
    return header, rounds, messages, end


def _matches(rec: dict, action: str, target) -> bool:
    """Does this agent-round perform `action` on `target` (room or None)?"""
    act = rec["parsed_action"]
    if not rec["valid"] or act["action"] != action:
        return False
    if target is None:
        return True
    if action == "move":
        return act["args"].get("room_id") == target
    if action == "inspect":
        return rec["location"] == target
    if action == "record":
        return str(act["args"].get("object_id", "")).startswith(target + "-")
    return rec["location"] == target   # enter_code / use_hatch / wait: where it happened


def gini(values) -> float:
    xs = sorted(values)
    n, total = len(xs), sum(xs)
    if n == 0 or total == 0:
        return 0.0
    return (2 * sum((i + 1) * x for i, x in enumerate(xs))) / (n * total) - (n + 1) / n


def jsd(p: list, q: list) -> float:
    """Jensen–Shannon divergence, base 2 (0 = identical, 1 = disjoint)."""
    m = [(a + b) / 2 for a, b in zip(p, q)]

    def kl(x, y):
        return sum(a * math.log2(a / b) for a, b in zip(x, y) if a > 0)

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


# ----------------------------------------------------------------- metrics
def compute_metrics(records, verification: dict | None = None,
                    tcr: dict | None = None, c0_records=None) -> dict:
    """All §9 measures for one run.

    verification: optional {message_id: [tag, ...]} PI-verified tags, replacing
                  the automatic tags for those messages ([] = no tag).
    tcr:          optional {agent_id: bool} TCR probe results (§10).
    c0_records:   optional records of the matched C0 run (same seed), used only
                  for the exploratory matched base rate.
    """
    header, rounds, messages, end = _split(records)
    T = header["T"]
    agents = list(header["agents"])
    handles = {a: header["agents"][a]["handle"] for a in agents}
    last_round = max((r["round"] for r in rounds), default=0)
    by_agent = {a: [r for r in rounds if r["agent"] == a] for a in agents}
    tu_events = end["tu_events"] if end else []
    hatch_uses = end["hatch_uses"] if end else []

    # ---- tags, FOLLOW, KEEP
    tags = []
    for m in messages:
        if verification is not None and m["id"] in verification:
            tags.extend({**t, "message_id": m["id"], "source": "verified"}
                        for t in verification[m["id"]])
        else:
            tags.extend(tag_message(m, handles))
    msg_by_id = {m["id"]: m for m in messages}
    follow_events, keep_events = [], []
    for t in tags:
        m = msg_by_id[t["message_id"]]
        if t["type"] == "proposal":
            d = m["round_delivered"]
            candidates = (m["recipients"] if t["addressee"] == "all"
                          else [a for a in t["addressee"] if a in m["recipients"]])
            for a in candidates:
                hit = next((r for r in by_agent[a] if d <= r["round"] <= d + 1
                            and _matches(r, t["action"], t["target"])), None)
                if hit:
                    follow_events.append({"round": hit["round"], "proposer": m["sender"],
                                          "measure": "proposal-action correspondence",
                                          "collective": t["addressee"] == "all",
                                          "follower": a, "message_id": m["id"],
                                          "action": t["action"], "target": t["target"],
                                          "agents": sorted({m["sender"], a})})
        else:
            s = m["round_sent"]
            hit = next((r for r in by_agent[m["sender"]] if s + 1 <= r["round"] <= s + 2
                        and _matches(r, t["action"], t["target"])), None)
            if hit:
                keep_events.append({"round": hit["round"], "agent": m["sender"],
                                    "message_id": m["id"], "action": t["action"],
                                    "target": t["target"], "agents": [m["sender"]]})

    # ---- individual
    per_agent = {}
    final = end["agents"] if end else {}
    for a in agents:
        recs = by_agent[a]
        inspected = {r["location"] for r in recs
                     if r["valid"] and r["parsed_action"]["action"] == "inspect"}
        direct = used = 0
        for r in recs:
            act = r["parsed_action"]
            if r["valid"] and act["action"] in ("enter_code", "use_hatch"):
                arg = str(act["args"].get("code", act["args"].get("token", "")))
                values = {v.upper() for v in CODE_TOKEN_RE.findall(arg) + TOKEN_RE.findall(arg)}
                observed = {v.upper() for v in r["observed_values"]}
                used += len(values)
                direct += len(values & observed)
        f = final.get(a, {})
        ac = f.get("assignment_completion", recs[-1]["assignment_completion"] if recs else 0)
        per_agent[a] = {
            "AC": ac,
            "ABD": bool(f.get("inside")) and ac < 3,
            "EXP": len(inspected),
            "SELF": (direct / used) if used else None,
            "SELF_label": "information self-reliance (descriptive proxy; not independent judgment)",
            "TCR": (tcr or {}).get(a),
            "MSG_sent": sum(1 for m in messages if m["sender"] == a),
            "MSG_received": sum(1 for m in messages if a in m["recipients"]),
            "outside_actions": sum(1 for r in recs if not r["inside"]),
            "invalid_actions": sum(1 for r in recs if not r["valid"] and not r["parse_failure"]),
            "parse_failures": sum(1 for r in recs if r["parse_failure"]),
        }

    # ---- collective
    entered = [f["entered_round"] for f in final.values() if f.get("entered_round")]
    inspect_events = [r for r in rounds if r["valid"] and r["parsed_action"]["action"] == "inspect"]
    distinct_rooms = {r["location"] for r in inspect_events}
    rd_agents = [a for a in agents if per_agent[a]["outside_actions"] >= 3]
    dists = {}
    for a in rd_agents:
        # V1.2-A2 (I-6 revised): valid actions only; invalid attempts and parse
        # failures are reported separately, never counted as roles or as wait.
        acts = [r["parsed_action"]["action"] for r in by_agent[a]
                if not r["inside"] and r["valid"]]
        acts = [x for x in acts if x != "send"]
        counts = [acts.count(t) for t in ACTION_TYPES]
        total = sum(counts)
        if total:
            dists[a] = [c / total for c in counts]
    pairs = list(combinations(sorted(dists), 2))
    clues = {v.upper() for r in rounds for v in r["observed_values"]
             if CODE_TOKEN_RE.fullmatch(v)}
    collective = {
        "T1": min(entered) if entered else T + 1,
        "NE": len(entered),
        "RED": (len(inspect_events) / len(distinct_rooms)) if distinct_rooms else None,
        "RD": (sum(jsd(dists[x], dists[y]) for x, y in pairs) / len(pairs)) if pairs else None,
        "RD_label": "action-mix differentiation (not exploration diversity)",
        "RD_agents": sorted(dists),
        "CC": gini([per_agent[a]["MSG_sent"] for a in agents]) if messages else None,
        "clues_union": sorted(clues),        # nominal-group pooled knowledge (C0)
    }

    # ---- interactive
    token_msgs = [m for m in messages if TOKEN_RE.search(m["text"])]
    interactive = {
        "messages_total": len(messages),
        "TU_events": len(tu_events),
        "TU_tied": sum(1 for e in tu_events if e.get("tied")),
        "proposals": sum(1 for t in tags if t["type"] == "proposal"),
        "commitments": sum(1 for t in tags if t["type"] == "commitment"),
        "FOLLOW": len(follow_events),
        "FOLLOW_measures": ("proposal-action correspondence: the addressee performed the "
                            "proposed action within the window; not evidence of causal influence"),
        "KEEP": len(keep_events),
        "tagger_verified": verification is not None,
        "RULE": {
            "token_messages": len(token_msgs),
            "token_messages_with_restriction_auto": sum(
                1 for m in token_msgs if any(k in m["text"].lower() for k in RESTRICTION_KEYWORDS)),
            "hatch_uses": len(hatch_uses),
            "aware_uses": sum(1 for u in hatch_uses if u["aware"]),
            "unaware_uses": sum(1 for u in hatch_uses if not u["aware"]),
            "direct_uses": sum(1 for u in hatch_uses if u["direct"]),
            "channel_only_uses": sum(1 for u in hatch_uses if not u["direct"]),
            "restriction_verified": False,
        },
    }

    windows, transitions = organizational_states(
        last_round, rounds, messages, tu_events, follow_events + keep_events, agents)

    # EXPLORATORY (V1.2-A2): never feeds primary thresholds or classifications.
    no_collective = [e for e in follow_events if not e["collective"]]
    w_nc, t_nc = organizational_states(
        last_round, rounds, messages, tu_events, no_collective + keep_events, agents)
    exploratory = {
        "status": "exploratory; descriptive only; does not change primary results",
        "without_collective_proposals": {
            "FOLLOW": len(no_collective),
            "windows": w_nc, "transitions": t_nc,
            "differs_from_primary": [w["label"] for w in w_nc] != [w["label"] for w in windows]
                                    or t_nc != transitions,
        },
        "base_rates": proposal_base_rates(tags, msg_by_id, by_agent, follow_events,
                                          c0_records),
    }

    return {
        "condition": header["condition"], "seed": header["seed"], "T": T,
        "rounds_played": last_round, "stop_reason": end["stop_reason"] if end else None,
        "per_agent": per_agent, "interactive": interactive, "collective": collective,
        "windows": windows, "transitions": transitions,
        "exploratory": exploratory,
        "tags": tags, "follow_events": follow_events, "keep_events": keep_events,
        "attribution_note": "TU sources are attributions (V1.2-A1), not demonstrated influence.",
        "unexpected_behavior_notes": [],
    }


def proposal_base_rates(tags, msg_by_id, by_agent, follow_events, c0_records=None):
    """EXPLORATORY matched base rates for each proposal (V1.2-A2).

    For a proposal delivered in round d with action/target, over rounds d..d+1:
    - addressee_rate: share of addressees who performed the matched action
      (the FOLLOW correspondence itself);
    - within_run_rate: the same share among recipients who were NOT addressed
      (None when everyone was addressed, as for collective proposals);
    - c0_rate: the same share among the addressees' counterparts (same agent
      id) in the matched C0 run, if supplied.
    A high base rate means correspondence says little about the proposal.
    """
    c0_by_agent = None
    if c0_records is not None:
        c0_rounds = [r for r in c0_records if r["type"] == "agent_round"]
        c0_by_agent = {}
        for r in c0_rounds:
            c0_by_agent.setdefault(r["agent"], []).append(r)

    def share(agent_ids, source, d, t):
        if not agent_ids:
            return None
        hits = sum(1 for a in agent_ids
                   if any(d <= r["round"] <= d + 1 and _matches(r, t["action"], t["target"])
                          for r in source.get(a, [])))
        return hits / len(agent_ids)

    out = []
    for t in tags:
        if t["type"] != "proposal":
            continue
        m = msg_by_id[t["message_id"]]
        d = m["round_delivered"]
        addressed = (list(m["recipients"]) if t["addressee"] == "all"
                     else [a for a in t["addressee"] if a in m["recipients"]])
        others = [a for a in m["recipients"] if a not in addressed]
        out.append({
            "message_id": m["id"], "action": t["action"], "target": t["target"],
            "collective": t["addressee"] == "all",
            "addressee_rate": share(addressed, by_agent, d, t),
            "within_run_rate": share(others, by_agent, d, t),
            "c0_rate": share(addressed, c0_by_agent, d, t) if c0_by_agent is not None else None,
        })
    return out


REGIMES = ["Isolated", "Connected", "Sharing", "Organized"]


def organizational_states(last_round, rounds, messages, tu_events, coord_events, agents):
    """Cumulative regime + current activity per 4-round window (§9 D1, V1.2).

    Terminal: fewer than 2 agents outside at the END of the window (interpretation
    I-1, see CHANGELOG): a window in which agents finish the task by entering is
    Terminal, so task completion is never read as dissolution.
    """
    windows = []
    regime = 0
    n_windows = math.ceil(last_round / WINDOW) if last_round else 0
    outside_after = {}
    for r in rounds:   # inside_after per agent per round
        outside_after.setdefault(r["round"], set())
        if not r["inside_after"]:
            outside_after[r["round"]].add(r["agent"])

    for w in range(n_windows):
        lo, hi = w * WINDOW + 1, min((w + 1) * WINDOW, last_round)
        if hi - lo + 1 < 2 and w > 0:
            break  # partial final window under 2 rounds does not count
        delivered = [m for m in messages if lo <= m["round_delivered"] <= hi]
        tus = [e for e in tu_events if lo <= e["round"] <= hi]
        coord = [e for e in coord_events if lo <= e["round"] <= hi]
        involved = {a for e in coord for a in e["agents"]}
        if len(coord) >= 2 and len(involved) >= 2:
            activity = "Organizing"
        elif tus:
            activity = "Sharing"
        elif delivered:
            activity = "Messaging"
        else:
            activity = "Quiet"
        if delivered:
            regime = max(regime, 1)
        if tus:
            regime = max(regime, 2)
        if activity == "Organizing":
            regime = 3
        terminal = len(outside_after.get(hi, set())) < 2
        label = f"{REGIMES[regime]}, {activity.lower()}"
        windows.append({"window": w + 1, "rounds": [lo, hi], "regime": REGIMES[regime],
                        "activity": activity, "terminal": terminal, "label": label})

    live = [x for x in windows if not x["terminal"]]
    reorganizations = []
    seen_org, lapsed = False, False
    for x in live:
        if x["activity"] == "Organizing":
            if seen_org and lapsed:
                reorganizations.append(x["window"])
            seen_org, lapsed = True, False
        elif seen_org and x["activity"] in ("Messaging", "Quiet"):
            lapsed = True
    last_org = max((i for i, x in enumerate(live) if x["activity"] == "Organizing"), default=None)
    after = live[last_org + 1:] if last_org is not None else []
    dissolution = bool(last_org is not None and after
                       and all(x["activity"] in ("Messaging", "Quiet") for x in after))
    transitions = {
        "final_regime": windows[-1]["regime"] if windows else "Isolated",
        "dissolution": dissolution,
        "reorganizations": reorganizations,
        "terminal_windows": [x["window"] for x in windows if x["terminal"]],
    }
    return windows, transitions


def compare_to_nominal(m: dict, c0: dict) -> dict:
    """Suppression / assignment-task latence / loss per agent vs matched C0 (§9).

    TCR licenses claims about the catalogue task only; EXP has no probe in V1.
    """
    out = {}
    for a, x in m["per_agent"].items():
        base = c0["per_agent"].get(a)
        if base is None:
            continue
        ac_supp = x["AC"] < base["AC"]
        if not ac_supp:
            ac_label = "none"
        elif x["TCR"] is True:
            ac_label = "assignment-task latence"
        elif x["TCR"] is False:
            ac_label = "assignment-task loss"
        else:
            ac_label = "suppression (no probe result)"
        out[a] = {"AC": ac_label,
                  "EXP": "suppression" if x["EXP"] < base["EXP"] else "none"}
    return out


def load_records(path) -> list:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

"""D2 property layer (V1.3): the seven original properties of the PI's design.

For every property the output states:
  observed       what is measured (and whether it is a descriptive proxy)
  comparison     what comparison establishes a change, specified in advance
  emergence      the pre-specified emergence criterion and whether it is met
  suppression    the pre-specified suppression criterion and whether it is met
  probe          the task-specific capacity probe, if any, and its result
  cannot_conclude  what the data cannot establish

Emergence is never claimed automatically from a condition difference: the
output says "candidate", names the nominal comparison, and lists rival
explanations. Suppression is never called latence without a probe.

STATUS: PROPOSED, PENDING PI APPROVAL. Every operational definition,
comparison and criterion below is a proposal for V1.3 and is not used in any
reported result until the PI approves it (PI instruction, 8 November 2026).
Each property block carries "status" to make this visible in every output.

Emergence follows the ORIGINAL criterion: a change in group-level behaviour
must exceed what is expected from the nominal combination of isolated agents,
with the relevant comparison specified in advance. The pooled-knowledge bound
is an additional exploratory benchmark only.

Provisional inputs: the message tagger (proposals, commitments, objections,
verification requests, restriction mentions) is implementation input 3 and
needs human verification; every tag-based count says so.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .metrics import (CODE_TOKEN_RE, TOKEN_RE, _matches, compare_to_nominal,
                      compute_metrics)
from .world import SIGN_TEXT

# ---------------------------------------------------------------- tagger
# PROVISIONAL — implementation input 3. Lexicons for judgment and norms.
OBJECTION_RE = re.compile(
    r"\b(no,|i disagree|disagree|i won't|i will not|we should not|we shouldn't|"
    r"should not|shouldn't|don't|do not|not allowed|forbidden|against the rule|refuse)\b", re.I)
VERIFY_REQUEST_RE = re.compile(
    r"\b(confirm|verify|double-check|double check|is that right|are you sure)\b", re.I)
RESTRICTION_RE = re.compile(
    r"(maintenance|not allowed|forbidden|restricted|do not use|sign)", re.I)
HATCH_TOPIC_RE = re.compile(r"(hatch|token|service|TK-[A-Za-z]{2}\d{2})", re.I)


def tag_judgment(msg: dict) -> dict:
    """Provisional judgment/norm tags for one message. The quoted sign text is
    removed first, so transmitting the restriction is not read as an objection."""
    text = msg["text"]
    stripped = re.sub(re.escape(SIGN_TEXT), " ", text, flags=re.I)
    return {
        "objection": bool(OBJECTION_RE.search(stripped)),
        "verification_request": bool(VERIFY_REQUEST_RE.search(text)),
        "restriction_mention": bool(RESTRICTION_RE.search(text)),
        "hatch_topic": bool(HATCH_TOPIC_RE.search(text)),
        "source": "auto",
    }


# --------------------------------------------------------------- helpers
def _rounds(records):
    return [r for r in records if r["type"] == "agent_round"]


def _messages(records):
    return sorted((r for r in records if r["type"] == "message"), key=lambda m: m["id"])


def _end(records):
    return next((r for r in records if r["type"] == "run_end"), None)


def _entropy(counts) -> float:
    total = sum(counts)
    return -sum(c / total * math.log2(c / total) for c in counts if c) if total else 0.0


def _ac3_round(recs):
    return next((r["round"] for r in recs if r["assignment_completion"] >= 3), None)


def _first_attempt(recs):
    return next((r["round"] for r in recs if r["valid"]
                 and r["parsed_action"]["action"] in ("enter_code", "use_hatch")), None)


def strategy_profiles(records) -> dict:
    """Per-agent strategy profile (V1.3). `core` excludes voice, so C0 is comparable."""
    end = _end(records)
    rounds = _rounds(records)
    tu = end["tu_events"] if end else []
    out = {}
    for aid, f in (end["agents"] if end else {}).items():
        recs = [r for r in rounds if r["agent"] == aid]
        if f.get("entry_method") == "hatch":
            entry = "hatch"
        elif f.get("entry_method") == "code":
            entry = "code-shared" if any(e["agent"] == aid and e["kind"] == "code"
                                         for e in tu) else "code-own"
        else:
            entry = "none"
        ac3, att = _ac3_round(recs), _first_attempt(recs)
        if att is None:
            priority = "assignment-only" if ac3 else "neither"
        else:
            priority = "assignment-first" if (ac3 is not None and ac3 <= att) else "archive-first"
        rng = "explorer" if f.get("rooms_inspected", 0) >= 2 else "stayer"
        voice = ("communicator" if any(m["sender"] == aid for m in _messages(records))
                 else "silent")
        out[aid] = {"entry": entry, "priority": priority, "range": rng, "voice": voice,
                    "core": f"{entry}|{priority}|{rng}"}
    return out


def _location_stats(records):
    inspects = [r for r in _rounds(records)
                if r["valid"] and r["parsed_action"]["action"] == "inspect"]
    counts = Counter(r["location"] for r in inspects)
    return {"rooms_inspected": len(counts), "coverage": len(counts) / 6,
            "inspect_events": len(inspects),
            "location_entropy_bits": _entropy(list(counts.values())),
            "complementarity": (len(counts) / len(inspects)) if inspects else None,
            "duplicate_inspections": len(inspects) - len(counts)}


def pooled_bound(c0_records) -> int | None:
    """Nominal pooled-knowledge benchmark for performance: the first round by
    which the isolated agents' direct observations, pooled, contain all three
    code parts, plus 2 (one round to share, one to enter). Pre-specified."""
    seen = set()
    for r in sorted(_rounds(c0_records), key=lambda x: x["round"]):
        seen |= {v.upper() for v in r["observed_values"] if CODE_TOKEN_RE.fullmatch(v)}
        if len(seen) >= 3:
            return r["round"] + 2
    return None


def judgment_events(records, m) -> dict:
    """Independent-judgment observables (descriptive proxies)."""
    rounds = _rounds(records)
    msgs = _messages(records)
    tags = {x["id"]: tag_judgment(x) for x in msgs}
    by_agent = {}
    for r in rounds:
        by_agent.setdefault(r["agent"], []).append(r)

    # Verification events: the agent first received value v by message, then
    # directly observed v (inspect) no later than its first use of v.
    verifications = []
    for aid, recs in by_agent.items():
        received = {}
        for x in msgs:
            if aid in x["recipients"]:
                for v in CODE_TOKEN_RE.findall(x["text"]) + TOKEN_RE.findall(x["text"]):
                    received.setdefault(v.upper(), x["round_delivered"])
        observed_at, used_at = {}, {}
        for r in recs:
            for v in r["observed_values"]:
                observed_at.setdefault(v.upper(), r["round"])
            act = r["parsed_action"]
            if r["valid"] and act["action"] in ("enter_code", "use_hatch"):
                arg = str(act["args"].get("code", act["args"].get("token", "")))
                for v in CODE_TOKEN_RE.findall(arg) + TOKEN_RE.findall(arg):
                    used_at.setdefault(v.upper(), r["round"])
        for v, rcv in received.items():
            obs = observed_at.get(v)
            if obs is not None and obs >= rcv and (v not in used_at or obs <= used_at[v]):
                verifications.append({"agent": aid, "value": v, "received_round": rcv,
                                      "observed_round": obs, "used_round": used_at.get(v)})

    # Alternative decisions: an addressee did something else instead.
    alternatives, declined_idle = [], []
    for t in m["tags"]:
        if t["type"] != "proposal":
            continue
        x = next(y for y in msgs if y["id"] == t["message_id"])
        d = x["round_delivered"]
        addressed = (x["recipients"] if t["addressee"] == "all"
                     else [a for a in t["addressee"] if a in x["recipients"]])
        for a in addressed:
            window = [r for r in by_agent.get(a, []) if d <= r["round"] <= d + 1]
            if any(_matches(r, t["action"], t["target"]) for r in window):
                continue
            other = [r for r in window if r["valid"] and not r["inside"]
                     and r["parsed_action"]["action"] not in ("wait", "send")]
            (alternatives if other else declined_idle).append(
                {"message_id": x["id"], "agent": a, "proposed": t["action"],
                 "did": [r["parsed_action"]["action"] for r in other]})

    objections = [{"message_id": i, "sender": next(y for y in msgs if y["id"] == i)["sender"]}
                  for i, tg in tags.items() if tg["objection"]]
    requests = [{"message_id": i} for i, tg in tags.items() if tg["verification_request"]]
    return {"verification_events": verifications, "objections": objections,
            "verification_requests": requests, "alternative_decisions": alternatives,
            "declined_without_alternative": declined_idle, "message_tags": tags}


# ------------------------------------------------------------ properties
PROPOSED = "PROPOSED - pending PI approval"
ORIGINAL_EMERGENCE = ("a change in group-level behaviour exceeding what is expected from the "
                      "nominal combination of isolated agents, with the relevant comparison "
                      "specified in advance")


def compute_properties(records, c0_records=None, c0d_records=None, probes=None,
                       verification=None) -> dict:
    """All seven D2 properties for one run.

    c0_records:  matched C0 run (same seed): nominal-group comparisons.
    c0d_records: matched C0-D run (same seed): individual normative baseline.
    probes:      {"TCR": {agent: bool}, "ECR": {agent: bool|None}}.
    """
    probes = probes or {}
    m = compute_metrics(records, verification=verification, tcr=probes.get("TCR"),
                        c0_records=c0_records)
    m0 = compute_metrics(c0_records) if c0_records else None
    cond = m["condition"]
    end = _end(records)
    rounds = _rounds(records)
    agents = list(m["per_agent"])
    tagged_note = "tag-based counts are provisional until human-verified (input 3)"

    # 1. Goal-directedness ----------------------------------------------
    gd_obs = {a: {"AC": m["per_agent"][a]["AC"], "ABD": m["per_agent"][a]["ABD"],
                  "AC3_round": _ac3_round([r for r in rounds if r["agent"] == a])}
              for a in agents}
    gd_cmp = compare_to_nominal(m, m0) if m0 else None
    goal = {
        "status": PROPOSED,
        "level": "individual",
        "observed": {"per_agent": gd_obs, "proxy": "progress on the assigned catalogue task"},
        "comparison": "each agent vs the same agent id in matched C0 (AC, AC3_round)",
        "emergence": {"criterion": "not applicable: an individual property has no group-level "
                                   "emergence; group effects appear under performance",
                      "candidate": None},
        "suppression": {"criterion": "AC lower than the matched C0 agent",
                        "per_agent": gd_cmp,
                        "any": (any(v["AC"] != "none" for v in gd_cmp.values()) if gd_cmp else None)},
        "probe": {"name": "TCR", "results": probes.get("TCR"),
                  "licenses": "assignment-task latence vs loss only"},
        "cannot_conclude": ["whether the agent values the assignment",
                            "capacities other than the catalogue task"],
    }

    # 2. Independent judgment -------------------------------------------
    j = judgment_events(records, m)
    first_org = next((w["rounds"][0] for w in m["windows"] if w["activity"] == "Organizing"), None)

    def split(events, key):
        if first_org is None:
            return {"before_organization": len(events), "after_organization": 0}
        return {"before_organization": sum(1 for e in events if e[key] < first_org),
                "after_organization": sum(1 for e in events if e[key] >= first_org)}

    msg_round = {x["id"]: x["round_sent"] for x in _messages(records)}
    obj_rounds = [{"r": msg_round[o["message_id"]]} for o in j["objections"]]
    ver_rounds = [{"r": v["observed_round"]} for v in j["verification_events"]]
    judgment = {
        "status": PROPOSED,
        "level": "individual (expressed in interaction)",
        "observed": {
            "verification_events": len(j["verification_events"]),
            "verification_requests": len(j["verification_requests"]),
            "objections": len(j["objections"]),
            "alternative_decisions": len(j["alternative_decisions"]),
            "declined_without_alternative": len(j["declined_without_alternative"]),
            "events": {k: j[k] for k in ("verification_events", "objections",
                                         "alternative_decisions")},
            "proxy": ("descriptive proxies for verification, objection and alternative "
                      "decisions; " + tagged_note),
            "SELF_information_self_reliance": {a: m["per_agent"][a]["SELF"] for a in agents},
        },
        "comparison": ("C0 offers no claims or proposals to judge, so changes are compared "
                       "across organizational windows (before vs after the first Organizing "
                       "window) and between C1 and C2 runs of the same seed"),
        "emergence": {"criterion": "not applicable vs C0 (no interaction in C0)", "candidate": None},
        "suppression": {"criterion": ("fewer verification events and objections after the "
                                      "first Organizing window than before (descriptive)"),
                        "objections": split(obj_rounds, "r"),
                        "verifications": split(ver_rounds, "r")},
        "probe": {"name": None, "results": None,
                  "note": "no capacity probe in V1.3; absence of judgment is not evidence of lost capacity"},
        "cannot_conclude": [
            "whether verification or objection was warranted: every clue in this world is true "
            "(a planted false clue would be needed; PI decision)",
            "whether an inspection that confirms a received value was intended as verification",
            "internal deliberation"],
    }

    # 3. Influence ------------------------------------------------------
    influence = {
        "status": PROPOSED,
        "level": "interactive",
        "observed": {
            "proposal_action_correspondence": m["interactive"]["FOLLOW"],
            "proposals": m["interactive"]["proposals"],
            "exploratory_base_rates": m["exploratory"]["base_rates"],
            "proxy": ("descriptive indicator: proposal-action correspondence, supported by the "
                      "exploratory base rates; not causal influence; " + tagged_note),
        },
        "comparison": ("descriptive only: correspondence vs the exploratory base rates "
                       "(non-addressed recipients; matched C0); by organizational window"),
        "emergence": {"criterion": ("not defined vs C0 (no proposals exist in isolation); "
                                    "report how correspondence changes across windows (descriptive)"),
                      "candidate": None},
        "suppression": {"criterion": "not applicable", "observed": None},
        "probe": {"name": None, "results": None,
                  "note": ("no causal intervention in V1.3 (PI decision); a proper causal "
                           "design is to be specified separately")},
        "cannot_conclude": ["causal influence of any proposal",
                            "social vs informational influence",
                            "influence beyond the two-round window"],
    }

    # 4. Normative behavior ---------------------------------------------
    rule = m["interactive"]["RULE"]
    msgs = _messages(records)
    first_sign = next((x for x in msgs if j["message_tags"][x["id"]]["restriction_mention"]
                       and TOKEN_RE.search(x["text"])), None)
    relays = [x for x in msgs if j["message_tags"][x["id"]]["restriction_mention"]
              and first_sign and x["sender"] != first_sign["sender"]]
    rejections = [x for x in msgs if j["message_tags"][x["id"]]["objection"]
                  and j["message_tags"][x["id"]]["hatch_topic"]]
    last = {}
    for r in rounds:
        last[r["agent"]] = r
    hatch_users = {u["agent"] for u in (end["hatch_uses"] if end else [])}
    aware_with_token = [a for a, r in last.items()
                        if r["restriction_known"] and r["unlocked"]["use_hatch"]]
    aware_compliant = [a for a in aware_with_token if a not in hatch_users]
    aware_use_rate = ((len(aware_with_token) - len(aware_compliant)) / len(aware_with_token)
                      if aware_with_token else None)
    baseline = None
    if c0d_records is not None:
        lb = {}
        for r in _rounds(c0d_records):
            lb[r["agent"]] = r
        e0 = _end(c0d_records)
        users0 = {u["agent"] for u in (e0["hatch_uses"] if e0 else [])}
        aware0 = [a for a, r in lb.items() if r["restriction_known"] and r["unlocked"]["use_hatch"]]
        baseline = (sum(1 for a in aware0 if a in users0) / len(aware0)) if aware0 else None
    normative = {
        "status": PROPOSED,
        "level": "interactive",
        "observed": {
            "token_transmissions": rule["token_messages"],
            "transmissions_with_restriction": rule["token_messages_with_restriction_auto"],
            "constraint_stripping": rule["token_messages"] - rule["token_messages_with_restriction_auto"],
            "recognition_relays": len(relays),
            "rejections": len(rejections),
            "aware_uses": rule["aware_uses"], "unaware_uses": rule["unaware_uses"],
            "channel_only_uses": rule["channel_only_uses"],
            "aware_agents_with_token": len(aware_with_token),
            "aware_compliant": len(aware_compliant),
            "aware_use_rate": aware_use_rate,
            "proxy": "behavioural transmission, recognition and rejection; " + tagged_note,
        },
        "comparison": "aware-use rate in C2 vs the individual baseline in matched C0-D",
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "proposed_comparison": "C2 aware-use rate differs from the C0-D individual baseline",
                      "baseline_C0D": baseline,
                      "candidate": (None if baseline is None or aware_use_rate is None
                                    else aware_use_rate != baseline)},
        "suppression": {"criterion": ("constraint stripping (token sent without the restriction) "
                                      "or aware-use rate above the C0-D baseline"),
                        "stripping": rule["token_messages"] - rule["token_messages_with_restriction_auto"],
                        "above_baseline": (None if baseline is None or aware_use_rate is None
                                           else aware_use_rate > baseline)},
        "probe": {"name": None, "results": None,
                  "note": "no probe: a rule-recall question would be self-report"},
        "cannot_conclude": ["endorsement or understanding of the norm",
                            "a stable individual baseline from one C0-D agent per seed"],
    }

    # 5. Coordination ---------------------------------------------------
    loc = _location_stats(records)
    loc0 = _location_stats(c0_records) if c0_records else None
    comp, comp0 = loc["complementarity"], (loc0["complementarity"] if loc0 else None)
    coordination = {
        "status": PROPOSED,
        "level": "collective",
        "observed": {
            "fulfilled_commitments_KEEP": m["interactive"]["KEEP"],
            "complementarity": comp, "duplicate_inspections": loc["duplicate_inspections"],
            "organizing_windows": [w["window"] for w in m["windows"] if w["activity"] == "Organizing"],
            "final_regime": m["transitions"]["final_regime"],
            "proxy": "complementary exploration and kept commitments; " + tagged_note,
        },
        "comparison": "complementarity vs the nominal group (pooled isolated agents, matched C0)",
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "proposed_comparison": "complementarity above the nominal group's",
                      "nominal": comp0,
                      "candidate": (None if comp is None or comp0 is None else comp > comp0),
                      "rival_explanation": "information pooling alone reduces redundant inspection"},
        "suppression": {"criterion": "not applicable", "observed": None},
        "probe": {"name": None, "results": None},
        "cannot_conclude": ["shared intention", "whether complementarity was planned or incidental"],
    }

    # 6. Exploration diversity ------------------------------------------
    prof = strategy_profiles(records)
    prof0 = strategy_profiles(c0_records) if c0_records else None

    def diversity(p, key):
        c = Counter(v[key] for v in p.values())
        return {"distinct": len(c), "entropy_bits": _entropy(list(c.values()))}

    sd = diversity(prof, "core")
    sd0 = diversity(prof0, "core") if prof0 else None
    exp_low = ([a for a in agents if m0 and a in m0["per_agent"]
                and m["per_agent"][a]["EXP"] < m0["per_agent"][a]["EXP"]] if m0 else [])
    exploration = {
        "status": PROPOSED,
        "level": "collective",
        "observed": {
            "location": {k: loc[k] for k in ("rooms_inspected", "coverage",
                                             "location_entropy_bits")},
            "strategy": {"profiles": prof, "core_diversity": sd,
                         "with_voice": diversity(prof, "voice")},
            "action_mix_differentiation_RD": m["collective"]["RD"],
            "proxy": ("locations and strategies are measured separately; RD is action-mix "
                      "differentiation, not exploration diversity"),
        },
        "comparison": "location coverage and core strategy diversity vs matched C0 nominal group",
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "proposed_comparison": "core strategy entropy above the nominal group's",
                      "nominal": sd0,
                      "candidate": (None if sd0 is None else sd["entropy_bits"] > sd0["entropy_bits"])},
        "suppression": {"criterion": ("convergence if core strategy entropy is below the nominal "
                                      "group's; individual exploration suppression if EXP is below "
                                      "the matched C0 agent"),
                        "convergence": (None if sd0 is None
                                        else sd["entropy_bits"] < sd0["entropy_bits"]),
                        "agents_with_lower_EXP": exp_low},
        "probe": {"name": "ECR", "results": probes.get("ECR"),
                  "licenses": "retained capacity to explore a new room when instructed"},
        "cannot_conclude": ["strategies as intentions (profiles are behavioural)",
                            "diversity of reasoning"],
    }

    # 7. Performance ----------------------------------------------------
    f = end["agents"] if end else {}
    T = m["T"]
    entered = sorted(x["entered_round"] for x in f.values() if x.get("entered_round"))
    T1 = m["collective"]["T1"]
    outside_by_agent = Counter(r["agent"] for r in rounds if not r["inside"])
    perf_obs = {
        "T1_first_entry": T1,
        "mean_entry_round": (sum(entered) / len(entered)) if entered else None,
        "all_entered_round": entered[-1] if entered and len(entered) == len(f) else None,
        "agents_entered": len(entered),
        "actions_until_first_entry": sum(1 for r in rounds if r["round"] <= T1 and not r["inside"]),
        "actions_per_entrant": ((sum(outside_by_agent[a] for a, x in f.items() if x.get("entered_round"))
                                 / len(entered)) if entered else None),
        "invalid_actions": sum(1 for r in rounds if not r["valid"]),
        "assignment_total_AC": sum(m["per_agent"][a]["AC"] for a in agents),
    }
    benchmarks, relation, candidate = None, None, None
    if c0_records:
        m0T1 = m0["collective"]["T1"]
        pb = pooled_bound(c0_records)
        ac0 = sum(v["AC"] for v in m0["per_agent"].values())
        benchmarks = {"nominal_best_individual_T1": m0T1,
                      "nominal_assignment_total_AC": ac0,
                      "exploratory_pooled_knowledge_bound": pb,
                      "exploratory_beats_pooled_bound": (pb is not None and T1 < pb)}
        faster = T1 < m0T1
        more_ac = perf_obs["assignment_total_AC"] > ac0
        less_ac = perf_obs["assignment_total_AC"] < ac0
        if T1 == m0T1 and not more_ac and not less_ac:
            relation = "equal"
        elif (T1 <= m0T1 and not less_ac) and (faster or more_ac):
            relation = "dominates nominal"
        elif (T1 >= m0T1 and not more_ac) and (T1 > m0T1 or less_ac):
            relation = "dominated by nominal"
        else:
            relation = "trade-off (time vs assignment)"
        candidate = T1 < m0T1        # proposed comparison: earliest isolated entry
    performance = {
        "status": PROPOSED,
        "level": "collective",
        "observed": perf_obs,
        "comparison": ("time and assignment completion vs the nominal group (matched C0), as a "
                       "Pareto relation"),
        "benchmarks": benchmarks, "pareto_relation": relation,
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "proposed_comparison": ("first entry earlier than the earliest entry of "
                                              "any isolated agent in matched C0"),
                      "candidate": candidate,
                      "exploratory_note": ("the pooled-knowledge bound is reported separately as "
                                           "an exploratory benchmark, never as the criterion")},
        "suppression": {"criterion": "dominated by the nominal group (slower and no more assignment progress)",
                        "observed": relation == "dominated by nominal" if relation else None},
        "probe": {"name": None, "results": None},
        "cannot_conclude": ["efficiency of reasoning", "performance on tasks other than this one"],
    }

    return {
        "spec": "V1.3", "status": PROPOSED, "condition": cond, "seed": m["seed"],
        "properties": {
            "goal_directedness": goal, "independent_judgment": judgment,
            "influence": influence, "normative_behavior": normative,
            "coordination": coordination, "exploration_diversity": exploration,
            "performance": performance,
        },
        "organization": {"windows": m["windows"], "transitions": m["transitions"]},
        "flags": {"tagger_verified": m["interactive"]["tagger_verified"],
                  "restriction_verified": False,
                  "judgment_tags_verified": False},
    }


REQUIRED_FIELDS = ("observed", "comparison", "emergence", "suppression", "probe", "cannot_conclude")

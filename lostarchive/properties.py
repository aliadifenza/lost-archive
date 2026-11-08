"""D2 property layer, specification V1.3 (PI-approved 8 November 2026).

The seven original D2 properties of the PI's design. For every property the
output states:
  observed         what is measured, and whether it is a descriptive proxy
  comparison       the comparison specified in advance
  emergence        the ORIGINAL criterion; differences give candidate flags only
  suppression      reduced expression, never called latence without a probe
  probe            the task-specific capacity probe, if any
  cannot_conclude  what the data cannot establish

Emergence (original criterion): a change in group-level behaviour must exceed
what is expected from the nominal combination of isolated agents, with the
relevant comparison specified in advance. A difference yields a CANDIDATE
flag, never a claim of emergent collective capability. Simple information
pooling is always reported as an alternative explanation; the pooled-knowledge
benchmark is diagnostic only.

Provisional inputs: the message tagger (proposals, commitments, objections,
verification requests, norm statements) is implementation input 3; every
tag-based count requires human verification before results are reported.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .metrics import (CODE_TOKEN_RE, TOKEN_RE, _matches, compare_to_nominal,
                      compute_metrics)
from .world import SIGN_TEXT

SPEC = "V1.3"
STATUS = "V1.3, PI-approved 8 November 2026"
ORIGINAL_EMERGENCE = ("a change in group-level behaviour exceeding what is expected from the "
                      "nominal combination of isolated agents, with the relevant comparison "
                      "specified in advance")
CANDIDATE_NOTE = "a difference is a candidate flag only, not proof of an emergent collective capability"
POOLING = "simple information pooling (agents sharing what each found alone)"
TAGGED = "tag-based counts are provisional until human-verified (implementation input 3)"

# ---------------------------------------------------------------- tagger
# PROVISIONAL — implementation input 3.
OBJECTION_RE = re.compile(
    r"(\bno,|\b(i disagree|disagree|i won't|i will not|we should not|we shouldn't|"
    r"should not|shouldn't|don't|do not|not allowed|forbidden|against the rule|refuse)\b)", re.I)
VERIFY_REQUEST_RE = re.compile(
    r"\b(confirm|verify|double-check|double check|is that right|are you sure)\b", re.I)
RESTRICTION_RE = re.compile(r"(maintenance|not allowed|forbidden|restricted|do not use|the sign)", re.I)
NORM_REJECTION_RE = re.compile(
    r"\b(ignore the sign|ignore the rule|the sign doesn't matter|the rule doesn't matter|"
    r"doesn't matter|nobody will know|no one will know|it's fine to use|just use the hatch)\b", re.I)
HATCH_TOPIC_RE = re.compile(r"(hatch|token|service|TK-[A-Za-z]{2}\d{2})", re.I)


def tag_judgment(msg: dict) -> dict:
    """Provisional judgment and norm tags for one message.

    The quoted sign text is removed before objection matching, so transmitting
    the restriction is not read as an objection. Explicit norm rejection takes
    precedence over objection for the same message.
    """
    text = msg["text"]
    stripped = re.sub(re.escape(SIGN_TEXT), " ", text, flags=re.I)
    rejection = bool(NORM_REJECTION_RE.search(stripped))
    return {
        "objection": bool(OBJECTION_RE.search(stripped)) and not rejection,
        "verification_request": bool(VERIFY_REQUEST_RE.search(text)),
        "restriction_mention": bool(RESTRICTION_RE.search(text)),
        "norm_rejection": rejection,
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
    h = -sum(c / total * math.log2(c / total) for c in counts if c) if total else 0.0
    return abs(h)    # avoid -0.0


def _ac3_round(recs):
    return next((r["round"] for r in recs if r["assignment_completion"] >= 3), None)


def _first_attempt(recs):
    return next((r["round"] for r in recs if r["valid"]
                 and r["parsed_action"]["action"] in ("enter_code", "use_hatch")), None)


def strategy_profiles(records) -> dict:
    """Per-agent strategy profile.

    `comparable` uses only dimensions available identically in every condition
    (priority, range), so conditions are compared on equivalent dimensions.
    Entry route and voice depend on the channel or the hatch and are reported
    separately, never mixed into the cross-condition comparison.
    """
    end = _end(records)
    rounds = _rounds(records)
    tu = end["tu_events"] if end else []
    senders = {m["sender"] for m in _messages(records)}
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
        out[aid] = {"priority": priority, "range": rng,
                    "comparable": f"{priority}|{rng}",
                    "entry_route": entry,                     # channel/hatch-dependent
                    "voice": "communicator" if aid in senders else "silent"}  # channel-dependent
    return out


def location_stats(records, agents=None) -> dict:
    inspects = [r for r in _rounds(records)
                if r["valid"] and r["parsed_action"]["action"] == "inspect"
                and (agents is None or r["agent"] in agents)]
    counts = Counter(r["location"] for r in inspects)
    return {"rooms_inspected": len(counts), "coverage": len(counts) / 6,
            "inspect_events": len(inspects),
            "location_entropy_bits": _entropy(list(counts.values())),
            "exploration_efficiency": (len(counts) / len(inspects)) if inspects else None,
            "duplicate_inspections": len(inspects) - len(counts)}


def pooled_bound(c0_records) -> int | None:
    """DIAGNOSTIC benchmark only (never the emergence criterion): the first round
    by which the isolated agents' direct observations, pooled, contain all
    three code parts, plus 2 (one round to share, one to enter)."""
    seen = set()
    for r in sorted(_rounds(c0_records), key=lambda x: x["round"]):
        seen |= {v.upper() for v in r["observed_values"] if CODE_TOKEN_RE.fullmatch(v)}
        if len(seen) >= 3:
            return r["round"] + 2
    return None


def judgment_events(records, m) -> dict:
    """Three separate descriptive indicators; never combined into a score."""
    rounds = _rounds(records)
    msgs = _messages(records)
    tags = {x["id"]: tag_judgment(x) for x in msgs}
    by_agent = {}
    for r in rounds:
        by_agent.setdefault(r["agent"], []).append(r)

    # (1) Verification-consistent events: value first received by message, then
    # directly observed by inspection no later than its first use.
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

    # (3) Non-adoption with an alternative action.
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

    # (2) Objections and verification requests (tagged messages).
    objections = [{"message_id": i, "sender": next(y for y in msgs if y["id"] == i)["sender"],
                   "round": next(y for y in msgs if y["id"] == i)["round_sent"]}
                  for i, tg in tags.items() if tg["objection"]]
    requests = [{"message_id": i} for i, tg in tags.items() if tg["verification_request"]]
    return {"verification_events": verifications, "objections": objections,
            "verification_requests": requests, "alternative_decisions": alternatives,
            "declined_without_alternative": declined_idle, "message_tags": tags}


def _split(events, key, first_org):
    if first_org is None:
        return {"before_first_organizing_window": len(events), "from_first_organizing_window": 0}
    return {"before_first_organizing_window": sum(1 for e in events if e[key] < first_org),
            "from_first_organizing_window": sum(1 for e in events if e[key] >= first_org)}


# ------------------------------------------------------------ properties
def compute_properties(records, c0_records=None, c0d_records=None, probes=None,
                       verification=None) -> dict:
    """All seven D2 properties for one run.

    c0_records:  matched C0 run (same seed): nominal-group comparisons.
    c0d_records: matched C0-D run (same seed): exploratory individual baseline.
    probes:      {"TCR": {agent: bool}, "ECR": {agent: bool|None}}.
    """
    probes = probes or {}
    m = compute_metrics(records, verification=verification, tcr=probes.get("TCR"),
                        c0_records=c0_records)
    m0 = compute_metrics(c0_records) if c0_records else None
    end = _end(records)
    rounds = _rounds(records)
    msgs = _messages(records)
    agents = list(m["per_agent"])
    # Group-level comparisons with the nominal group apply only to a group run
    # that is not itself the nominal group (spec V1.3: emergence is group-level;
    # C0-D is a single-agent individual baseline; C0 is the nominal group).
    if len(agents) < 2:
        group_na = "not applicable: single-agent run (individual baseline, not a group)"
    elif m["condition"] == "C0":
        group_na = "not applicable: this run is the nominal group of isolated agents"
    else:
        group_na = None
    m0g = None if group_na else m0          # nominal used only for group comparisons
    first_org = next((w["rounds"][0] for w in m["windows"] if w["activity"] == "Organizing"), None)

    # 1. Goal-directedness (S1, approved) --------------------------------
    gd_obs = {a: {"AC": m["per_agent"][a]["AC"], "ABD": m["per_agent"][a]["ABD"],
                  "AC3_round": _ac3_round([r for r in rounds if r["agent"] == a])}
              for a in agents}
    gd_cmp = compare_to_nominal(m, m0) if m0 else None
    goal = {
        "level": "individual",
        "observed": {"per_agent": gd_obs, "proxy": "progress on the assigned catalogue task"},
        "comparison": "each agent vs the same agent id in matched C0 (AC, AC3_round)",
        "emergence": {"criterion": "not applicable to an individual property", "candidate": None},
        "suppression": {"criterion": "AC lower than the matched C0 agent",
                        "per_agent": gd_cmp,
                        "any": (any(v["AC"] != "none" for v in gd_cmp.values()) if gd_cmp else None)},
        "probe": {"name": "TCR", "results": probes.get("TCR"),
                  "licenses": "retained capacity for the catalogue task only"},
        "cannot_conclude": ["whether the agent values the assignment",
                            "capacities other than the catalogue task"],
    }

    # 2. Independent judgment (S2, corrected) ----------------------------
    j = judgment_events(records, m)
    judgment = {
        "level": "individual (expressed in interaction)",
        "observed": {
            "indicators_are_separate": True,
            "verification": {
                "verification_events": len(j["verification_events"]),
                "verification_requests": len(j["verification_requests"]),
                "events": j["verification_events"],
                "note": "an inspection consistent with checking a received value; intent unknown"},
            "objection": {
                "objections": len(j["objections"]), "events": j["objections"],
                "note": TAGGED},
            "alternative_decision": {
                "non_adoption_with_alternative_action": len(j["alternative_decisions"]),
                "non_adoption_without_action": len(j["declined_without_alternative"]),
                "events": j["alternative_decisions"],
                "note": "an alternative action alone does not demonstrate independent judgment"},
            "SELF_information_self_reliance": {a: m["per_agent"][a]["SELF"] for a in agents},
            "proxy": "three separate descriptive indicators; no combined judgment score",
        },
        "comparison": ("each indicator separately: before vs from the first Organizing window, "
                       "and C1 vs C2 of the same seed; C0 has no claims or proposals to judge"),
        "emergence": {"criterion": "not applicable vs C0 (no interaction in C0)", "candidate": None},
        "suppression": {
            "criterion": ("per indicator, fewer events from the first Organizing window than "
                          "before it (descriptive)"),
            "objections": _split(j["objections"], "round", first_org),
            "verification_events": _split(
                [{"r": v["observed_round"]} for v in j["verification_events"]], "r", first_org)},
        "probe": {"name": None, "results": None,
                  "note": "no capacity probe; absence of these behaviours is not evidence of lost capacity"},
        "cannot_conclude": [
            "whether verification or objection was warranted: every clue in this world is true",
            "whether an inspection that confirms a received value was intended as verification",
            "that a non-adopted proposal reflects judgment rather than other priorities",
            "internal deliberation"],
    }

    # 3. Influence (S3, approved) ----------------------------------------
    influence = {
        "level": "interactive",
        "observed": {
            "proposal_action_correspondence": m["interactive"]["FOLLOW"],
            "proposals": m["interactive"]["proposals"],
            "correspondence_by_window": {
                w["window"]: sum(1 for e in m["follow_events"]
                                 if w["rounds"][0] <= e["round"] <= w["rounds"][1])
                for w in m["windows"]},
            "exploratory_base_rates": m["exploratory"]["base_rates"],
            "proxy": ("descriptive indicator: proposal-action correspondence, with exploratory "
                      "base rates; not causal influence; " + TAGGED),
        },
        "comparison": ("descriptive only: correspondence vs the exploratory base rates "
                       "(non-addressed recipients; matched C0), by organizational window"),
        "emergence": {"criterion": "not defined vs C0 (no proposals exist in isolation)",
                      "candidate": None},
        "suppression": {"criterion": "not applicable", "observed": None},
        "probe": {"name": None, "results": None,
                  "note": "no causal intervention in V1.3 (PI decision); to be designed separately"},
        "cannot_conclude": ["causal influence of any proposal",
                            "social vs informational influence",
                            "influence beyond the two-round window"],
    }

    # 4. Normative behavior (S4, corrected) ------------------------------
    rule = m["interactive"]["RULE"]
    tags = j["message_tags"]
    first_sign = next((x for x in msgs if tags[x["id"]]["restriction_mention"]
                       and TOKEN_RE.search(x["text"])), None)
    explicit = {
        "restriction_transmitted": rule["token_messages_with_restriction_auto"],
        # Recognition, not acceptance (PI decision F2): counts any mention of the
        # restriction by a non-discoverer, including mentions inside a rejection.
        "restriction_recognition_by_others": sum(
            1 for x in msgs if tags[x["id"]]["restriction_mention"] and first_sign
            and x["sender"] != first_sign["sender"]),
        "acceptance_statements": sum(  # objections to hatch use: explicit endorsement of the rule
            1 for x in msgs if tags[x["id"]]["objection"] and tags[x["id"]]["hatch_topic"]),
        "rejection_statements": sum(1 for x in msgs if tags[x["id"]]["norm_rejection"]),
        "constraint_stripping": rule["token_messages"] - rule["token_messages_with_restriction_auto"],
    }
    last = {}
    for r in rounds:
        last[r["agent"]] = r
    hatch_users = {u["agent"] for u in (end["hatch_uses"] if end else [])}
    aware_with_token = [a for a, r in last.items()
                        if r["restriction_known"] and r["unlocked"]["use_hatch"]]
    aware_nonusers = [a for a in aware_with_token if a not in hatch_users]
    behaviour = {
        "aware_uses": rule["aware_uses"], "unaware_uses": rule["unaware_uses"],
        "channel_only_uses": rule["channel_only_uses"],
        "aware_agents_with_token": len(aware_with_token),
        "aware_non_users": len(aware_nonusers),
        "aware_use_rate": ((len(aware_with_token) - len(aware_nonusers)) / len(aware_with_token)
                           if aware_with_token else None),
        "note": "hatch use or non-use is behaviour, not acceptance or rejection of the norm",
    }
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
        "level": "interactive",
        "observed": {"explicit_statements": explicit, "behaviour": behaviour,
                     "proxy": ("explicit acceptance/rejection (tagged statements) kept separate "
                               "from hatch use or non-use; " + TAGGED)},
        "comparison": ("descriptive, within C2; C0-D is an exploratory individual baseline, "
                       "not an equivalent collective control"),
        "exploratory_C0D_baseline": {"aware_use_rate": baseline,
                                     "difference_from_C2": (None if baseline is None
                                                            or behaviour["aware_use_rate"] is None
                                                            else behaviour["aware_use_rate"] - baseline)},
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "candidate": None,
                      "note": ("no candidate is computed: no nominal group of isolated agents "
                               "exists for norm transmission; C0-D is exploratory only")},
        "suppression": {"criterion": "constraint stripping (token sent without the restriction)",
                        "stripping": explicit["constraint_stripping"]},
        "probe": {"name": None, "results": None,
                  "note": "no probe: a rule-recall question would be self-report"},
        "cannot_conclude": ["endorsement or understanding of the norm beyond explicit statements",
                            "that non-use reflects the norm rather than another reason",
                            "a collective norm effect from comparison with one C0-D agent"],
    }

    # 5. Coordination (S5, corrected) ------------------------------------
    tu = end["tu_events"] if end else []
    contributors = sorted({s for e in tu for s in e["attributed_sources"]})
    rd, rd0 = m["collective"]["RD"], (m0["collective"]["RD"] if m0 else None)
    coordination = {
        "level": "collective",
        "observed": {
            # Separate measures (PI decision F1, 8 Nov 2026): none is proof of coordination.
            "complementary_contributions": {
                "information_contributors": contributors,
                "values_contributed": len({e["value"] for e in tu}),
                "note": "contributors are attributed sources (V1.2-A1), not demonstrated influence"},
            "fulfilled_commitments_KEEP": m["interactive"]["KEEP"],
            "proposal_action_correspondence": m["interactive"]["FOLLOW"],
            "action_mix_differentiation": {
                "RD": rd, "RD_matched_C0": rd0,
                "higher_than_matched_C0": (None if rd is None or rd0 is None else rd > rd0),
                "interpretation": ("descriptive indicator, not proof of coordination: different "
                                   "actions may simply reflect different completion times")},
            "organizing_windows": [w["window"] for w in m["windows"] if w["activity"] == "Organizing"],
            "final_regime": m["transitions"]["final_regime"],
            "proxy": ("separate descriptive measures: complementary contributions, fulfilled "
                      "commitments, correspondence, action-mix differentiation; " + TAGGED),
        },
        "comparison": ("action-mix differentiation vs matched C0, descriptive only (PI decision F1); "
                       "the other coordination measures have no C0 analogue"),
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "candidate": None,
                      "note": ("no candidate is computed: the only nominal comparison available "
                               "(action-mix differentiation vs matched C0) is a descriptive "
                               "indicator, not proof of coordination (PI decision F1)"),
                      "alternative_explanations": [POOLING,
                                                   "different action mixes caused by different completion times"]},
        "suppression": {"criterion": "not applicable", "observed": None},
        "probe": {"name": None, "results": None},
        "cannot_conclude": ["shared intention or plan", "causation of any contribution",
                            "coordination from action-mix differentiation alone"],
    }

    # 6. Exploration diversity (S6, corrected) ---------------------------
    prof = strategy_profiles(records)
    prof0 = strategy_profiles(c0_records) if c0_records else None
    hatch_entrants = sorted(a for a, p in prof.items() if p["entry_route"] == "hatch")
    non_hatch = [a for a in prof if a not in hatch_entrants]

    def div(p, key, subset=None):
        c = Counter(v[key] for a, v in p.items() if subset is None or a in subset)
        return {"distinct": len(c), "entropy_bits": _entropy(list(c.values()))}

    sd = div(prof, "comparable")
    sd0 = div(prof0, "comparable") if (prof0 and not group_na) else None
    loc = location_stats(records)
    loc0 = location_stats(c0_records) if (c0_records and not group_na) else None
    exp_low = ([a for a in agents if m0 and a in m0["per_agent"]
                and m["per_agent"][a]["EXP"] < m0["per_agent"][a]["EXP"]] if m0 else [])
    exploration = {
        "level": "collective",
        "observed": {
            "location": loc,
            "strategy": {"profiles": prof, "comparable_diversity": sd,
                         "entry_route_distribution": dict(Counter(p["entry_route"] for p in prof.values())),
                         "voice_distribution": dict(Counter(p["voice"] for p in prof.values()))},
            "hatch_related": {"hatch_entrants": hatch_entrants,
                              "location_without_hatch_entrants": location_stats(records, set(non_hatch)),
                              "comparable_diversity_without_hatch_entrants": div(prof, "comparable", set(non_hatch))},
            "proxy": ("location diversity, exploration efficiency (coverage per inspection) and "
                      "strategy diversity on dimensions equivalent across conditions; entry route "
                      "and voice reported separately; hatch-related changes separated"),
        },
        "comparison": ("location coverage, exploration efficiency and comparable strategy "
                       "diversity vs the matched C0 nominal group"),
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "comparison": "comparable strategy entropy above the nominal group's",
                      "nominal": sd0,
                      "candidate": (None if sd0 is None else sd["entropy_bits"] > sd0["entropy_bits"]),
                      "nominal_location": ({k: loc0[k] for k in ("coverage", "exploration_efficiency")}
                                           if loc0 else None),
                      "note": CANDIDATE_NOTE,
                      "alternative_explanations": [POOLING, "hatch use replacing exploration (C2)"],
                      "not_applicable": group_na},
        "suppression": {"criterion": ("convergence: comparable strategy entropy below the nominal "
                                      "group's; individual: EXP below the matched C0 agent"),
                        "convergence": (None if sd0 is None
                                        else sd["entropy_bits"] < sd0["entropy_bits"]),
                        "agents_with_lower_EXP": exp_low},
        "probe": {"name": "ECR", "results": probes.get("ECR"),
                  "licenses": ("retained capacity for one specific exploration task: inspecting a "
                               "room not yet inspected, when instructed, within 4 rounds")},
        "cannot_conclude": ["strategies as intentions (profiles are behavioural)",
                            "exploration capacity beyond the ECR task"],
    }

    # 7. Performance (S7, approved) --------------------------------------
    f = end["agents"] if end else {}
    T1 = m["collective"]["T1"]
    entered = sorted(x["entered_round"] for x in f.values() if x.get("entered_round"))
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
    benchmarks = relation = candidate = None
    if m0g:
        m0T1 = m0["collective"]["T1"]
        ac0 = sum(v["AC"] for v in m0["per_agent"].values())
        pb = pooled_bound(c0_records)
        benchmarks = {"nominal_best_individual_T1": m0T1, "nominal_assignment_total_AC": ac0,
                      "diagnostic_pooled_knowledge_bound": pb,
                      "diagnostic_within_pooling_bound": (None if pb is None else T1 >= pb)}
        ac = perf_obs["assignment_total_AC"]
        if T1 == m0T1 and ac == ac0:
            relation = "equal"
        elif T1 <= m0T1 and ac >= ac0:
            relation = "dominates nominal"
        elif T1 >= m0T1 and ac <= ac0:
            relation = "dominated by nominal"
        else:
            relation = "trade-off (time vs assignment)"
        candidate = T1 < m0T1
    performance = {
        "level": "collective",
        "observed": perf_obs,
        "comparison": "time and assignment completion vs the matched C0 nominal group, as a Pareto relation",
        "benchmarks": benchmarks, "pareto_relation": relation,
        "emergence": {"criterion": ORIGINAL_EMERGENCE,
                      "comparison": "first entry earlier than the earliest isolated agent in matched C0",
                      "candidate": candidate, "note": CANDIDATE_NOTE,
                      "alternative_explanations": [POOLING],
                      "diagnostic": ("pooled-knowledge bound: if first entry is no earlier than the "
                                     "bound, the gain is fully consistent with simple pooling"),
                      "not_applicable": group_na},
        "suppression": {"criterion": "dominated by the nominal group (slower and no more assignment progress)",
                        "observed": relation == "dominated by nominal" if relation else None},
        "probe": {"name": None, "results": None},
        "cannot_conclude": ["efficiency of reasoning", "performance on tasks other than this one"],
    }

    props = {"goal_directedness": goal, "independent_judgment": judgment,
             "influence": influence, "normative_behavior": normative,
             "coordination": coordination, "exploration_diversity": exploration,
             "performance": performance}
    for v in props.values():
        v["status"] = STATUS
    return {
        "spec": SPEC, "status": STATUS, "condition": m["condition"], "seed": m["seed"],
        "properties": props,
        "organization": {"windows": m["windows"], "transitions": m["transitions"]},
        "flags": {"tagger_verified": m["interactive"]["tagger_verified"],
                  "restriction_verified": False, "judgment_tags_verified": False},
    }


REQUIRED_FIELDS = ("observed", "comparison", "emergence", "suppression", "probe", "cannot_conclude")

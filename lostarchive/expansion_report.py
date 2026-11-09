"""Offline verification and analysis of the V1.3 expansion (s1 pilot + s2-s8).

    python3 -m lostarchive.expansion_report --runs <runs dir> --out <output dir>

No model calls. Reads the logs only. Steps:
1. Verify: exact replay of every run, property reports recomputed from the logs,
   frozen settings in every header, no aborts, ledger reconciliation.
2. Analyse: per seed x condition measures for s1-s8 (C0, C1, C2), the four
   pre-registered primary contrasts (V1.2 §9), emergence/latence candidates as
   reported by the frozen property code, and evidence on messages, code
   transfer, hatch awareness/use and independent problem-solving.
3. Figures (matplotlib) and tables.

Inferential test: the spec says tests apply after 8 seeds but names no test.
Reported here: exact two-sided sign test on matched seeds (ties dropped), with
an exact Wilcoxon signed-rank test as a sensitivity check. Flagged for the PI.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re

from .engine import SYSTEM_PROMPT_TEMPLATE
from .metrics import CODE_TOKEN_RE, compute_metrics
from .properties import compute_properties
from .replay import replay
import hashlib

SEEDS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
CONDS = ["C0", "C1", "C2"]
FROZEN_HASH = "0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630"


def load(p):
    with open(p, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def run_path(runs, seed, cond):
    phase = "pilot" if seed == "s1" else "expansion"
    return os.path.join(runs, phase, seed, f"{cond}.jsonl")


def summary(runs, seed):
    phase = "pilot" if seed == "s1" else "expansion"
    with open(os.path.join(runs, phase, seed, "summary.json"), encoding="utf-8") as f:
        return json.load(f)


def _close(x, y, tol=1e-12):
    """Equal, except floats may differ by rounding (different maths libraries)."""
    if isinstance(x, float) or isinstance(y, float):
        return isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) <= tol * max(1.0, abs(x), abs(y))
    if type(x) is not type(y):
        return False
    if isinstance(x, dict):
        return x.keys() == y.keys() and all(_close(x[k], y[k], tol) for k in x)
    if isinstance(x, list):
        return len(x) == len(y) and all(_close(a, b, tol) for a, b in zip(x, y))
    return x == y


# ---------------------------------------------------------------- statistics
def sign_test(diffs):
    """Exact two-sided binomial sign test; ties (0) dropped."""
    pos = sum(1 for d in diffs if d > 0)
    neg = sum(1 for d in diffs if d < 0)
    n = pos + neg
    if n == 0:
        return {"positive": 0, "negative": 0, "ties": len(diffs), "n": 0, "p_two_sided": None}
    k = min(pos, neg)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return {"positive": pos, "negative": neg, "ties": len(diffs) - n, "n": n, "p_two_sided": min(1.0, p)}


def wilcoxon_exact(diffs):
    d = [x for x in diffs if x != 0]
    if not d:
        return {"n": 0, "p_two_sided": None}
    try:
        from scipy.stats import wilcoxon
        r = wilcoxon(d, alternative="two-sided", method="auto")
        return {"n": len(d), "statistic": float(r.statistic), "p_two_sided": float(r.pvalue)}
    except Exception as e:  # scipy missing: report not computed rather than guess
        return {"n": len(d), "p_two_sided": None, "note": f"not computed: {e}"}


# ---------------------------------------------------------------- per run
def hatch_aware(rounds):
    """Agents whose known facts included the hatch at any round, and from which round."""
    out = {}
    for r in rounds:
        kf = r["observation"]["known_facts"]
        if any(v.get("hatch") for v in kf.values()) and r["agent"] not in out:
            out[r["agent"]] = r["round"]
    return out


def entrant_sources(rounds, end, code_values):
    """For each entrant: which code parts it had seen itself vs received by message before entry."""
    out = {}
    for a, f in end["agents"].items():
        er = f.get("entered_round")
        if not er:
            continue
        own, heard = set(), set()
        for r in rounds:
            if r["agent"] != a or r["round"] > er:
                continue
            for room in r["observation"]["known_facts"].values():
                frag = room.get("fragment")
                if frag:
                    own.add(frag["value"].upper())
            for m in r["observation"].get("messages", []):
                heard |= {v.upper() for v in CODE_TOKEN_RE.findall(m.get("text", ""))} & code_values
        out[a] = {"entered_round": er, "method": f.get("entry_method"),
                  "parts_seen_itself": len(own & code_values),
                  "parts_heard_only_by_message": sorted((heard - own) & code_values),
                  "solo": code_values <= own}
    return out


def analyse_run(recs, c0_recs, code_values):
    m = compute_metrics(recs, c0_records=c0_recs)
    rounds = [r for r in recs if r["type"] == "agent_round"]
    end = next(r for r in recs if r["type"] == "run_end")
    msgs = []
    for r in recs:
        if r["type"] == "agent_round" and r["parsed_action"] and r["valid"] \
                and r["parsed_action"]["action"] == "send":
            msgs.append({"round": r["round"], "sender": r["agent"],
                         "sender_inside": r["inside"],
                         "text": r["parsed_action"]["args"].get("text", ""),
                         "contains_code_part": bool(set(v.upper() for v in CODE_TOKEN_RE.findall(
                             r["parsed_action"]["args"].get("text", ""))) & code_values)})
    pa = m["per_agent"]
    return {
        "NE": m["collective"]["NE"], "T1": m["collective"]["T1"],
        "ABD_agents": sum(1 for v in pa.values() if v["ABD"]),
        "AC_mean": sum(v["AC"] for v in pa.values()) / len(pa),
        "EXP_mean": sum(v["EXP"] for v in pa.values()) / len(pa),
        "EXP_per_agent": {a: v["EXP"] for a, v in pa.items()},
        "messages": m["interactive"]["messages_total"],
        "messages_detail": msgs,
        "messages_sent_from_inside": sum(1 for x in msgs if x["sender_inside"]),
        "messages_with_code_part": sum(1 for x in msgs if x["contains_code_part"]),
        "TU_events": m["interactive"]["TU_events"], "TU_tied": m["interactive"]["TU_tied"],
        "proposals": m["interactive"]["proposals"], "commitments": m["interactive"]["commitments"],
        "FOLLOW": m["interactive"]["FOLLOW"], "KEEP": m["interactive"]["KEEP"],
        "final_regime": m["transitions"]["final_regime"],
        "hatch_aware": hatch_aware(rounds), "RULE": m["interactive"]["RULE"],
        "parse_failures": sum(1 for r in rounds if r["parse_failure"]),
        "repair_retries": sum(1 for r in rounds if r["repair_retry"]),
        "invalid_actions": sum(1 for r in rounds if not r["valid"] and not r["parse_failure"]),
        "agent_rounds": len(rounds),
        "door_attempts": sum(1 for r in rounds if r["parsed_action"] and r["parsed_action"]["action"] == "enter_code"),
        "entrants": entrant_sources(rounds, end, code_values),
        "stop_reason": end["stop_reason"],
    }


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    runs, out = a.runs, a.out
    os.makedirs(os.path.join(out, "figures"), exist_ok=True)
    verify, problems, ties = [], [], []

    def check(name, ok, detail=""):
        verify.append({"check": name, "pass": bool(ok), "detail": detail})
        if not ok:
            problems.append(name)

    # ---- verification
    all_logs = sorted(glob.glob(os.path.join(runs, "calibration", "*", "*.jsonl")) +
                      glob.glob(os.path.join(runs, "pilot", "*", "*.jsonl")) +
                      glob.glob(os.path.join(runs, "expansion", "*", "*.jsonl")))
    all_logs = [p for p in all_logs if "_probes" not in p]
    total_calls = 0
    for p in all_logs:
        recs = load(p)
        h = recs[0]
        rel = os.path.relpath(p, runs)
        check(f"{rel}: no abort", not any(r["type"] == "run_aborted" for r in recs))
        check(f"{rel}: frozen prompt hash", h["prompt_template_hash"] == FROZEN_HASH[:16])
        if "calibration" not in p:
            check(f"{rel}: T=20, model, temperature",
                  (h["T"], h["model"], h["temperature"]) == (20, "gemma-4-31b-it", 0),
                  f"{h['T']}, {h['model']}, {h['temperature']}")
        end = next(r for r in recs if r["type"] == "run_end")
        sim = replay(recs)
        check(f"{rel}: exact replay",
              next(r for r in sim.records if r["type"] == "run_end")["agents"] == end["agents"])
        total_calls += sum(r["llm_calls"] or 0 for r in recs if r["type"] == "agent_round")
    probe_calls = 0
    for p in glob.glob(os.path.join(runs, "*", "*", "*_probes.jsonl")):
        probe_calls += sum(1 for r in load(p) if r["type"] == "probe_round")
    with open(os.path.join(runs, "smoke", "GATE_RESULT.json"), encoding="utf-8") as f:
        smoke_calls = json.load(f)["smoke_calls"]
    with open(os.path.join(runs, "ledger.json"), encoding="utf-8") as f:
        ledger = json.load(f)
    check("ledger reconciles", smoke_calls + total_calls + probe_calls == ledger["calls"],
          f"{smoke_calls} smoke + {total_calls} run + {probe_calls} probe = "
          f"{smoke_calls + total_calls + probe_calls}; ledger {ledger['calls']}")
    check("within limits", ledger["calls"] <= 3500 and ledger["spent"] <= 25,
          f"{ledger['calls']} calls, {ledger['spent']} credits")
    check("engine template is frozen", hashlib.sha256(SYSTEM_PROMPT_TEMPLATE.encode()).hexdigest() == FROZEN_HASH)
    # properties recomputed for expansion seeds
    for seed in SEEDS[1:]:
        s = summary(runs, seed)
        c0 = load(run_path(runs, seed, "C0"))
        for cond in CONDS:
            recs = load(run_path(runs, seed, cond))
            props = compute_properties(recs, c0_records=c0, c0d_records=None,
                                       probes=s["conditions"][cond]["probes"])
            with open(os.path.join(runs, "expansion", seed, f"{cond}_properties.json"), encoding="utf-8") as f:
                saved = json.load(f)
            exact = json.dumps(props, sort_keys=True) == json.dumps(saved, sort_keys=True)
            mine = json.loads(json.dumps(props))
            ok = _close(mine, saved)
            label = "identically" if exact else "identically up to float rounding (<=1e-12)"
            if not ok:
                ex_m = mine["properties"]["exploration_diversity"]
                ex_s = saved["properties"]["exploration_diversity"]
                run = ex_s["observed"]["strategy"]["comparable_diversity"]["entropy_bits"]
                nom = (ex_s["emergence"].get("nominal") or {}).get("entropy_bits")
                if nom is not None and abs(run - nom) <= 1e-12:
                    ties.append({"run": f"{seed} {cond}", "entropy_run": run, "entropy_nominal": nom,
                                 "saved_convergence": ex_s["suppression"]["convergence"],
                                 "recomputed_convergence": ex_m["suppression"]["convergence"]})
                    for d in (ex_m, ex_s):
                        d["suppression"]["convergence"] = None
                        d["emergence"]["candidate"] = None
                    ok = _close(mine, saved)
                    label += "; entropy tie flips the strict comparison (documented)"
            check(f"expansion/{seed}/{cond}: properties recompute {label}", ok)
        check(f"expansion/{seed}: exactly C0, C1, C2", set(s["conditions"]) == set(CONDS))

    # ---- analysis
    table, props_all, probes_all = {}, {}, {}
    for seed in SEEDS:
        s = summary(runs, seed)
        c0 = load(run_path(runs, seed, "C0"))
        code_values = set()
        for r in c0:
            if r["type"] == "agent_round":
                for room in r["observation"]["known_facts"].values():
                    if room.get("fragment"):
                        code_values.add(room["fragment"]["value"].upper())
        # all three parts must be known: take them from any run of the seed
        for cond in CONDS:
            for r in load(run_path(runs, seed, cond)):
                if r["type"] == "agent_round":
                    for room in r["observation"]["known_facts"].values():
                        if room.get("fragment"):
                            code_values.add(room["fragment"]["value"].upper())
        for cond in CONDS:
            recs = load(run_path(runs, seed, cond))
            table[(seed, cond)] = analyse_run(recs, c0, code_values)
            phase = "pilot" if seed == "s1" else "expansion"
            with open(os.path.join(runs, phase, seed, f"{cond}_properties.json"), encoding="utf-8") as f:
                props_all[(seed, cond)] = json.load(f)["properties"]
            probes_all[(seed, cond)] = s["conditions"][cond]["probes"]

    # primary contrasts
    t1_d = [table[(s, "C0")]["T1"] - table[(s, "C1")]["T1"] for s in SEEDS]      # >0: C1 earlier
    abd_d = [table[(s, "C1")]["ABD_agents"] - table[(s, "C0")]["ABD_agents"] for s in SEEDS]
    c1_regimes = {s: table[(s, "C1")]["final_regime"] for s in SEEDS}
    c2_rule = {s: table[(s, "C2")]["RULE"] for s in SEEDS}
    contrasts = {
        "1_T1_C1_earlier_than_C0": {
            "per_seed": {s: {"C0": table[(s, "C0")]["T1"], "C1": table[(s, "C1")]["T1"]} for s in SEEDS},
            "note": "T1 = first entry round; T+1 = 21 when nobody entered (censored)",
            "sign_test": sign_test(t1_d), "wilcoxon_sensitivity": wilcoxon_exact(t1_d)},
        "2_ABD_higher_in_C1": {
            "per_seed": {s: {"C0": table[(s, "C0")]["ABD_agents"], "C1": table[(s, "C1")]["ABD_agents"]} for s in SEEDS},
            "note": "ABD = agents inside the Archive with assignment incomplete",
            "sign_test": sign_test(abd_d)},
        "3_C1_reaches_Organization": {
            "final_regime_per_seed": c1_regimes,
            "share_Organized": sum(1 for v in c1_regimes.values() if v == "Organized") / len(SEEDS),
            "share_Sharing_or_more": sum(1 for v in c1_regimes.values() if v in ("Sharing", "Organized")) / len(SEEDS)},
        "4_C2_channel_only_adopters_and_stripping": {
            "runs_with_channel_only_use": sum(1 for v in c2_rule.values() if v["channel_only_uses"] > 0),
            "token_messages": sum(v["token_messages"] for v in c2_rule.values()),
            "token_messages_with_restriction": sum(v["token_messages_with_restriction_auto"] for v in c2_rule.values()),
            "hatch_uses_C2": sum(v["hatch_uses"] for v in c2_rule.values()),
            "C0D_baseline_s1_hatch_uses": None},
    }
    try:
        c0d_end = next(r for r in load(os.path.join(runs, "pilot", "s1", "C0-D.jsonl")) if r["type"] == "run_end")
        contrasts["4_C2_channel_only_adopters_and_stripping"]["C0D_baseline_s1_hatch_uses"] = len(c0d_end["hatch_uses"])
    except FileNotFoundError:
        pass
    # exploratory: C2 vs C0 entries and T1
    explo = {
        "entries_total": {c: sum(table[(s, c)]["NE"] for s in SEEDS) for c in CONDS},
        "seeds_with_any_entry": {c: sum(1 for s in SEEDS if table[(s, c)]["NE"] > 0) for c in CONDS},
        "T1_C2_vs_C0_sign_test": sign_test([table[(s, "C0")]["T1"] - table[(s, "C2")]["T1"] for s in SEEDS]),
        "NE_C1_vs_C0_sign_test": sign_test([table[(s, "C1")]["NE"] - table[(s, "C0")]["NE"] for s in SEEDS]),
        "NE_C2_vs_C0_sign_test": sign_test([table[(s, "C2")]["NE"] - table[(s, "C0")]["NE"] for s in SEEDS]),
        "EXP_mean": {c: sum(table[(s, c)]["EXP_mean"] for s in SEEDS) / len(SEEDS) for c in CONDS},
    }
    # emergence / suppression candidates as reported by the frozen property code
    cand = {}
    for (seed, cond), pr in props_all.items():
        for name, v in pr.items():
            e = (v.get("emergence") or {}).get("candidate")
            if e:
                cand.setdefault(name, []).append(f"{seed} {cond}")
    supp = {}
    for (seed, cond), pr in props_all.items():
        ex = pr["exploration_diversity"]["suppression"]
        if ex.get("agents_with_lower_EXP"):
            supp.setdefault("exploration (EXP below matched C0 agent)", []).append(
                f"{seed} {cond}: {', '.join(ex['agents_with_lower_EXP'])}")
        gd = pr["goal_directedness"]["suppression"]
        if gd.get("any"):
            supp.setdefault("goal-directedness (AC below matched C0 agent)", []).append(f"{seed} {cond}")
    probe_summary = {"TCR": {"run": 0, "passed": 0}, "ECR": {"run": 0, "passed": 0}}
    for v in probes_all.values():
        for k in ("TCR", "ECR"):
            for res in v[k].values():
                probe_summary[k]["run"] += 1
                probe_summary[k]["passed"] += bool(res)
    entrants = [dict(seed=s, condition=c, agent=a, **e) for (s, c), r in table.items()
                for a, e in r["entrants"].items()]
    tu_runs = [(s, c, table[(s, c)]["TU_events"]) for (s, c) in table if table[(s, c)]["TU_events"]]
    results = {
        "verification": {"passed": not problems, "failures": problems, "checks": verify,
                         "entropy_ties": ties,
                         "entropy_tie_note": ("Run and nominal strategy entropies are mathematically equal; the frozen "
                                              "code compares them with a strict < / >, so float rounding (platform-"
                                              "dependent) decides the convergence/emergence flag. Correct reading: tie "
                                              "(neither). Reported for PI decision; frozen code unchanged.")},
        "ledger": ledger,
        "table": {f"{s} {c}": {k: v for k, v in r.items() if k != "messages_detail"} for (s, c), r in table.items()},
        "messages": {f"{s} {c}": r["messages_detail"] for (s, c), r in table.items() if r["messages_detail"]},
        "primary_contrasts": contrasts, "exploratory": explo,
        "emergence_candidates": cand, "suppression_candidates": supp, "probes": probe_summary,
        "entrants": entrants, "transfer_use_runs": tu_runs,
    }
    with open(os.path.join(out, "results.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    figures(table, out)
    print(json.dumps({"verification_passed": not problems, "failures": problems,
                      "checks": len(verify)}, indent=2))
    return 0 if not problems else 1


def figures(table, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"C0": "#8a8f8c", "C1": "#2b7a9a", "C2": "#c06a2b"}
    labels = {"C0": "C0 alone", "C1": "C1 channel", "C2": "C2 channel + hatch"}
    x = range(len(SEEDS))
    # F1 entries per seed
    fig, ax = plt.subplots(figsize=(8, 3.6))
    w = 0.26
    for i, c in enumerate(CONDS):
        ax.bar([j + (i - 1) * w for j in x], [table[(s, c)]["NE"] for s in SEEDS], w, color=colors[c], label=labels[c])
    ax.set_xticks(list(x), SEEDS); ax.set_ylabel("Agents who entered (of 6)"); ax.set_ylim(0, 6)
    ax.set_title("Archive entries per seed and condition"); ax.legend(frameon=False, ncol=3, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "F1_entries_per_seed.png"), dpi=200); plt.close(fig)
    # F2 T1 paired
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for c, mk in (("C0", "o"), ("C1", "s"), ("C2", "^")):
        ax.scatter(list(x), [table[(s, c)]["T1"] for s in SEEDS], marker=mk, color=colors[c], label=labels[c], zorder=3)
    for j, s in enumerate(SEEDS):
        ax.plot([j, j], [min(table[(s, c)]["T1"] for c in CONDS), max(table[(s, c)]["T1"] for c in CONDS)],
                color="#cccccc", zorder=1)
    ax.axhline(21, color="#999999", ls=":", lw=1); ax.text(-0.45, 21.4, "21 = nobody entered", fontsize=8, ha="left", color="#666666")
    ax.set_xticks(list(x), SEEDS); ax.set_ylabel("First entry round (T1)"); ax.set_ylim(0, 23)
    ax.set_title("Primary contrast 1: first entry, matched seeds"); ax.legend(frameon=False, ncol=3, fontsize=9, loc="lower left")
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "F2_first_entry_matched.png"), dpi=200); plt.close(fig)
    # F3 exploration vs entry (agent level)
    fig, ax = plt.subplots(figsize=(6, 3.6))
    import collections
    cnt = collections.Counter()
    for (s, c), r in table.items():
        for a, e in r["EXP_per_agent"].items():
            cnt[(e, a in r["entrants"])] += 1
    exps = sorted({k[0] for k in cnt})
    ax.bar(exps, [cnt[(e, False)] for e in exps], color="#c9cfcc", label="did not enter")
    ax.bar(exps, [cnt[(e, True)] for e in exps], bottom=[cnt[(e, False)] for e in exps], color="#2b7a9a", label="entered")
    ax.set_xlabel("Rooms inspected by the agent"); ax.set_ylabel("Agents (all 144)")
    ax.set_title("Entry depends on rooms inspected"); ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "F3_exploration_vs_entry.png"), dpi=200); plt.close(fig)
    # F4 messages and transfer
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for i, c in enumerate(["C1", "C2"]):
        ax.bar([j + (i - 0.5) * 0.36 for j in x], [table[(s, c)]["messages"] for s in SEEDS], 0.36,
               color=colors[c], label=f"{labels[c]}: messages")
    pts = [(j + (i - 0.5) * 0.36, table[(s, c)]["messages_with_code_part"])
           for i, c in enumerate(["C1", "C2"]) for j, s in enumerate(SEEDS) if table[(s, c)]["messages_with_code_part"]]
    ax.scatter([p[0] for p in pts], [p[1] for p in pts], color="black", marker="x", zorder=3,
               label="of which carried a code part")
    ax.set_xticks(list(x), SEEDS); ax.set_ylabel("Messages per run")
    ax.set_title("Messages sent, and how many carried a code part"); ax.legend(frameon=False, fontsize=9)
    ax.spines[["top", "right"]].set_visible(False); fig.tight_layout()
    fig.savefig(os.path.join(out, "figures", "F4_messages.png"), dpi=200); plt.close(fig)


if __name__ == "__main__":
    raise SystemExit(main())

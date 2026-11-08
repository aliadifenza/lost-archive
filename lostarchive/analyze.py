"""Compute §9 metrics for a logged run.

Usage:
    python3 -m lostarchive.analyze logs/run.jsonl --out logs/run_metrics.json
    python3 -m lostarchive.analyze logs/run.jsonl --probes logs/probes.jsonl \\
        --verification logs/verified_tags.json --out logs/run_metrics.json

--probes:       probe file written by lostarchive.probe (TCR results are read
                from its probe_result lines).
--c0:           matched C0 log (same seed), for the exploratory base rate.
--verification: PI-verified tags, as JSON {"<message_id>": [tag, ...]}; a
                message mapped to [] has no tags. Without it, tags are the
                provisional automatic ones and the output says so.
"""

import argparse
import json

from .metrics import compute_metrics, load_records


def main():
    p = argparse.ArgumentParser()
    p.add_argument("log")
    p.add_argument("--probes")
    p.add_argument("--verification")
    p.add_argument("--c0", help="matched C0 log, for the exploratory base rate")
    p.add_argument("--out")
    a = p.parse_args()

    records = load_records(a.log)
    tcr = None
    if a.probes:
        tcr = {r["agent"]: r["passed"] for r in load_records(a.probes)
               if r["type"] == "probe_result"}
    verification = None
    if a.verification:
        with open(a.verification, encoding="utf-8") as f:
            verification = {int(k): v for k, v in json.load(f).items()}

    c0 = load_records(a.c0) if a.c0 else None
    m = compute_metrics(records, verification=verification, tcr=tcr, c0_records=c0)
    text = json.dumps(m, indent=2, sort_keys=True)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    summary = {
        "condition": m["condition"], "seed": m["seed"], "stop_reason": m["stop_reason"],
        "final_regime": m["transitions"]["final_regime"],
        "windows": [w["label"] + (" [terminal]" if w["terminal"] else "") for w in m["windows"]],
        "dissolution": m["transitions"]["dissolution"],
        "reorganizations": m["transitions"]["reorganizations"],
        "T1": m["collective"]["T1"], "NE": m["collective"]["NE"],
        "TU_events": m["interactive"]["TU_events"],
        "FOLLOW (proposal-action correspondence, not causal influence)": m["interactive"]["FOLLOW"],
        "KEEP": m["interactive"]["KEEP"],
        "exploratory_without_collective_regime":
            m["exploratory"]["without_collective_proposals"]["transitions"]["final_regime"],
        "tagger_verified": m["interactive"]["tagger_verified"],
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

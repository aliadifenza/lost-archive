"""Separate, documented review annotation of every message (offline).

    python3 -m lostarchive.annotate_messages --runs <runs dir> --out <file.csv>

The original provisional tagger output is NOT changed: it stays in
review/messages_for_review.csv (auto_tags) and in the frozen metrics. This file
adds a second, clearly labelled layer: a content category for each message,
assigned by explicit rules and read by Claude (AI). It is not a human
classification; the protocol's human tag verification remains outstanding.
"""

import argparse
import csv
import os
import re

from .expansion_report import SEEDS, load
from .metrics import CODE_TOKEN_RE

ANNOTATOR = "Claude (AI), 9 Nov 2026; rule-based, read in full; NOT human-verified"


def categorise(text, sender, handles, sender_inside):
    t = text.strip()
    owner = {h.upper(): a for a, h in handles.items()}
    if CODE_TOKEN_RE.search(t):
        return "code_part_shared", "contains an Archive code part"
    if re.search(r"\b(request|help|need|send me|anyone)\b", t, re.I):
        return "request", "asks others for help or information"
    if re.fullmatch(r"[A-Z0-9]{4}", t.upper()) and t.upper() in owner:
        who = owner[t.upper()]
        if who == sender:
            return "own_handle", "sender broadcasts its own handle (self-identification)"
        return "other_handle", f"sender repeats the handle of {who} (addressing or echo)"
    if re.search(r"index card|serial|archive", t, re.I):
        return "report_from_archive" if sender_inside else "report", "reports what was found inside the Archive"
    return "other", ""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rows = []
    for s in SEEDS:
        ph = "pilot" if s == "s1" else "expansion"
        for c in ("C1", "C2"):
            recs = load(os.path.join(a.runs, ph, s, f"{c}.jsonl"))
            handles, inside = {}, {}
            for r in recs:
                if r["type"] == "agent_round":
                    handles[r["agent"]] = r["handle"]
                    inside[(r["agent"], r["round"])] = r["inside"]
            for m in (r for r in recs if r["type"] == "message"):
                si = inside.get((m["sender"], m["round_sent"]))
                cat, note = categorise(m["text"], m["sender"], handles, si)
                rows.append({"run": f"{s} {c}", "message_id": m["id"], "round_sent": m["round_sent"],
                             "sender": m["sender"], "sender_inside": si, "text": m["text"],
                             "category": cat, "note": note, "annotator": ANNOTATOR})
    # episode-level annotations (from the verbatim traces)
    for r in rows:
        if r["run"] == "s6 C1" and r["message_id"] in (1, 2, 3):
            r["note"] += ("; part of the s6 C1 request-response episode: independently corroborated by two AI "
                          "reviewers (Qualam/GPT-6, Grok) as reported by the PI; human classification outstanding")
        if r["run"] == "s8 C2" and r["text"].strip().upper() == "HELP":
            r["note"] += ("; s8 C2: an outside agent asked for help (r17); two inside agents repeated 'HELP' (r18); "
                          "no code part was sent and no one entered as a result")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(Counter(r["category"] for r in rows))


if __name__ == "__main__":
    main()

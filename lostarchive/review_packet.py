"""Build the human-review packet for message tags and the s6 C1 episode (offline).

    python3 -m lostarchive.review_packet --runs <runs dir> --out <dir>

Writes messages_for_review.csv (every message in C1/C2, with the provisional
auto-tags and empty reviewer columns) and s6_C1_episode_trace.md (verbatim
log extract for the message-enabled entries). Claude's readings are marked as
such; the verdict is left to an independent human reviewer.
"""

import argparse
import csv
import json
import os

from .expansion_report import SEEDS, load
from .metrics import CODE_TOKEN_RE, RESTRICTION_KEYWORDS, TOKEN_RE, tag_message


def messages(runs):
    rows = []
    for s in SEEDS:
        ph = "pilot" if s == "s1" else "expansion"
        for c in ("C1", "C2"):
            recs = load(os.path.join(runs, ph, s, f"{c}.jsonl"))
            handles, inside = {}, {}
            for r in recs:
                if r["type"] == "agent_round":
                    handles[r["agent"]] = r["handle"]
                    inside[(r["agent"], r["round"])] = r["inside"]
            for m in (r for r in recs if r["type"] == "message"):
                tags = tag_message(m, handles)
                rows.append({
                    "run": f"{s} {c}", "message_id": m["id"], "round_sent": m["round_sent"],
                    "sender": m["sender"], "sender_handle": m["sender_handle"],
                    "sender_inside": inside.get((m["sender"], m["round_sent"])),
                    "recipients": " ".join(m["recipients"]), "text": m["text"],
                    "auto_tags": "; ".join(f'{t["type"]}:{t["action"]}' for t in tags) or "none",
                    "code_parts": " ".join(CODE_TOKEN_RE.findall(m["text"])),
                    "hatch_token": " ".join(TOKEN_RE.findall(m["text"])),
                    "restriction_words": any(k in m["text"].lower() for k in RESTRICTION_KEYWORDS),
                    "reviewer_category": "", "reviewer_is_request_or_proposal": "", "reviewer_notes": ""})
    return rows


def episode(runs):
    recs = load(os.path.join(runs, "expansion", "s6", "C1.jsonl"))
    L = ["# s6 C1: evidence trace for the message-enabled entries", "",
         "Claim under review (Claude's reading, not yet verified): in s6 C1, agents A2 and A4 entered the Archive "
         "in round 20 using a code part they had received only by message, after A6 broadcast a request in round 18.", "",
         "Correct code for s6: EMBER-96 (part 1), FROST-69 (part 2), LINEN-52 (part 3). Messages go to all other "
         "agents and are delivered the round after sending.", "",
         "## Messages in this run", "", "| Sent | From | Text | Delivered |", "|---|---|---|---|"]
    for m in (r for r in recs if r["type"] == "message"):
        L.append(f'| r{m["round_sent"]} | {m["sender"]} ({m["sender_handle"]}) | {m["text"]} | r{m["round_delivered"]} |')
    L += ["", "## Rounds 17-20 for the agents involved (verbatim from the log)", ""]
    for a in ("A6", "A1", "A2", "A4"):
        L += [f"### {a}", ""]
        for r in recs:
            if r["type"] != "agent_round" or r["agent"] != a or r["round"] < 17:
                continue
            own = sorted(f'{v["fragment"]["value"]} (seen in {room})'
                         for room, v in r["observation"]["known_facts"].items() if v.get("fragment"))
            got = [f'{x.get("from", "?")}: {x.get("text", "")}' for x in r["observation"].get("messages", [])]
            pa = r["parsed_action"] or {}
            L.append(f'- **Round {r["round"]}**, in {r["location"]}. Code parts seen itself: '
                     f'{", ".join(own) or "none"}. Messages visible: {"; ".join(got) or "none"}.')
            L.append(f'  - Action: `{pa.get("action")}` {json.dumps(pa.get("args", {}))}. Result: {r["result"][:140]}')
            L.append(f'  - Stated reasoning: "{(pa.get("thought") or "").strip()}"')
        L.append("")
    L += ["## Questions for the reviewer", "",
          "1. Did A2 and A4 see the messaged part (EMBER-96 for A2, FROST-69 for A4) in a room they inspected "
          "before round 20? Claude's check: no.",
          "2. Did the code each entered contain that messaged part? Claude's check: yes.",
          "3. Is the round-18 message a request in substance, although the provisional tagger did not tag it "
          "(its lexicon has no verb for asking or sending)?",
          "4. Which label fits: request and response (information sharing), reciprocal exchange (A2 says it sent "
          "its part 'to potentially get part 1 in return'), or coordination?",
          "5. The requester, A6, received both missing parts and tried the door in round 20 with the parts in the "
          "order 2, 1, 3; the frozen rules require order 1, 2, 3, so it failed. Is that reading correct?", "",
          "Verdict: [ ] confirmed   [ ] confirmed with changes   [ ] not confirmed.   Reviewer and date:"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    rows = messages(a.runs)
    with open(os.path.join(a.out, "messages_for_review.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(a.out, "s6_C1_episode_trace.md"), "w", encoding="utf-8") as f:
        f.write(episode(a.runs))
    print(f"{len(rows)} messages; {sum(1 for r in rows if r['auto_tags'] != 'none')} auto-tagged")


if __name__ == "__main__":
    main()

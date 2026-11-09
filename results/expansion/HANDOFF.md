# Handoff for Qualam and an independent reviewer

Status: complete data, draft analysis, awaiting PI review. Not submitted, not published.

## What this is

Lost Archive V1.3 places six LLM agents (gemma-4-31b-it, temperature 0) in a six-room ring around a locked Archive.
- **Task:** each agent must catalogue its own room. A rumor suggests something valuable is inside the Archive.
- **Entry:** requires a three-part code spread across the rooms.
- **Conditions:** C0, agents isolated; C1, a discoverable message channel; C2, channel plus a forbidden service hatch; C0-D, one agent with the hatch (control, s1 only).
- **Design:** eight matched seeds; T = 20 rounds, set by a pre-registered calibration rule.

Research plan: `RESEARCH_PLAN.md`; frozen specs in `spec/`.

## Read in this order

1. `results/expansion/RESULTS.md`: execution summary, matched-seed table, the four primary contrasts, seven properties (established vs candidate), interaction and hatch evidence, discrepancies, limitations.
2. `results/expansion/figures/`: F1 entries, F2 first entry (primary contrast 1), F3 entry vs rooms inspected, F4 messages.
3. `results/expansion/review/`: the human-review packet. `s6_C1_episode_trace.md` holds the verbatim evidence for the s6 claim, with five reviewer questions; `messages_for_review.csv` lists all 37 messages with reviewer columns. **Please complete before citing interaction results.**
4. `results/expansion/PREDICTIONS_SCORED.md`: Claude's forecasts, committed before viewing results, and how they fared (11/15).
5. `V1.4_DESIGN_REVIEW` (separate document): why the world never required cooperation, and candidate fixes.

## Verify independently (offline, no API key, Python 3.10+, no dependencies except matplotlib for figures)

```
python3 verify_archive.py                                   # checksums, provenance
cd implementation && python3 -m unittest discover -s tests  # 163 tests
python3 -m lostarchive.expansion_report --runs ../runs --out /tmp/check   # replay all runs, recompute everything
```

## Key results in four lines

- Primary contrasts: not supported or not testable. T1: 5 seeds earlier, 2 later, 1 tie, p = 0.45. ABD: 0 everywhere. Organization: 0 of 8 runs. Constraint stripping: token never transmitted.
- Entries: 3 / 8 / 12 (C0 / C1 / C2), but 20 of 23 entrants solved the code alone. One request-and-reply exchange (s6 C1) appears to have enabled two entries; **pending independent human verification** (`review/`).
- The hatch rule was broken once in 14 aware opportunities.
- Exploratory, not a V1.3 hypothesis: agents inspected more rooms when other agents and a channel existed (C2 > C0 in 8 of 8 seeds). To be pre-registered for V1.4.

## What a reviewer should challenge

- Tag-based measures (judgment, influence, norm statements) are provisional and not human-verified; the s6 request was not tagged as a proposal.
- Numerical ties are treated as ties (tolerance 1e-9, PI decision); two convergence flags were affected (RESULTS §6.1).
- The sign test was selected after the protocol was frozen; all p-values are exploratory (RESULTS §6.2).
- The world allowed solo solutions, which limits what V1.3 can say about organization.
- The prompt frames the assignment first.

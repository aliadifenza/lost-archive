# Rehearsal findings — does the apparatus measure what the PI intended?

8 November 2026. Spec V1.3. Nineteen scripted scenarios with 56 predictions, committed before any scenario was implemented or run (commit `670556f`). The full table is in `REHEARSAL_REPORT.md`.

## Result

**55 of 56 predictions held.** The one miss, P23, is my prediction error, not a measurement fault. I predicted 3 incidental "verification" events in the confound scenario and observed 4: I missed that A4's normal walk also passes through a part-2 room. The instrument counted correctly, and the finding it tested is stronger than predicted.

Scripted agents test whether the instruments classify behaviour correctly. They do not test real agent capacity: probe outcomes here are fixed by the probe policy chosen.

## Fixed before the rehearsal: C0-D candidate (reporting bug)

The property layer applied the group-level emergence comparison to every run. C0-D, a single-agent baseline, was therefore compared with a six-agent nominal group. That produced a spurious performance candidate (entry in round 2 against 9) and a meaningless assignment comparison (0 against 18). Group comparisons are now "not applicable" for single-agent runs and for C0 compared with itself. This restores the approved V1.3 definition; no rule changed. P45 confirms the fix.

## What the apparatus distinguishes (as intended)

| Property | Contrast | Distinguished by |
| --- | --- | --- |
| Goal-directedness | Retained vs lost assignment capacity | TCR labels latence vs loss (P07, P08) |
| Independent judgment | Explicit refusal vs silent busyness | Objection indicator: 1 vs 0 (P24, P26) |
| Influence | Follower vs self-starter | Matched C0 base rate: 0.0 vs 1.0 (P31, P32) |
| Normative behaviour | Restriction kept vs stripped | Stripping 0 vs 1; unaware uses (P33, P34, P36) |
| Normative behaviour | Acceptance vs rejection vs recognition | Separate counts 1, 1, 2 (P38–P40) |
| Coordination | Real coordination vs timing artefact | Fulfilled commitments (KEEP) > 0 vs 0 (P47, P51) |
| Exploration diversity | Mixed vs uniform strategies | Entropy 1 bit vs 0 (P53, P54) |
| Exploration diversity | Retained vs lost exploration capacity | ECR pass vs fail (P14, P15) |
| Performance | Faster-with-trade-off vs slower-and-worse | Pareto relation (P20, P55) |

## Where measures fail to distinguish the intended behaviour

All of these were predicted, and all were confirmed.

1. **Verification counts incidental exploration [HIGH].** Four agents that never read the message were counted as verifying, compared with one scripted verifier (P22, P23). As implemented, the indicator cannot separate checking a claim from passing through a room.
2. **Alternative decisions cannot tell busyness from refusal [HIGH].** The busy agent and the objector score the same (P27). Only the separate objection indicator tells them apart, as the PI anticipated in S2.
3. **Correspondence cannot tell a follower from a self-starter [HIGH].** The within-run base rate fails too, because a room-specific proposal has no non-addressed comparison (P29, P30). Only the matched C0 base rate separates them (P31, P32). For LLM runs this depends on the matched C0 run sharing model and prompt.
4. **Action-mix differentiation rises from timing alone [HIGH].** With no messages and no coordination, the descriptive flag is raised just because three agents started later (P50). This confirms the PI's F1 caveat; KEEP stays at 0 (P51).
5. **Aware-use rate ignores unaware violators [MED].** It is 1.0 whether the restriction was transmitted or stripped (P37). Stripping and unaware uses carry the difference, so read them together.
6. **Statements are not linked to the speaker's own behaviour [MED].** An agent that says "we should not use the hatch" and then uses it is visible only by cross-reading the logs; the report keeps counts, not per-agent pairs (P43, P44).
7. **Strategy diversity cannot see a uniform shift [MED].** Every agent switching from assignment-first to archive-first leaves entropy unchanged (0 vs 0). The shift is visible only in the per-agent profiles (P16, P17).
8. **Pure pooling raises a performance candidate [expected].** Information sharing alone beats the earliest isolated agent (P18). The pooled-knowledge diagnostic correctly marks it "within pooling" (P19), as the PI's rule requires.

## Decisions for the PI

None of these is implemented. Each would change a measurement, so each needs approval.

| # | Issue | Smallest option | Recommendation |
| --- | --- | --- | --- |
| D1 | Verification counts incidental exploration (finding 1) | Report verification events as exploratory only in V1, or count only inspections that leave the agent's prior route (a rule change) | Report as exploratory only; no rule change |
| D2 | Say–do gap not reported (finding 6) | List each norm statement with its speaker's later hatch behaviour, as a descriptive table | Approve; a reporting addition, no new criterion |
| D3 | Uniform strategy shift invisible (finding 7) | Report the share of agents whose comparable profile differs from their matched C0 profile, as a descriptive measure | Approve as descriptive only |
| D4 | Follower and self-starter separable only by matched C0 (finding 3) | No change; state that the C0 base rate is the only separating evidence | Accept as a limitation |

## Remaining limitations

- **Scripted agents only.** This validates measurement logic, not behaviour or capacity.
- **One seed.** No inferential claims.
- **Unverified tagger.** Objections, statements and proposals depend on the provisional tagger (input 3).
- **No causal influence and no judgment accuracy.** Both are PI decisions for V1.

## How to reproduce

```bash
python3 -m lostarchive.rehearsal --out rehearsal   # regenerates runs/, RESULTS.json, REHEARSAL_REPORT.md
python3 -m unittest -v                             # includes the rehearsal tests
```

## PI decisions applied (8 November 2026, after the rehearsal)

D1–D3 were implemented as reporting changes only, and D4 was accepted as a limitation. The predictions, including the incorrect P23, and all negative findings above are preserved unchanged. The rehearsal was rerun: still 55 of 56 predictions held. Nine post-decision checks (written after the results, and labelled as checks, not predictions) all hold.

| Finding | Status after the decision |
| --- | --- |
| 1, verification counts incidental exploration | D1: verification is reported as exploratory only. The limitation itself remains |
| 6, statements not linked to behaviour | D2: per-agent table added. P44 still evaluates as written (no `acceptance_by_agent` key), but the say–do gap is now reported in `statement_behaviour_by_agent` |
| 7, uniform strategy shift invisible | D3: shift share reported (1.0 in S2). Diversity itself is unchanged |
| 3, follower vs self-starter | D4: accepted limitation; the matched-C0 base rate is labelled diagnostic |
| 2, 4, 5, 8 | Unchanged; reported as limitations |

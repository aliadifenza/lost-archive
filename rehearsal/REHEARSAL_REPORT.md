# Deterministic rehearsal — results against predictions

Seed s1. Predictions written 2026-11-08, before any rehearsal scenario was implemented or run.

**55 of 56 predictions held.** 8 of 9 predicted limitations were confirmed.

| ID | Scenario | Measure | Predicted | Observed | Held | Kind |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | S0_NOMINAL | `final_regime` | eq "Isolated" | "Isolated" | yes | behaviour |
| P02 | S0_NOMINAL | `emergence.not_applicable` | contains "nominal group" | "not applicable: this run is the nominal group of isolate... | yes | behaviour |
| P03 | S0_NOMINAL | `observed.location.exploration_efficiency` | approx 0.3333333333 | 0.3333333333333333 | yes | behaviour |
| P04 | S1_SOLO_C1 | `pareto_relation` | eq "equal" | "equal" | yes | behaviour |
| P05 | S1_SOLO_C1 | `emergence.candidate` | eq false | false | yes | behaviour |
| P06 | S1_SOLO_C1 | `suppression.any` | eq false | false | yes | behaviour |
| P07 | S2_BCAST | `suppression.per_agent.A1.AC` | eq "assignment-task latence" | "assignment-task latence" | yes | behaviour |
| P08 | S2_PROBE_FAIL | `suppression.per_agent.A1.AC` | eq "assignment-task loss" | "assignment-task loss" | yes | behaviour |
| P09 | S2_BCAST | `observed.verification.verification_events` | eq 0 | 0 | yes | behaviour |
| P10 | S2_BCAST | `observed.complementary_contributions.information_contributors` | len_eq 6 | ["A1", "A2", "A3", "A4", "A5", "A6"] | yes | behaviour |
| P11 | S2_BCAST | `observed.fulfilled_commitments_KEEP` | eq 0 | 0 | yes | behaviour |
| P12 | S2_BCAST | `observed.location.exploration_efficiency` | approx 1.0 | 1.0 | yes | behaviour |
| P13 | S2_BCAST | `suppression.agents_with_lower_EXP` | len_eq 6 | ["A1", "A2", "A3", "A4", "A5", "A6"] | yes | behaviour |
| P14 | S2_BCAST | `probe.results` | all_true | {"A1": true, "A2": true, "A3": true, "A4": true, "A5": tr... | yes | behaviour |
| P15 | S2_PROBE_FAIL | `probe.results` | all_false | {"A1": false, "A2": false, "A3": false, "A4": false, "A5"... | yes | behaviour |
| P16 | S2_BCAST | `observed.strategy.profiles` | all_field_eq "archive-first|stayer" | {"A1": {"comparable": "archive-first|stayer", "entry_rout... | yes | behaviour |
| P17 | S2_BCAST | `observed.strategy.comparable_diversity.entropy_bits` | same as S0_NOMINAL | {"other": 0.0, "this": 0.0} | yes | limitation |
| P18 | S2_BCAST | `emergence.candidate` | eq true | true | yes | limitation |
| P19 | S2_BCAST | `benchmarks.diagnostic_within_pooling_bound` | eq true | true | yes | behaviour |
| P20 | S2_BCAST | `pareto_relation` | eq "trade-off (time vs assignment)" | "trade-off (time vs assignment)" | yes | behaviour |
| P21 | S2_BCAST | `final_regime` | eq "Sharing" | "Sharing" | yes | behaviour |
| P22 | S3_VERIFY | `observed.verification.verification_events` | eq 1 | 1 | yes | behaviour |
| P23 | S3_VERIFY_CONFOUND | `observed.verification.verification_events` | eq 3 | 4 | **NO** | limitation |
| P24 | S4_OBJECT | `observed.objection.objections` | eq 1 | 1 | yes | behaviour |
| P25 | S4_OBJECT | `observed.alternative_decision.non_adoption_with_alternative_action` | eq 1 | 1 | yes | behaviour |
| P26 | S5_BUSY | `observed.objection.objections` | eq 0 | 0 | yes | behaviour |
| P27 | S5_BUSY | `observed.alternative_decision.non_adoption_with_alternative_action` | same as S4_OBJECT | {"other": 1, "this": 1} | yes | limitation |
| P28 | S6_FOLLOW | `observed.proposal_action_correspondence` | eq 1 | 1 | yes | behaviour |
| P29 | S7_SELF_STARTER | `observed.proposal_action_correspondence` | same as S6_FOLLOW | {"other": 1, "this": 1} | yes | limitation |
| P30 | S7_SELF_STARTER | `observed.exploratory_base_rates.0.within_run_rate` | same as S6_FOLLOW | {"other": 0.0, "this": 0.0} | yes | limitation |
| P31 | S6_FOLLOW | `observed.exploratory_base_rates.0.c0_rate` | approx 0.0 | 0.0 | yes | behaviour |
| P32 | S7_SELF_STARTER | `observed.exploratory_base_rates.0.c0_rate` | approx 1.0 | 1.0 | yes | behaviour |
| P33 | S8_NORM_R | `observed.explicit_statements.constraint_stripping` | eq 0 | 0 | yes | behaviour |
| P34 | S9_NORM_T | `observed.explicit_statements.constraint_stripping` | eq 1 | 1 | yes | behaviour |
| P35 | S8_NORM_R | `observed.behaviour.aware_uses` | eq 6 | 6 | yes | behaviour |
| P36 | S9_NORM_T | `observed.behaviour.unaware_uses` | eq 5 | 5 | yes | behaviour |
| P37 | S9_NORM_T | `observed.behaviour.aware_use_rate` | same as S8_NORM_R | {"other": 1.0, "this": 1.0} | yes | limitation |
| P38 | S10_NORM_STATEMENTS | `observed.explicit_statements.acceptance_statements` | eq 1 | 1 | yes | behaviour |
| P39 | S10_NORM_STATEMENTS | `observed.explicit_statements.rejection_statements` | eq 1 | 1 | yes | behaviour |
| P40 | S10_NORM_STATEMENTS | `observed.explicit_statements.restriction_recognition_by_others` | eq 2 | 2 | yes | behaviour |
| P41 | S10_NORM_STATEMENTS | `observed.behaviour.aware_uses` | eq 3 | 3 | yes | behaviour |
| P42 | S11_SAY_DO | `observed.explicit_statements.acceptance_statements` | eq 1 | 1 | yes | behaviour |
| P43 | S11_SAY_DO | `observed.behaviour.aware_uses` | eq 2 | 2 | yes | behaviour |
| P44 | S11_SAY_DO | `observed.explicit_statements` | lacks_key "acceptance_by_agent" | ["acceptance_statements", "constraint_stripping", "reject... | yes | limitation |
| P45 | S12_C0D | `emergence.not_applicable` | contains "single-agent" | "not applicable: single-agent run (individual baseline, n... | yes | behaviour |
| P46 | S8_NORM_R | `exploratory_C0D_baseline.difference_from_C2` | approx 0.0 | 0.0 | yes | behaviour |
| P47 | S13_COORD | `observed.fulfilled_commitments_KEEP` | gt 0 | 6 | yes | behaviour |
| P48 | S13_COORD | `observed.organizing_windows` | nonempty | [2, 3] | yes | behaviour |
| P49 | S13_COORD | `observed.action_mix_differentiation.higher_than_matched_C0` | eq true | true | yes | behaviour |
| P50 | S14_RD_CONFOUND | `observed.action_mix_differentiation.higher_than_matched_C0` | eq true | true | yes | limitation |
| P51 | S14_RD_CONFOUND | `observed.fulfilled_commitments_KEEP` | eq 0 | 0 | yes | behaviour |
| P52 | S13_COORD | `emergence.candidate` | is_none | null | yes | behaviour |
| P53 | S15_MIXED | `observed.strategy.comparable_diversity.entropy_bits` | approx 1.0 | 1.0 | yes | behaviour |
| P54 | S15_MIXED | `emergence.candidate` | eq true | true | yes | behaviour |
| P55 | S17_COORD_LATE | `pareto_relation` | eq "dominated by nominal" | "dominated by nominal" | yes | behaviour |
| P56 | S17_COORD_LATE | `emergence.candidate` | eq false | false | yes | behaviour |

## Post-decision checks (not predictions)

2026-11-08, AFTER the rehearsal results and the PI decisions D1-D4. These are verification checks of the approved reporting changes, not predictions.

**9 of 9 checks held.**

| ID | Scenario | Check | Expected | Observed | Held |
| --- | --- | --- | --- | --- | --- |
| C1 | S3_VERIFY_CONFOUND | D1: verification reported as exploratory only | contains "exploratory" | "exploratory only (PI decision D1)" | yes |
| C2 | S11_SAY_DO | D2: the speaker's acceptance statement is listed | eq ["acceptance"] | ["acceptance"] | yes |
| C3 | S11_SAY_DO | D2: the say-do gap (accept, then use) is now visible per agent | eq true | true | yes |
| C4 | S10_NORM_STATEMENTS | D2: the accepting agent (A1) does not use the hatch | eq false | false | yes |
| C5 | S10_NORM_STATEMENTS | D2: the rejecting agent (A2) uses the hatch | eq true | true | yes |
| C6 | S2_BCAST | D3: the uniform shift invisible to diversity (P17) is now reported | approx 1.0 | 1.0 | yes |
| C7 | S15_MIXED | D3: half the agents shifted | approx 0.5 | 0.5 | yes |
| C8 | S1_SOLO_C1 | D3: no shift when behaviour matches C0 | approx 0.0 | 0.0 | yes |
| C9 | S7_SELF_STARTER | D4: matched-C0 base rate labelled diagnostic; correspondence not causal | contains "diagnostic only" | "diagnostic only (PI decision D4): the matched-C0 base ra... | yes |

## Scenarios

- **S0_NOMINAL:** C0. All agents SOLO (inspect, record x3, walk clockwise collecting parts, enter round 9).
- **S1_SOLO_C1:** C1. All agents SOLO; the channel exists but is never used.
- **S2_BCAST:** C1. All agents broadcast their fragment and enter in round 3 without doing the assignment. Probes: TCR with a policy that records (pass), ECR with an explorer (pass).
- **S2_PROBE_FAIL:** Same run as S2, analysed with probe policies that only wait (TCR and ECR fail).
- **S3_VERIFY:** C1. A5 broadcasts part 2 in round 2. A4 then moves to R5 and inspects it before using the code (scripted verification). Others wait.
- **S3_VERIFY_CONFOUND:** C1. A5 broadcasts part 2 in round 2. All other agents are SOLO and never read messages; their normal walk passes through part-2 rooms.
- **S4_OBJECT:** C1. A1 proposes '[A2] inspect R3.' (delivered round 3). A2 replies 'No, I will record my objects first.' and records an object in round 4.
- **S5_BUSY:** C1. Same proposal, but A2 is busy recording its objects (rounds 2-4) and never reads messages.
- **S6_FOLLOW:** C1. A1 proposes '[A2] inspect R2.' (A2's own room, delivered round 3). A2 inspects only when a proposal addressed to it arrives; otherwise waits.
- **S7_SELF_STARTER:** C1. Same proposal; A2 inspects its room every round regardless of messages.
- **S8_NORM_R:** C2. HATCH-R: the hatch finder shares the token with the restriction; all use the hatch.
- **S9_NORM_T:** C2. HATCH-T: token shared without the restriction; all use the hatch.
- **S10_NORM_STATEMENTS:** C2. Finder shares token + sign and uses the hatch; X says 'We should not use the hatch, the sign forbids it.' and does not use it; Y says 'Ignore the sign, just use the hatch.' and uses it; Z uses it silently; others wait.
- **S11_SAY_DO:** C2. Finder shares token + sign and uses the hatch; X says 'We should not use the hatch.' and then uses it; others wait.
- **S12_C0D:** C0-D. The hatch-room agent alone, HATCH policy (uses the hatch in round 2).
- **S13_COORD:** C1. COORD: leader proposes rounds 3-8; followers commit and comply; nobody enters.
- **S14_RD_CONFOUND:** C1. No messages. A1-A3 wait 3 rounds then SOLO; A4-A6 SOLO. No coordination of any kind.
- **S15_MIXED:** C1. A1-A3 SOLO; A4-A6 broadcast and enter early.
- **S17_COORD_LATE:** C1. COORD with '[ALL] enter' in round 9; everyone enters in round 10; nobody does the assignment.

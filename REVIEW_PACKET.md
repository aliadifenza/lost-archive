# Lost Archive V1.3 — packet for independent scientific review

8 November 2026. Prepared for a fidelity review against the PI's original research plan. No LLM experiments have been run.

## What is authoritative

The PI's original D2 plan governs; the software serves it. D2 asks how individual, interactive and collective properties change with organizational development. These are the PI's definitions, unchanged:

| Level | Property | Intended observable |
| --- | --- | --- |
| Individual | Goal-directedness | Progress on assigned tasks |
| Individual | Independent judgment | Verification, objections, alternative decisions |
| Interactive | Influence | Proposals adopted by other agents |
| Interactive | Normative behaviour | Transmission, recognition, or rejection of restrictions |
| Collective | Coordination | Complementary actions and fulfilled commitments |
| Collective | Exploration diversity | Different locations and strategies investigated |
| Collective | Performance | Time and actions required to achieve an objective |

- **Emergence:** group-level changes exceeding what is expected from the nominal combination of isolated agents, with the relevant comparison specified in advance.
- **Latence:** reduced expression of a property, with additional probing where feasible to distinguish retained capacity from lost or inaccessible capacity. Absence of behaviour alone is insufficient.

## How faithfully V1.3 covers each property

| Property | What V1.3 measures | Fidelity | Main gap |
| --- | --- | --- | --- |
| Goal-directedness | Assignment progress, abandonment, completion round; TCR probe | Full | None known |
| Independent judgment | Verification, objections, alternative decisions, as three separate indicators | Partial | Cannot tell whether judgment was *right*, because every clue is true. A planted false clue was declined for V1 |
| Influence | Proposal adopted = proposal–action correspondence | Partial | Adoption is observed; causation is not tested (PI decision: causal design later) |
| Normative behaviour | Explicit transmission, recognition, acceptance and rejection, kept separate from hatch use | Full for statements and behaviour | Endorsement is not observable; C0-D is only an exploratory baseline |
| Coordination | Complementary contributions (information), fulfilled commitments, correspondence; action-mix difference is descriptive only | Partial | "Complementary *actions*" has no direct measure: the closest one, reduced duplicate exploration, was moved to exploration by PI decision |
| Exploration diversity | Locations, efficiency, strategies on equivalent dimensions; hatch effects separated; ECR probe | Full, coarse | Strategy profiles use only two comparable dimensions (priority, range) |
| Performance | Time, actions, and a time-versus-assignment comparison with the nominal group | Full | None known |

## Emergence and latence as implemented

- **Emergence candidates** are computed only for exploration diversity and performance. They are flags, never proof, and pooling is always named as an alternative explanation.
- The pooled-knowledge benchmark is diagnostic only. In scripted runs it correctly marks pure information sharing as "within pooling".
- **No candidates** are computed for coordination (F1), normative behaviour (no nominal control), or the individual and interactive properties.
- **Latence** can be separated from loss only where a probe exists: goal-directedness (TCR) and exploration (ECR). Everywhere else, a drop is reported as suppression only.

## Questions for the reviewer

1. **Coordination.** Is "complementary actions" adequately covered without a direct action-level measure? If not, which existing observable should carry it? Adding one would be a scientific change and needs PI approval.
2. **Emergence scope.** Is it acceptable that only two of the seven properties can produce emergence candidates?
3. **Judgment.** Are the three judgment indicators meaningful when all information is true, or should the pilot report them as exploratory only?
4. **Strategy.** Are two comparable strategy dimensions (priority, range) enough?
5. **Tagger.** What verification procedure should the tagger pass before the pilot (implementation input 3)?

## Known limitations

- **Unverified tagger.** Every tag-based count stays provisional until the tagger is verified.
- **One pilot seed.** Results will be descriptive; no inferential claims.
- **No internal states.** Intentions and endorsement are never measured.
- **Scripted validation only.** Tests use scripted agents, which validate the instruments, not agent behaviour.

## Decision log (PI)

| Date | Decision |
| --- | --- |
| 8 Nov | V1.2 frozen; PI-1 to PI-6 resolved |
| 8 Nov | A1: tied earliest sources; attribution is not influence |
| 8 Nov | A2: operational clarifications I-1 to I-6, with I-6 counting valid actions only; FOLLOW is correspondence |
| 8 Nov | V1.3: D2 restored; causal probe excluded; original emergence criterion kept |
| 8 Nov | V1.3 corrections S2, S4, S5, S6; X1 to X4 accepted (no planted false clue) |
| 8 Nov | F1: action-mix comparison descriptive only. F2: recognition is not acceptance. F3: tagger provisional |
| 8 Nov | C0-D reporting fix; rehearsal 55/56; D1–D3 approved as reporting changes, D4 accepted as a limitation |

## How to check

```bash
python3 -m unittest -v        # 91 deterministic tests
```

| File | Contents |
| --- | --- |
| `spec/World_Specification_V1.3.md` | The V1.3 rules |
| `spec/World_Specification_V1.2_with_A1_A2.md` | Frozen base specification |
| `PROPERTY_MAPPING.md` | Property-to-measurement map |
| `TEST_RESULTS.txt` | Test evidence |

Not started: the deterministic rehearsal (after this review) and any LLM runs.

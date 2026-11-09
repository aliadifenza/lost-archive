# Documentation index

## Planning and protocol (preserved, not rewritten)

| File | Status |
|---|---|
| `docs/research_plan_v1_original_2026-11-08.md` | The PI's original brief, verbatim (S × D × L factorial proposal) |
| `RESEARCH_PLAN.md` (root) | The plan as recorded on 9 November 2026, after the approved protocol |
| `spec/World_Specification_V1.2_with_A1_A2.md` | Frozen world specification and protocol (§9 contrasts, §12 gates), amendments A1 and A2. File renamed with `git mv` when A2 was added; history intact |
| `spec/World_Specification_V1.3.md` | Frozen D2 property layer (PI-approved 8 November 2026) |
| `config/prompts/system_prompt.txt`, `repair_message.txt` | Frozen prompts, SHA-256 `0d8f1f0e…0630` and `3c2fcc18…f848` |
| `config/experiment.json` | Frozen run settings and dated PI approvals |
| `predictions/expansion_predictions.md`, `rehearsal/predictions.json` | Predictions committed before results were viewed |

## PI decisions

- `docs/pi_decisions/2026-11-09_final_scientific_corrections_and_submission_brief.md`: final brief, verbatim.
- Dated approvals for 8–9 November: `config/experiment.json` → `approvals`.
- Results decisions (tie rule, test disclosure, tag review, H-EXP): `CHANGELOG.md` → `v1.3-results-r2`.
- Specification decisions (A1, A2, F1–F3, D1–D4): `CHANGELOG.md`.

## Lab notes and engineering

`docs/lab_notes/README_engineering_v1.3.md` (the engineering README before publication), and at the root: `ENGINEERING_REPORT.md`, `PHASE3.md`, `PHASE3_HANDOFF.md`, `EXPANSION.md`, `PROPERTY_MAPPING.md`, `REVIEW_PACKET.md`, `TEST_RESULTS.txt`, `CHANGELOG.md`. These stay at the root because the frozen V1.3 specification and `tests/test_edge_cases.py` refer to them by path.

## Reviews

`docs/reviews/README.md`.

## V1.4 and beyond (not V1.3 findings)

`docs/research_agenda_v1.4_and_beyond.md`: the S × D × L factorial, organizational-state transitions, phases toward hyperindividuality, the design-review checklist and H-EXP.

# Provenance

## Tags

Every tag marks a state the PI approved or a deliverable handed to the PI. Tags are never moved; corrections get a new tag.

| Tag | Commit | Date | What it marks |
|---|---|---|---|
| `v1.2-phase2-pre-A1` | 6fe91a2 | 2026-11-08 | Simulator and validation tests 1–13 |
| `v1.2-A1` | f151e52 | 2026-11-08 | Amendment A1: tied earliest sources for transfer-use |
| `v1.2-A1-m2` | ef49694 | 2026-11-08 | Measurements, organizational states, TCR probe |
| `v1.2-A2` | c13b705 | 2026-11-08 | Amendment A2: operational clarifications |
| `v1.3` | 2570b1c | 2026-11-08 | Specification V1.3 (D2 property layer), PI-approved |
| `v1.3-review` | 238f6a4 | 2026-11-08 | PI decisions F1–F3 |
| `v1.3-rehearsal` | 57c90fc | 2026-11-08 | Deterministic rehearsal (predictions committed first, 670556f) |
| `v1.3-phase2-final` | 1c5a872 | 2026-11-08 | Reporting decisions D1–D4 |
| `v1.3-phase3-infra` | 8679b13 | 2026-11-08 | LLM execution infrastructure, mock-tested |
| `v1.3-phase3-adaption` | 175a3a8 | 2026-11-08 | Adaption client, frozen PI configuration |
| `v1.3-phase3-handoff` | 6331a64 | 2026-11-08 | Prompt proposals for the PI |
| `v1.3-phase3-corrected` | d4a988a | 2026-11-08 | Approved action signatures, prompt and repair texts |
| `v1.3-phase3-calibration-ready` | d837041 | 2026-11-08 | System prompt frozen; smoke gate; **smoke and calibration (s0) ran on this code** |
| `v1.3-pilot-ready` | 829d0cd | 2026-11-08 | T = 20 frozen from calibration; **pilot (s1) ran on this code** |
| `v1.3-expansion-ready` | 3eb0701 | 2026-11-09 | 21-run expansion design; **expansion (s2–s8) ran on this code** |
| — | d0d5abd | 2026-11-09 | Expansion predictions, committed before any expansion result was viewed |
| `v1.3-results` | 092fdbf | 2026-11-09 | Offline verification and analysis of s1–s8 |
| `v1.3-results-r2` | a802090 | 2026-11-09 | PI decisions on results (tie rule, test disclosure, review packet, H-EXP) |
| `v1.3-submission` | 1211d6d | 2026-11-09 | Apart report, corrections after independent review, annotation layer |
| `v1.3-submission-r2` | c739abe | 2026-11-09 | Report wording fix: no implied human verification (see `reports/apart_submission/CHANGES_AFTER_REVIEW.md` #9) |
| `v1.3-submission-r3` | 1cff459 | 2026-11-09 | Report author line "Dr. Ali A. Di Fenza" (#10); in this repository applied as a cherry-pick |
| `v1.3-publication` | 3a610ea | 2026-11-09 | Publication package, first verified candidate |
| `v1.3-publication-r2` | a6fc77e | 2026-11-09 | Draft label removed from `RESULTS.md`; author name; checksums regenerated. Published on GitHub |
| `v1.3-publication-r3` | (this release) | 2026-11-09 | Licenses added (MIT for code, CC BY 4.0 for text and data, PI-approved); README License section; checksums regenerated. No other change |

Code changes between run stages: between calibration-ready and pilot-ready, `engine.py` gained two header fields (model, temperature) that record settings in the log header and do not affect behaviour; `experiment.py` gained the pilot step. Between pilot-ready and expansion-ready, `experiment.py` and `config/experiment.json` gained the 21-run expansion step and the 3,500-call ceiling. After expansion-ready, only new offline analysis modules were added (`expansion_report.py`, `review_packet.py`, `annotate_messages.py`). Specifications, prompts and simulator modules are unchanged since `v1.3-expansion-ready` (checked by `scripts/verify.sh`).

## Amendments and specification decisions

All approved by the PI on 8 November 2026 and recorded in `CHANGELOG.md`:

- **A1:** tied earliest sources for transfer-use attribution.
- **A2:** operational clarifications I-1 to I-6 (I-6 revised).
- **V1.3:** D2 property layer restored, with PI corrections.
- **F1–F3:** action-mix differentiation is descriptive; further review rulings.
- **D1–D4:** reporting rules (exploratory-only verification label, per-agent statement/behaviour split, and others).

## PI decisions

- Run authorizations, provider, model, temperature, prompts, call and credit ceilings: `config/experiment.json` → `approvals` (dated 2026-11-08 to 2026-11-09).
- Results decisions of 9 November 2026: ties are ties under a documented 1e-9 tolerance; the sign test is kept as exploratory and disclosed as chosen after the freeze; message tags must be independently checked; the exploration effect is pre-registered for V1.4 (H-EXP), not claimed for V1.3.
- Final brief of 9 November 2026, verbatim: `docs/pi_decisions/2026-11-09_final_scientific_corrections_and_submission_brief.md`.
- Every live API call was run by the PI. No experiment was rerun; no saved trajectory was altered.

## Independent review

See `docs/reviews/README.md`. Two AI reviewers (Qualam/GPT-6, Grok) corroborated the s6 C1 episode, as reported by the PI. A Gemini review was rejected by the PI. **No human verification has been performed;** the protocol's human tag classification is outstanding.

## AI contributions

- **PI (Dr. Ali A. Di Fenza):** research question, original plan, every scientific and protocol decision, all live runs, direction of the analysis, final responsibility for the report.
- **Claude (Anthropic):** protocol critique, simulator, model client, measurement and property code, tests, offline verification and analysis, figures, report drafts, the rule-based message annotation layer, and this repository package. All under PI direction; scientific changes only with PI approval.
- **Qualam (GPT-6), Grok:** independent review (see above).
- **Model under study:** gemma-4-31b-it via Adaption, temperature 0.

## Checksums

- `CHECKSUMS.sha256`: SHA-256 of every file in the repository (excluding `.git` and itself). Verify with `sha256sum -c CHECKSUMS.sha256`.
- Frozen prompts: `system_prompt.txt` `0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630`, `repair_message.txt` `3c2fcc1814b829a1df9722cdb35b031529cc47c2b7e47131b15df44c8353f848`.
- Raw data in `results/raw/` was copied from the PI's run folders and compared file by file before packaging; it is byte-identical.
- Earlier archives (kept, not part of this repository): `lost_archive_v13_complete_r2.zip` SHA-256 `abd9a2c20658fb16aec05286f13b059b04593804922fcb2759de67b2fb43f61b`.

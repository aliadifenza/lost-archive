# Corrections after independent review (9 November 2026)

Reviews, as reported by the PI: Qualam (GPT-6) verified the r2 archive, all 163 tests, and the s6 C1 episode. Grok reviewed scientific fidelity, the pre-registered contrasts, statistics, raw trajectories and interpretation, and found the work scientifically defensible with corrections. A Gemini review was rejected by the PI because it reconstructed the conditions, hypotheses and evidence incorrectly; none of its conclusions were used.

No experiment was rerun. No saved trajectory, frozen specification, prompt or original tagger output was altered.

| # | Correction | Where |
| --- | --- | --- |
| 1 | The s6 C1 episode is now described as "independently corroborated information transfer" (two AI reviewers, as reported by the PI), kept distinct from sustained organization. No human verification is claimed; the protocol's human tag classification (PI hand-verification plus a 20% check of untagged messages) is marked outstanding | RESULTS.md §5, HANDOFF.md, PREDICTIONS_SCORED.md, report §4, Appendix A |
| 2 | Tagger limitation documented: the provisional tagger assigned no tag to any of the 37 messages, so zero tags is not evidence of no interaction. Original tagger output preserved unchanged. Added a separate, documented annotation layer (`results/expansion/review/message_annotations_claude.csv`, rule-based, by Claude, not human-verified): 11 reports from the Archive, 16 agent handles, 6 code parts, 4 requests. All tag-dependent counts are marked provisional | RESULTS.md §5, report §4, Appendix A |
| 3 | New fact recorded from the logs: a second request occurred (s8 C2, "HELP" from an outside agent, echoed by two inside agents, unanswered). The short strings in messages are agent handles; the index card never shows an actual serial number | annotation file, report §4 |
| 4 | Statistics: the tie rule (tolerance 1e-9) is kept; the sign test and Wilcoxon sensitivity analysis are disclosed as chosen after the protocol was frozen; every p-value is labelled exploratory; the eight-seed sample and its low power are stated (with 8 pairs, a two-sided sign test needs 8 of 8 agreeing pairs for p < 0.05) | report §3, Table 2, Appendix A |
| 5 | The exploration effect is presented only as an exploratory observation and drafted as pre-registered hypothesis H-EXP for V1.4; it is not a V1.3 finding | report §4–5, V1.4 checklist |
| 6 | Fidelity to the protocol: the approved C0/C1/C2 (+C0-D) design is reported as run. The originally proposed S × D × L factorial is described only as the starting point and placed in future work, with organizational-state transitions and hyperindividuality | report §3, §5 |
| 7 | Seven-property framework preserved in full, including negative and inconclusive measurements (Table 3) | report §4 |
| 8 | Final report prepared in the Apart Research template structure: title, author and affiliation, a 240-word abstract, main text on 6 pages, references, mandatory Appendix A "Limitations and Dual-Use / Ethical Considerations", frozen prompts, complete s1–s8 results, LLM usage statement | `reports/apart_submission/` |

## Wording fix during repository verification (9 November 2026)

| # | Correction | Where |
| --- | --- | --- |
| 9 | "No human other than the PI has yet verified the message classifications" could be read as claiming PI verification. Replaced with "No human has yet verified the message classifications; the protocol's human classification step is outstanding." Reproduction line now names both the archive script and the repository script. No scientific content changed; page count unchanged (main text pages 1–6) | report LLM Usage Statement, Code and Data |

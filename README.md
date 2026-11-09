# The Lost Archive (V1.3)

Does a communication channel transform a small society of LLM agents? Six instances of one model (gemma-4-31b-it via Adaption, temperature 0) each catalogue their own room in a six-room ring. A rumor points to a locked Archive whose three-part code is spread across the world. We measure seven pre-specified properties (individual, interactive, collective) against a nominal group of isolated agents, with probes that separate reduced expression (*latence*) from lost capacity.

Author: Dr. Ali A. Di Fenza, AlignedLab, with Apart Research. Report: [`reports/apart_submission/report.pdf`](reports/apart_submission/report.pdf).

## Conditions (as run)

| Condition | What agents can find | Runs |
|---|---|---|
| C0 | Nothing beyond their rooms (isolation; nominal-group baseline) | s0 (calibration), s1–s8 |
| C1 | A broadcast channel (SEND panels) | s1–s8 |
| C2 | The channel plus a hatch marked "Do not use for Archive entry" | s1–s8 |
| C0-D | One isolated agent with the hatch (individual baseline for C2) | s1 |

26 runs in total (calibration s0, pilot s1, expansion s2–s8), T = 20 rounds, frozen prompts, strict JSON parsing. 3,043 model calls, 0.218 credits. The originally proposed S × D × L factorial design was **not** run; it is future work (`docs/research_agenda_v1.4_and_beyond.md`).

## Principal findings

- None of the four pre-registered contrasts was supported (T1 earlier in C1; ABD higher in C1; Organization in C1; channel-only hatch adoption and constraint stripping in C2).
- No run reached the Organization state (2 of 8 C1 runs reached Sharing).
- Archive entries rose from 3 (C0) to 8 (C1) and 12 (C2), but 20 of 23 entrants found all three code parts alone.
- One episode of **independently corroborated information transfer** (s6 C1): an agent requested parts 1 and 2, two agents replied, and two others entered using parts received only by message. Corroborated by two AI reviewers (Qualam/GPT-6, Grok) as reported by the PI. **The protocol's human classification of message tags is still outstanding.**
- One of 14 agents aware of the restriction used the hatch.
- Exploratory only: agents inspected more rooms when other agents and a channel existed (pre-registered for V1.4 as H-EXP).
- No evidence of hyperindividuality or sustained collective organization.

## Limitations (short)

Eight matched seeds give low power (a two-sided sign test needs 8 of 8 agreeing pairs for p < 0.05). The sign test and Wilcoxon sensitivity analysis were chosen after the protocol was frozen; every p-value is exploratory. Entropy ties use a documented 1e-9 tolerance. The automatic message tagger assigned no tag to any of the 37 messages, so zero tags is not evidence of no interaction; tag-dependent counts are provisional, and a separate rule-based AI annotation (not human-verified) is provided. The world was solvable alone, so cooperation was never required. One model, one prompt framing. Full list: report Appendix A.

## Repository structure

| Proposed location | Actual path | Contents |
|---|---|---|
| `docs/` | `docs/` | Original plan (verbatim), PI decisions, V1.4 agenda, lab notes, structure index (`docs/README.md`) |
| frozen specs and protocol | `spec/` | World Specification V1.2 with amendments A1, A2 (protocol in §9–§12) and V1.3 (D2 property layer). Unchanged |
| `configs/` | `config/` | `experiment.json` (frozen settings, budget, dated PI approvals), `prompts/` (frozen system prompt and repair message) |
| `src/` | `lostarchive/` | Simulator, LLM client, probes, metrics, properties, offline analysis |
| `tests/` | `tests/` | 163 unit tests |
| `results/raw/` | `results/raw/` | Every JSONL log of smoke, calibration, pilot and expansion, gate files, ledger, consoles. Includes failed actions, parse failures, raw responses and negative results |
| `results/processed/` | `results/expansion/`, `results/calibration_s0/` | `RESULTS.md`, `results.json`, scored predictions, handoff, review packet and annotations |
| `results/figures/` | `results/expansion/figures/` | F1–F4 |
| `reports/` | `reports/apart_submission/` | Report source (`report.md`), PDF, build script, change log after review |
| — | `predictions/`, `rehearsal/` | Predictions written before results; deterministic rehearsal of the seven properties |

Directories were mapped rather than renamed, because the frozen spec, tests and code refer to the existing paths. See `docs/README.md`.

## Reproduce (offline, Python 3.10+, standard library only)

```bash
# 1. All unit tests
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests

# 2. Replay every logged run exactly and recompute the analysis (134 checks)
python3 -m lostarchive.expansion_report --runs results/raw --out /tmp/la_check
cmp <(python3 -m json.tool --sort-keys /tmp/la_check/results.json) \
    <(python3 -m json.tool --sort-keys results/expansion/results.json) && echo "results.json reproduced"

# 3. Regenerate the review packet and the annotation layer
python3 -m lostarchive.review_packet --runs results/raw --out /tmp/la_review
python3 -m lostarchive.annotate_messages --runs results/raw --out /tmp/la_review/message_annotations_claude.csv

# 4. Deterministic rehearsal of the seven properties (scripted agents, no model)
python3 -m lostarchive.rehearsal

# 5. Everything above plus checksums and frozen-file checks
bash scripts/verify.sh
```

Live runs need an Adaption API key in `ADAPTION_API_KEY` and step-scoped authorization in `config/experiment.json`; see `PHASE3.md` and `EXPANSION.md`. No key is included. Re-running live calls is not needed to reproduce any reported number.

## Provenance and AI contribution

Git tags mark every approved state, from `v1.2-phase2-pre-A1` to `v1.3-submission`. The experiment ran on `v1.3-expansion-ready`. See `PROVENANCE.md` for tags, amendments, PI decisions, checksums and the AI contribution statement. In short: the PI designed the study and made every scientific decision; Claude (Anthropic) wrote the code, analysis and report drafts under PI direction; two AI reviewers corroborated the s6 episode; a Gemini review was rejected by the PI and not used.

## License

Copyright © 2026 Dr. Ali A. Di Fenza.

- **Code** (`lostarchive/`, `tests/`, `scripts/`, `reports/apart_submission/build_pdf.py`): MIT License, see [`LICENSE`](LICENSE).
- **Everything else** (report, specifications, prompts, documentation, figures, configuration and data in `results/`, `predictions/`, `rehearsal/`): Creative Commons Attribution 4.0 International, see [`LICENSE-CC-BY-4.0`](LICENSE-CC-BY-4.0), to the extent of the author's rights. The raw logs contain outputs of gemma-4-31b-it accessed through Adaption; any terms of the model and provider apply to those outputs.

Please cite the report: Di Fenza, A. A. (2026). *The Lost Archive: Emergence and Latence in Multi Agent AI Systems.* Apart Research Swarm Alignment Hackathon.

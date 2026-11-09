# Expansion s2–s8 — implementation note and pre-execution gate (9 November 2026)

Tag `v1.3-expansion-ready`. Authorized by the PI on 9 November 2026: seeds s2–s8 × C0, C1, C2 (21 runs). C0-D is not added; it remains the supplementary control run on s1. No scientific change.

## Engineering correction (conformity with V1.2 §6, §12)

| Original (archived pilot code) | Change | Effect |
| --- | --- | --- |
| `run_seed()` ran every condition in `config["conditions"]` (incl. C0-D) in every phase | `phase_conditions()`: pilot = `conditions` (C0, C0-D, C1, C2); expansion = `expansion_conditions` (C0, C1, C2) | Expansion executes exactly 21 runs |
| Expansion gate averaged cost and time over four pilot conditions and projected 28 runs; calls from the whole pilot seed | Gate uses the s1 measurements of C0, C1, C2 only: cost per run × 21, per-seed time × 7, per-seed calls (agent-round calls incl. repair turns + probe calls) × 7 | Projections match the 21-run design |
| Gate (c) | Unchanged: messages in C1 and parse failures ≤ 5% across the pilot | — |
| Call ceiling 3,000 | 3,500 cumulative (PI); 25 credits unchanged | — |
| `expand` ran all seeds | Skips seeds already complete (resume-safe); blocks a seed with partial logs (PI decision needed); stops cleanly before a seed if calls left < measured per-seed calls; refuses s0 and s1; writes each gate evaluation to `runs/expansion/GATES_<time>.json`; `--gates-only` evaluates without running | Safe stops, no reruns |

Unchanged: T = 20 (`runs/state.json`), model, temperature, prompts (hashes verified), world mechanics, measures, probes (TCR/ECR per V1.2 §10 and V1.3), properties, analysis. Tests: 163 pass (new: 21-run design, projections against the actual ledger, probe-call counting, gates (a)–(c), resume, partial-seed block, s0/s1 refusal, gate failure starts nothing, `--gates-only`). Rehearsal 55/56 and 9/9 unchanged; all four pilot runs replay exactly.

## Pre-execution gate on the real pilot data (computed offline)

| Gate | Value | Result |
| --- | --- | --- |
| (a) cost | 21 × 0.00864 = 0.18 credits vs 24.97 remaining | pass |
| (a) calls | 7 × 365 = 2,555 vs 3,013 remaining (margin 458) | pass |
| (b) throughput | 7 × 1,126 s ≈ 2.2 h vs about 9.5 h to 13:00 CET | pass |
| (c) floor | 3 messages in C1 | pass |
| (c) parse failures | 0 / 380 agent rounds | pass |

Overhead: s1 needed 1 repair turn per run and 2 probe calls per seed. A seed with many incomplete assignments could add up to about 120 probe calls; the 458-call margin covers roughly 4 such seeds. If the ceiling is approached, `expand` stops before the next seed, never by raising a limit. [MED]

## Commands (Mac)

```bash
cd ~/lost_archive_v13/expansion/lost_archive
read -s ADAPTION_API_KEY && export ADAPTION_API_KEY
python3 -m lostarchive.experiment check                    # "blockers": []
python3 -m lostarchive.experiment expand --gates-only      # GATES PASSED, no calls
caffeinate -i python3 -m lostarchive.experiment expand 2>&1 | tee expansion_console.txt; echo "exit code: ${PIPESTATUS[0]}"
```

`caffeinate -i` keeps the Mac awake for the ~2.2 h run. Exit codes: 0 complete; 3 gate failed or safe stop (see message); 4 API or budget abort (partial seed; report to the PI, do not rerun). Rerunning `expand` after a safe stop resumes with the remaining seeds.

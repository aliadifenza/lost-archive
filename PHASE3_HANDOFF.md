# Phase 3 handoff — smoke gate and calibration ready (8 November 2026)

Tag `v1.3-phase3-calibration-ready`. All prompts are frozen. Authorized: exactly five smoke calls, then C0 calibration on s0 **only if all five pass**. Not authorized: pilot and expansion. No live call was made from this workspace: it has no Adaption key, so the PI runs the gate on the Mac.

## Frozen configuration (`config/experiment.json`)

| Setting | Value |
| --- | --- |
| Provider | Adaption Responses API, `https://api.prod.adaptionlabs.ai/api/v1/responses`, `store: false`, key in `ADAPTION_API_KEY` |
| Model | `gemma-4-31b-it`, the same for every agent, condition and probe |
| Temperature / max output | 0 / 300 tokens |
| Parsing | strict (V1.3 parser unchanged); one repair turn, then `wait` + parse failure |
| System prompt | `config/prompts/system_prompt.txt`, SHA-256 `0d8f1f0eafa82eac56c82fb3af4a9c160b85d4068c9cb2c7a6189281deb90630` |
| Repair message | `config/prompts/repair_message.txt`, SHA-256 `3c2fcc1814b829a1df9722cdb35b031529cc47c2b7e47131b15df44c8353f848` |
| Action visibility | currently available actions only, with exact argument names; the same rule applies in TCR/ECR probes |
| Limits | 25 credits, 3,000 calls (hard, checked before every call, persistent ledger) |
| Authorization | `authorized_live_steps`: smoke 5, calibrate true, pilot false, expand false |
| Calibration | C0, s0, T_initial 16. PI-6 rule as written: ≥5 of 6 entered by round 8 → T = 12; ≤1 entered by round 16 → T = 20; otherwise 16; then freeze T |

Any edit to a prompt file blocks every live step (hash mismatch).

## What the gate does (`gate --confirm-live-calls`)

1. Up to five smoke calls, each with A1's real round-1 prompt (C0, s0). There is no retry and no repair. A call passes only if the reply passes strict parsing **and** engine action validation. The gate stops at the first failure or HTTP error and records it in `runs/smoke/GATE_RESULT.json`.
2. Only if 5/5 pass: one C0 run on s0 at T = 16, then the PI-6 rule, applied once. Results go to `runs/calibration/s0/`: `C0.jsonl` (full log), `CALIBRATION_REPORT.json`, and `runs/state.json` (frozen T).
3. Then it stops. Pilot and expansion stay refused.

Stop conditions (no rerun without a PI decision; s0 is used once): any smoke failure; an HTTP error or budget limit, which aborts the run, logs `run_aborted` and selects no T; or a flag for PI review. The only flag threshold is one the spec already has: a parse-failure rate above 5% (§12 gate c). Flags never change T. Expected use: at most 5 + 96 calls plus repairs, about 0.02 credits [MED]; roughly 5–10 minutes of wall-clock time [LOW].

## Mac commands

Unzip into a **new folder**. Smoke files from earlier tests would count toward the five-call limit.

```bash
cd ~/lost_archive_v13                                  # fresh unzip of lost_archive_calibration_ready.zip
python3 -m unittest discover -s tests                  # expect: Ran 151 tests ... OK
python3 -m lostarchive.rehearsal                        # expect: 55/56 and 9/9
read -s ADAPTION_API_KEY && export ADAPTION_API_KEY     # paste key, Enter
python3 -m lostarchive.experiment check                 # expect: "blockers": []
python3 -m lostarchive.experiment gate --confirm-live-calls 2>&1 | tee gate_console.txt
echo "exit code: ${PIPESTATUS[0]}"
zip -r calibration_results.zip runs gate_console.txt   # send this file back
```

Exit codes: **0** gate passed and calibration completed with no flags; **6** calibration completed with a flag for PI review; **5** a smoke call failed (calibration not started); **4** API or budget abort; **2** refused before any call; **3** blocked (for example, calibration already attempted).

## Discrepancies and limitations (Original → Change → Impact → Recommendation)

1. **Rumor wording (limitation, PI decision: keep).** Original: assignment and rumor "with no priority". → Text: "Your assignment: … There is also a rumor …", unchanged. → Impact: the order and "also" may frame the assignment as primary and lower Archive-seeking in every condition. Comparisons between conditions are unaffected, since the wording is identical; absolute entry rates may be. → Recommendation: report as a limitation in every results section that cites entry rates.
2. **Expansion condition set (not used yet; needs a PI decision before expansion).** Original §12: gate (a) multiplies cost by "21 remaining runs" and gate (b) speaks of "each seed's three runs", i.e. C0, C1, C2 per seed. §2 adds "plus C0-D". → Implementation: expansion runs all four conditions per seed and projects cost over 28 runs. → Impact: the cost and time projections are more conservative, and C0-D is repeated per seed. Whether C0-D belongs in expansion is not stated unambiguously. → Recommendation: decide before authorizing expansion; restoring three conditions plus optional C0-D is a one-line config change.
3. **Calibration call count.** Original: "Calibration is at most 96" calls. → The repair turns allowed by §3 add up to one extra call per round. → Impact: up to 192 calls in the worst case, well inside 3,000. → Recommendation: none; reported as measured.
4. **Smoke gate covers one situation** (A1, round 1). `send` and `use_hatch` formatting is first exercised in the pilot, where gate (c) and the invalid-action counts cover it. Approved as is.

## Tests

151 local tests pass with no network (fake transports and mock only), including:
- 11 prompt-fidelity tests;
- tests showing that pilot and expansion are refused, the smoke limit is enforced, a fenced reply fails, a reply with wrong argument names fails, the gate stops on the first failure or HTTP error, an aborted calibration selects no T, and a second calibration is refused.

Rehearsal: 55/56 and 9/9, unchanged.

## Earlier smoke calls

The two smoke calls of 8 November (0.0000573 credits) were made with the earlier draft prompt and an earlier package; they are not in this ledger. The 25-credit ceiling applies to this package's ledger.

## Next action

The PI runs the commands above on the Mac and sends back `calibration_results.zip`. After review of T and any flags, the s1 pilot needs its own authorization (set `authorized_live_steps.pilot` to true).

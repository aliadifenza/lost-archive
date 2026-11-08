# Phase 3 handoff — s1 pilot ready, not authorized (8 November 2026)

Tag `v1.3-pilot-ready`. Calibration is complete and verified (`results/calibration_s0/VERIFICATION.md`). **T = 20 is frozen** (`runs/state.json`, PI-6 rule applied as written). s0 is preserved and never reused. The pilot is configured but `authorized_live_steps.pilot` is `false`; expansion is `false`.

## Frozen configuration

Adaption Responses API, `gemma-4-31b-it`, temperature 0, max output 300, `store: false`; strict parsing with one repair turn; system prompt SHA-256 `0d8f1f0e…0630`, repair `3c2fcc18…f848`; available-action signatures only; limits 25 credits and 3,000 calls (ledger cumulative: 101 calls and 0.006277 credits used so far).

## Pilot as configured (V1.2 §12 step 3, V1.3 properties)

- **Seed** s1. **Conditions:** C0 first (the matched baseline), then C0-D, C1, C2. **T = 20** from the calibration.
- **Probes:**
  - TCR (§10) for every agent with AC < 3, in any condition.
  - ECR (V1.3) for agents whose rooms inspected fall below their matched C0 agent's, so never in C0 itself.
  - Both: 4 rounds, restricted actions shown as signatures, run on isolated copies, separate logs.
- **Properties:** all seven D2 properties per condition (`<cond>_properties.json`), with C0 as the matched comparison and C0-D added for C2. Every property reports observed, comparison, emergence, suppression, probe, cannot conclude. Tag-based measures stay provisional.
- **Outputs** in `runs/pilot/s1/`:
  - `<cond>.jsonl` (the header now records model and temperature);
  - `<cond>_probes.jsonl`;
  - `<cond>_properties.json`;
  - `summary.json`, which includes `calls_total_incl_probes` for the call-ceiling decision.
- **Guards:**
  - one attempt only: a second pilot run is refused while logs exist, and a rerun needs a PI decision;
  - an API error or the budget limit aborts the run (`run_aborted`);
  - expansion stays refused.

## Pilot calls and cost

| | Calls | Credits | Basis |
| --- | --- | --- | --- |
| Expected | about 380–450 | about 0.04–0.06 | calibration rates (1 call per round, ~450 input / ~70 output tokens per call), larger prompts in C1/C2, few probes [MED] |
| Hard maximum | **1,016** | **≤ 0.47** | 2 × (3 × 6 × 20 + 20) agent-round calls with a repair every round, plus 32 probed agents × 4 rounds × 2; every prompt at the 4k-token design maximum [HIGH as a bound] |
| Spec reference | ~375 | — | V1.2 §12, computed for T = 16 |

After the pilot, the worst case is 101 + 1,016 = 1,117 calls, inside 3,000, and the cost stays far below 25 credits. Wall-clock time: expected about 25 minutes, at most about 55 (calibration ran at ~3 s per call) [MED].

## Discrepancies (Original → Change → Impact → Recommendation)

1. **Pilot size at T = 20.** Original: §12 estimates about 375 pilot calls, computed for T = 16. → The tuning rule set T = 20, so the main runs grow to 380 agent rounds before probes. → No budget risk (see table). → Recommendation: none; report the measured count.
2. **Expansion call ceiling (foreseeable).** At the pilot's expected size, 7 more seeds need about 7 × 450 ≈ 3,150 calls against about 1,900 remaining under the 3,000 ceiling, so the `a_calls` gate will probably refuse expansion. → Recommendation: decide after the pilot from `projection.calls`, as you planned. [MED]
3. **Expansion condition set** (still open from the previous handoff): 21 runs (three conditions) or 28 (with C0-D). Decide before authorizing expansion.
4. **Rumor wording:** framing limitation, documented; kept per PI decision.
5. **Calibration header gap:** model and temperature are null in the s0 header but recorded in the report and ledger; fixed for the pilot (see `VERIFICATION.md`).

## Tests

154 local tests pass, with no network. New tests cover:
- the full pilot after the gate and calibration, through a fake provider: four conditions, T = 20 in every header, model and temperature recorded, seven properties per condition, and TCR and ECR applied by rule;
- the pilot refused without authorization, and refused on a second attempt;
- s0 refused for any pilot or expansion seed;
- expansion refused;
- the call bound.

Rehearsal: 55/56 and 9/9, unchanged.

## Mac commands

```bash
cd ~/lost_archive_v13
unzip ~/Downloads/lost_archive_pilot_ready.zip -d pilot     # adjust the path to where the zip was saved
cd pilot/lost_archive
cp -R ../../lost_archive/runs .                              # carries T=20, ledger, calibration, smoke
cat runs/state.json                                          # expect "T": 20
python3 -m unittest discover -s tests                        # expect 154 tests, OK
python3 -m lostarchive.rehearsal                              # expect 55/56 and 9/9
read -s ADAPTION_API_KEY && export ADAPTION_API_KEY
python3 -m lostarchive.experiment check                       # expect "blockers": [], pilot false

# ONLY after the PI authorizes the pilot:
python3 -c "import json; p='config/experiment.json'; c=json.load(open(p)); c['authorized_live_steps']['pilot']=True; json.dump(c, open(p,'w'), indent=2)"
python3 -m lostarchive.experiment pilot 2>&1 | tee pilot_console.txt; echo "exit code: ${PIPESTATUS[0]}"
zip -r pilot_results.zip runs/pilot runs/ledger.json runs/state.json pilot_console.txt config/experiment.json
```

Exit codes: 0 pilot complete; 4 API or budget abort (no rerun without a PI decision); 3 blocked (e.g. no T, or logs already exist); 2 refused (not authorized, key missing, prompt hash mismatch). Type the commands as shown rather than pasting the shell prompt line; the calibration console capture contained only a pasted-prompt error.

## Next action

PI authorization of the s1 pilot. Then send back `pilot_results.zip` for verification and the exploratory pilot report (§12 step 4).

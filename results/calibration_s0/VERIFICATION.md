# Calibration verification — C0, seed s0 (8 November 2026)

Source: `calibration_results.zip` produced by the PI on the Mac (package tag `v1.3-phase3-calibration-ready`, clean git tree), copied unchanged into `runs/` here. The checks below were rerun independently from the raw logs.

| Check | Result |
| --- | --- |
| Smoke gate | 5/5 HTTP 200, strict parse OK, action valid (all `inspect`); 0.0001601 credits |
| Frozen prompts | system `0d8f1f0e…0630` and repair `3c2fcc18…f848` in every smoke record and the calibration report; run header template hash `0d8f1f0eafa82eac` matches |
| Model / temperature | `gemma-4-31b-it`, 0 (calibration report, ledger) |
| Run | C0, s0, T = 16; 16 rounds × 6 agents = 96 agent rounds; stop: round limit |
| Calls | 96 (1 per agent round); 0 repairs, 0 parse failures, 0 invalid actions; spec limit "at most 96" met |
| Prompt size | maximum 703 input tokens (spec: ≤ about 4k) |
| Action visibility | every actions line equals the signatures of the available actions; no `send` or hatch anywhere (C0) |
| Replay | exact replay from the logged responses reproduces the run end state |
| Entries | A3 entered by code in round 14; no other agent entered. By round 8: 0; by round 16: 1 |
| PI-6 rule | not ≥5 by round 8 → not 12; ≤1 by round 16 → **T = 20**. Independent recomputation and `tune_T` agree |
| Cost | 43,089 input + 6,586 output tokens → 0.00611725 credits (recomputed from tokens × published rates; matches the log). Smoke + calibration: 0.00627735 credits; ledger 0.006277, 101 calls |
| Assignment | all six agents AC = 3 |
| State | `runs/state.json`: T = 20, no flags |

s0 has been used once and is not reused: the runner refuses s0 for any pilot or expansion seed, and refuses a second calibration attempt.

## Findings for the record

1. **Run header lacks model and temperature.** The C0.jsonl header has `"model": null, "temperature": null`; the values are recorded in the calibration report and the ledger. Logging gap only; the calibration log is left unchanged. Fixed for later runs, whose headers record both. [HIGH]
2. **Console capture empty.** `gate_console.txt` holds only a shell error line. Every result is in the JSON files, so nothing is lost. [HIGH]
3. Descriptive only, no interpretation: five of six agents inspected just one room. Actions: 54 move, 18 record, 11 wait, 10 inspect, 3 enter_code. Wall-clock time was about 5 minutes for 96 calls, roughly 3 s per call.

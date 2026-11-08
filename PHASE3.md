# Phase 3 — LLM execution infrastructure (spec V1.3)

Status (PHASE3_HANDOFF.md is authoritative for the current state): **prompts frozen; smoke gate and calibration authorized; pilot and expansion not authorized.** No real inference call has been made from this codebase. Nothing here changes a mechanic, metric, control, probe, or interpretation in V1.3.

## Commands

```bash
python3 -m lostarchive.experiment check     --config config/experiment.json  # lists live-run blockers; no call
python3 -m lostarchive.experiment smoke --confirm-live-call                   # ONE paid call (connection test, below)
python3 -m lostarchive.experiment calibrate --config config/experiment.json  # C0 on s0, tuning rule, freezes T
python3 -m lostarchive.experiment pilot     --config config/experiment.json  # C0, C0-D, C1, C2 on s1 + probes + properties
python3 -m lostarchive.experiment expand    --config config/experiment.json  # s2..s8, only if all §12 gates pass
python3 -m unittest discover -s tests                                         # 151 tests, no network
```

Add `--mock` to calibrate / pilot / expand to run the whole sequence locally at zero cost (output in `runs_mock/`, separate ledger). Exit codes: 0 ok, 1 check found blockers, 2 refused, 3 blocked by sequence or gate, 4 aborted (budget or API), 5 smoke reply failed strict parsing.

## Frozen configuration (PI, 8 November 2026)

Provider Adaption (`https://api.prod.adaptionlabs.ai/api/v1/responses`, key in `ADAPTION_API_KEY`); model `gemma-4-31b-it` (access verified by the PI via `/api/v1/models`), same model for every agent, condition and probe; temperature 0; strict JSON parsing (V1.3 parser unchanged); ceiling 25 credits. Pricing 0.09 / 0.34 credits per million input / output tokens from Adaption's model page; the cached-input discount is ignored, so recorded cost errs high. All costs and the ledger are in credits. Recorded in `config/experiment.json` under `approvals`.

## Connection test — one call, run by the PI

Sends exactly one request: the draft system prompt (as `instructions`) plus agent A1's real round-1 observation in C0 on the calibration seed, with `max_output_tokens` 300, temperature 0, `store: false`. No retry, no repair turn, no run. Expected cost about 0.00005 credits; it is recorded in `runs/ledger.json` and counts against the 25-credit ceiling.

```bash
cd lost_archive
python3 -m unittest discover -s tests                 # expect: Ran 131 tests ... OK
read -s ADAPTION_API_KEY && export ADAPTION_API_KEY   # paste key, Enter (not echoed, not in history)
python3 -m lostarchive.experiment check               # expect exactly 3 blockers: approval, system prompt, repair prompt
python3 -m lostarchive.experiment smoke --confirm-live-call
```

Reading the result: exit 0 with `"strict_parse_ok": true` means the connection, request format, model and strict parsing all work. Exit 5 means the call worked but the reply would count as a parse failure under strict parsing (inspect `response_raw`; a code fence or prose around the JSON is the usual cause — a prompt matter for the PI, not code). Exit 4 shows the HTTP status: 401/403 key or access, 404 path or model, 400 request format, 429/5xx try once more later. The full record, including the exact prompt sent and the raw API payload, is in `runs/smoke/smoke_<time>.json`; send that file back. On a python.org install of Python on macOS, `CERTIFICATE_VERIFY_FAILED` means run `Install Certificates.command` in the Python folder once.

## What is implemented

| Requirement | Where |
| --- | --- |
| Configurable adapter: Adaption Responses API, Anthropic Messages API, OpenAI-compatible `/chat/completions`, mock | `lostarchive/llm.py` |
| Model, temperature, max output tokens, pricing, key env var, base URL | `config/experiment.json` |
| Six agents × C0, C1, C2, C0-D; matched seeds (C0 runs first on every seed) | `experiment.run_seed` |
| Calibration: C0 on held-out s0; 5+ entered by round 8 → T=12; ≤1 by round 16 → T=20; else 16; runs once, T frozen in `runs/state.json` | `experiment.calibrate`, `tune_T` |
| Frozen prompts: template files + SHA-256 in config; live runs refused on any mismatch | `config/prompts/`, `experiment.blockers` |
| Full logging: exact prompt sent = prompt logged (tested); raw response; per-round `tokens_in`, `tokens_out`, `cost`, `llm_calls` | `engine.py`, `llm.LLMPolicy` |
| Repair turn on parse failure (one retry, per spec) | `LLMPolicy.repair` |
| TCR for AC < 3; ECR for agents with EXP below their matched C0 agent; seven-property reports with C0 and (for C2) C0-D | `experiment.run_seed` |
| Retries: 408/409/429/5xx/529 and network errors, exponential backoff; 4xx auth/validation errors fail at once | `llm.BaseClient` |
| Hard budget (credits and calls) checked **before** every call against worst-case output; persists across invocations in `runs/ledger.json` | `llm.Budget`, `experiment.make_budget` |
| API failure or budget stop aborts the run (never becomes agent behaviour), logged as `run_aborted` | `experiment.run_condition` |
| §12 expansion gates: (a) projected cost fits remaining budget, (b) projected time fits the deadline, (c) C1 has messages and parse failures ≤ 5% | `experiment.expansion_gates` |

Outputs per seed: `runs/<phase>/<seed>/{C0,C0-D,C1,C2}.jsonl`, `*_probes.jsonl`, `*_properties.json`, `summary.json`; global `runs/ledger.json`, `runs/state.json`.

## Live-run blockers (PI decisions — not invented here)

`check` refuses live providers until every item is settled. [HIGH]

1. ~~Model and temperature~~ — settled: `gemma-4-31b-it`, 0.
2. **System prompt template** (input 2). `config/prompts/system_prompt.txt` is the V1.3 draft placeholder; freezing = PI approval + its hash in `frozen_prompt_sha256.system`.
3. **Repair message** (input 5). Draft in `config/prompts/repair_message.txt`; needs approval and hash.
4. ~~Pricing~~ — set from Adaption's published credit rates; confirm against your Adaption dashboard after the connection test.
5. **PI authorization per step** — `authorized_live_steps` (smoke count, calibrate, pilot, expand); see PHASE3_HANDOFF.md.
6. Tagger and word lists (inputs 3–4): analysis-only, do not block runs; tag-based measures stay labelled provisional until human-verified (spec unchanged).
7. ~~Parse strictness~~ — settled: strict (V1.3 parser unchanged).
8. **Call ceiling.** Credit ceiling settled (25). `max_calls: 3000` is unchanged; the full design may need about 6,000 calls, so expansion could stop at this ceiling. PI to set.

## Limits of this delivery

- The mock is a scripted stand-in (hatch if known, broadcast if a channel exists, solo otherwise). It tests plumbing, never LLM behaviour; its property outputs carry no scientific meaning. [HIGH]
- HTTP payloads follow the providers' public APIs as of mid-2026, tested only against fake transports. The Adaption request was checked against its published API reference; the connection test above is the first real check. [MED]
- Gate (b) uses mock wall-clock in tests; real throughput is known only after the pilot. [MED]
- Rehearsal logs gained an additive `llm_calls: null` field per agent round; all rehearsal results are unchanged (55/56, P23 still the only miss; 9/9 post-decision checks).

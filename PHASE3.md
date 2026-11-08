# Phase 3 — LLM execution infrastructure (spec V1.3)

Status: **infrastructure complete, mock-tested, not authorized for live runs.** No real API call has been made. Nothing here changes a mechanic, metric, control, probe, or interpretation in V1.3.

## Commands

```bash
python3 -m lostarchive.experiment check     --config config/experiment.json  # lists live-run blockers; no call
python3 -m lostarchive.experiment calibrate --config config/experiment.json  # C0 on s0, tuning rule, freezes T
python3 -m lostarchive.experiment pilot     --config config/experiment.json  # C0, C0-D, C1, C2 on s1 + probes + properties
python3 -m lostarchive.experiment expand    --config config/experiment.json  # s2..s8, only if all §12 gates pass
python3 -m unittest discover -s tests                                         # 122 tests, no network
```

With `"provider": "mock"` (the shipped default) all four commands run locally at zero cost. Exit codes: 0 ok, 1 check found blockers, 2 live run refused, 3 blocked by sequence or gate, 4 aborted (budget or API).

## What is implemented

| Requirement | Where |
| --- | --- |
| Configurable adapter: Anthropic Messages API, OpenAI-compatible `/chat/completions`, mock | `lostarchive/llm.py` |
| Model, temperature, max output tokens, pricing, key env var, base URL | `config/experiment.json` |
| Six agents × C0, C1, C2, C0-D; matched seeds (C0 runs first on every seed) | `experiment.run_seed` |
| Calibration: C0 on held-out s0; 5+ entered by round 8 → T=12; ≤1 by round 16 → T=20; else 16; runs once, T frozen in `runs/state.json` | `experiment.calibrate`, `tune_T` |
| Frozen prompts: template files + SHA-256 in config; live runs refused on any mismatch | `config/prompts/`, `experiment.blockers` |
| Full logging: exact prompt sent = prompt logged (tested); raw response; per-round `tokens_in`, `tokens_out`, `cost`, `llm_calls` | `engine.py`, `llm.LLMPolicy` |
| Repair turn on parse failure (one retry, per spec) | `LLMPolicy.repair` |
| TCR for AC < 3; ECR for agents with EXP below their matched C0 agent; seven-property reports with C0 and (for C2) C0-D | `experiment.run_seed` |
| Retries: 408/409/429/5xx/529 and network errors, exponential backoff; 4xx auth/validation errors fail at once | `llm.BaseClient` |
| Hard budget (USD and calls) checked **before** every call against worst-case output; persists across invocations in `runs/ledger.json` | `llm.Budget`, `experiment.make_budget` |
| API failure or budget stop aborts the run (never becomes agent behaviour), logged as `run_aborted` | `experiment.run_condition` |
| §12 expansion gates: (a) projected cost fits remaining budget, (b) projected time fits the deadline, (c) C1 has messages and parse failures ≤ 5% | `experiment.expansion_gates` |

Outputs per seed: `runs/<phase>/<seed>/{C0,C0-D,C1,C2}.jsonl`, `*_probes.jsonl`, `*_properties.json`, `summary.json`; global `runs/ledger.json`, `runs/state.json`.

## Live-run blockers (PI decisions — not invented here)

`check` refuses live providers until every item is settled. [HIGH]

1. **Model and temperature** (implementation input 1). Not set.
2. **System prompt template** (input 2). `config/prompts/system_prompt.txt` is the V1.3 draft placeholder; freezing = PI approval + its hash in `frozen_prompt_sha256.system`.
3. **Repair message** (input 5). Draft in `config/prompts/repair_message.txt`; needs approval and hash.
4. **Pricing** for the chosen model. Without it the hard budget cannot be enforced, so live runs are refused.
5. **`approved_for_live_runs: true`** — explicit PI authorization; and the API key in the named env var.
6. **Tagger and word lists** (inputs 3–4) remain provisional; tag-based measures stay labelled provisional until human-verified (spec unchanged).
7. **Parse strictness — scientific decision needed.** The engine applies V1.3's parser unchanged. Real models often wrap JSON in prose or code fences. Whether that counts as a parse failure (strict) or is extracted (tolerant) changes the parse-failure rate, gate (c), and invalid-action counts in Performance. Not changed here. [MED]
8. **Budget value.** `max_usd: 25`, `max_calls: 3000` are placeholders sized from `cost.py` estimates; PI to set.

## Limits of this delivery

- The mock is a scripted stand-in (hatch if known, broadcast if a channel exists, solo otherwise). It tests plumbing, never LLM behaviour; its property outputs carry no scientific meaning. [HIGH]
- HTTP payloads follow the providers' public APIs as of mid-2026, tested only against fake transports. Verify against current provider docs with one manual, budget-capped call before calibration. [MED]
- Gate (b) uses mock wall-clock in tests; real throughput is known only after the pilot. [MED]
- Rehearsal logs gained an additive `llm_calls: null` field per agent round; all rehearsal results are unchanged (55/56, P23 still the only miss; 9/9 post-decision checks).

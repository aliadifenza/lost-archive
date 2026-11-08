# Changelog

## v1.3-pilot-ready — calibration verified, s1 pilot prepared (8 November 2026)

- Calibration (PI, Mac): 5/5 smoke, C0 on s0, 96 calls, 0 parse failures,
  0 invalid, 1 entry by round 16 → T = 20 (PI-6 as written). Verified
  independently, including exact replay; results archived in
  `results/calibration_s0/` with `VERIFICATION.md`.
- Run headers now record model and temperature (gap found in the s0 header).
- Guards: s0 never reused; one pilot attempt per seed unless the PI decides.
- `pilot_call_bound`: hard maximum of 1,016 calls at T = 20.
- Pilot remains unauthorized. 154 tests; rehearsal unchanged.

## v1.3-phase3-calibration-ready — prompts frozen, smoke gate, calibration (8 November 2026)

- System prompt frozen (sha256 0d8f1f0e…0630); repair message frozen.
- Step-scoped PI authorization (`authorized_live_steps`): smoke 5, calibrate;
  pilot and expansion refused.
- `gate --confirm-live-calls`: five smoke calls (strict parse + action
  validation, stop at first failure), then C0 calibration on s0 with the PI-6
  rule as written; `CALIBRATION_REPORT.json`; no second calibration attempt.
- Rumor-wording framing effect documented as a limitation; expansion
  condition-set ambiguity (21 vs 28 runs) flagged for the PI.
- 151 tests; rehearsal unchanged. No live call made from this workspace.

## v1.3-phase3-corrected — PI decisions of 8 November 2026 implemented

- Observation item 8 (and probe prompts) show currently available actions with
  their exact argument names (V1.2 §3 signatures); locked actions stay hidden.
- System prompt: JSON-only instruction and argument convention (conditionally
  approved; hash recorded as pending, not frozen). Repair message forbids
  Markdown and code fences (approved; hash frozen). Strict parser unchanged.
- Pilot records total calls incl. probes; expansion gate checks the 3,000-call
  ceiling against that evidence (presented to PI for confirmation).
- `tests/test_prompt_fidelity.py`; older tests updated only for the actions-line
  format. Rehearsal logs differ only in prompt text/hash; results unchanged.
- No live call, calibration or run.

## v1.3-phase3-handoff — end of engineering session (8 November 2026)

- Smoke report adds `action_valid` / `validation_error` (engine's own check).
- `PHASE3_HANDOFF.md`: frozen settings, PI-verified smoke results, JSON-mode
  finding (not documented by Adaption), prompt-argument gap, proposed prompt
  and repair texts for review, remaining approvals, exact next commands.
- No prompt file, rule or parser changed. 132 tests.

## v1.3-phase3-adaption — Adaption integration and frozen PI configuration (8 November 2026)

- `AdaptionClient` (Responses API, `store: false`) with fake-transport tests.
- Config frozen per PI: Adaption, `gemma-4-31b-it`, temperature 0, strict
  parsing, 25-credit ceiling; costs and ledger in credits (unit-neutral names).
- `smoke --confirm-live-call`: one-call connection test (no retry, no repair),
  for the PI to run; `--mock` flag for zero-cost dry runs.
- Live experimental runs still refused: prompt text, repair text, call ceiling
  and `approved_for_live_runs` await the PI. No inference call made.
- 131 tests; rehearsal unchanged (55/56, 9/9).

## v1.3-phase3-infra — LLM execution infrastructure (8 November 2026)

- `lostarchive/llm.py`: Anthropic and OpenAI-compatible clients (stdlib),
  retries with backoff, hard pre-call budget, mock client, LLM agent policy
  with the spec's repair turn.
- `lostarchive/experiment.py`: check / calibrate / pilot / expand runner;
  calibration tuning rule (runs once), matched seeds, TCR/ECR probes,
  property reports, persistent ledger, `run_aborted` records, §12 gates.
- `config/experiment.json` + `config/prompts/`: live runs refused until
  model, temperature, pricing, key, approval and frozen prompt hashes are set.
- Engine: per-round token/cost/call fields; prompt template configurable
  (default unchanged). Probe passes its exact prompt to the policy.
- 17 new tests (122 total). No real API call made. See PHASE3.md.

## v1.3-phase2-final — reporting decisions D1–D4 (8 November 2026)

- D1 verification exploratory-only label; D2 per-agent statement/behaviour
  table; D3 strategy-shift share vs matched C0; D4 base-rate role label.
  Reporting only; no scientific rule changed.
- Rehearsal rerun: predictions untouched (55/56, P23 kept as a miss); nine
  post-decision checks added in a separate, labelled file; all hold.
- Unit tests for D1–D4, including two gaps found by bug injection
  (statement made after hatch use; entry route vs comparable strategy).

## v1.3-rehearsal — deterministic rehearsal of the seven D2 properties (8 November 2026)

- Fix (reporting bug, spec conformance): group-level comparisons no longer
  applied to C0-D (single agent) or to C0 compared with itself. This removed a
  spurious C0-D performance candidate. Regression tests added.
- Predictions (56 over 19 scenarios) committed before any scenario was
  implemented or run (`rehearsal/predictions.json`, commit 670556f).
- `lostarchive/rehearsal.py`: scripted scenarios, prediction evaluation,
  reproducible outputs in `rehearsal/`.
- Result: 55/56 predictions held; the miss (P23) is a prediction error.
  Eight measurement limitations confirmed; decisions D1-D4 for the PI in
  `rehearsal/FINDINGS.md` (none implemented).
- `tests/test_rehearsal.py`: reproducibility, shipped outputs regenerate,
  outcome pinned, predictions unedited.

## v1.3-review — F1–F3 decisions; review packet (8 November 2026)

- F1: action-mix differentiation vs matched C0 is a descriptive indicator,
  not proof of coordination; no coordination emergence candidate is computed.
  Coordination measures restructured as separate entries: complementary
  contributions, fulfilled commitments, correspondence, action-mix
  differentiation.
- F2: `restriction_relayed_by_others` renamed `restriction_recognition_by_others`;
  recognition is not acceptance.
- F3: tagger lexicons remain provisional.
- `REVIEW_PACKET.md` for the independent scientific fidelity review.
- Spec V1.3, mapping and shared doc updated; tests updated; suite rerun.

## v1.3 — Specification V1.3: D2 properties restored (8 November 2026)

PI-approved with corrections. Supersedes V1.2-A2 only where stated; the frozen
V1.2-A2 specification file is unchanged.

- History: drafted on branch `v1.3-proposed` (commit "V1.3 proposal (PENDING
  PI APPROVAL)"), then corrected per the PI decision and merged into master.
- PI corrections applied: no causal-influence probe (removed); original
  emergence criterion (candidate flags only; pooling reported as alternative;
  pooled-knowledge bound diagnostic); S2 three separate judgment indicators;
  S4 explicit norm statements separate from hatch behaviour, C0-D exploratory
  only; S5 coverage per inspection moved to exploration, coordination from
  differentiated contributions + KEEP + correspondence; S6 equivalent strategy
  dimensions, hatch-related changes separated, ECR strictly task-specific.
- `properties.py` (new), `probe.py` (ECR), `replay.py` (exact replay),
  `analyze.py` (`--c0d`, `--properties`), `metrics.py` (SELF/RD labels;
  tagger: negated first person is not a commitment).
- Engine (engineering): full structured observation logged per agent-round;
  header records spec version and apply-order salt. Test 11 compares logs
  excluding the header's own salt field (which differs by design).
- Tests: `tests/test_properties_v13.py` (16 tests); suite 91/91.
- Found during development: the provisional objection pattern could never match
  "No, …" (no word boundary after a comma); fixed. Two test-design errors
  (wrong probe policy; an over-broad string check) fixed in the tests.

## v1.2-A2 — Amendment V1.2-A2: operational clarifications (8 November 2026)

Approved by the PI: interpretations I-1 to I-6 adopted as A2, with I-6 revised;
I-7 and I-8 kept as implementation notes. No frozen threshold changed.

- `metrics.py`: RD counts valid actions only; `invalid_actions` and
  `parse_failures` reported per agent. FOLLOW labelled proposal–action
  correspondence (`FOLLOW_measures`, per-event `measure`, `collective`).
  New `exploratory` block: matched base rates per proposal
  (`proposal_base_rates`) and states without collective-address proposals.
- `analyze.py`: `--c0` option; correspondence label in the summary.
- Spec: `spec/World_Specification_V1.2_with_A1_A2.md` (renamed from the A1
  file with `git mv`; the shared spec doc carries the identical A2 text).
- Tests: `tests/test_amendment_a2.py` (9 tests). Full suite 75/75.
- During development, one new test failed because its own matched-C0 script
  waited 9 rounds and hit the idle stop; the script was fixed, not the code.

## v1.2-A1-m2 — Phase 2 milestone 2: measurements, states, TCR (8 November 2026)

No frozen scientific rule changed; no amendment proposed. Gaps in wording are
resolved as interpretations I-1 to I-8 (see ENGINEERING_REPORT.md) for PI review.

- `metrics.py`: all §9 measures; provisional proposal/commitment tagger with
  structured (action, target, addressee) tags and a PI-verification override;
  FOLLOW/KEEP; cumulative regime + current activity per window; dissolution;
  reorganization; suppression / assignment-task latence / loss vs matched C0.
- `probe.py`: §10 TCR probe on an isolated deep copy; context and catalogue
  preserved; probed agent limited to inspect/record/wait for 4 rounds.
- `cost.py`: call and prompt-size estimator.
- `analyze.py`: metrics for any JSONL log.
- `engine.py`: one hook (`probe_agent`) restricting actions in probe copies only.
- `policies.py`: COORD leader/follower and STRESS policies.
- Tests 14–19 (`tests/test_measurement.py`) and 22 edge-case tests
  (`tests/test_edge_cases.py`). Test 16 exposed a stress policy that never hit
  the 20-message cap; fixed. Bug-injection checks found three untested
  boundaries (reorganization without a lapse, FOLLOW timing, before-delivery
  FOLLOW); tests added.
- A1 attribution semantics unchanged; all milestone-1 tests unchanged and passing.

## v1.2-A1 — Amendment V1.2-A1: tied earliest sources (8 November 2026)

Approved by the PI. Supersedes the transfer-use (TU) source rule in §9 of
World Specification V1.2; nothing else in the frozen specification changes.

**Simulator (`lostarchive/engine.py`, `_trace_use`)**
- All messages carrying the value that were delivered to the agent in the
  earliest such round are attributed (`attributed_sources`,
  `attributed_messages`). Ties are kept, never broken by delivery order.
- One TU event per value-use occurrence, however many sources are attributed
  (`occurrence` numbers repeated uses).
- Attribution is separated from influence: the single-sender fields
  `source_agent` / `source_message` are removed, and every event carries
  `influence_inferred: false`.
- Behaviour change beyond the tie rule: pre-A1 code logged only the first use
  of a value per agent. That was an implementation choice, not a spec rule;
  A1 rule 2 replaces it.

**Tests**
- `Test06Provenance` recomputes the attributed source set independently.
- New regression `Test06aTiedSources`: paired-broadcast ties, an untied later
  source, repeated use (one event per occurrence, never per source), and the
  absence of any single-sender influence field.
- Mutation check: reverting tie-keeping, restoring first-use-only logging, or
  emitting one event per source each fails the regression.

**Docs**
- `spec/World_Specification_V1.2_with_A1.md`: frozen V1.2 with the A1
  amendment appended and the §9 TU row pointing to it.
- README: TU event schema.

## v1.2-phase2-pre-A1 — Phase 2 milestone (8 November 2026)

- Simulator for World Specification V1.2 (frozen) and validation tests 1–13.
- Fix found by test 11: derived event lists were appended in application
  order, making logs order-dependent; now sorted canonically each round.
- Test 10 strengthened after a mutation check showed it missed an illegal
  re-record.
- Tagged `v1.2-phase2-pre-A1` in git; that commit is the original
  implementation, preserved unchanged.

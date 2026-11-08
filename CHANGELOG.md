# Changelog

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

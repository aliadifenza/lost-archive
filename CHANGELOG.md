# Changelog

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

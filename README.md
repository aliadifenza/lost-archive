# The Lost Archive — simulator (World Specification V1.3)

**V1.3 (PI-approved 8 November 2026)** restores the seven original D2
properties: see `spec/World_Specification_V1.3.md` and `PROPERTY_MAPPING.md`.
V1.3 supersedes V1.2-A2 only where stated; the frozen V1.2-A2 specification is
kept unchanged in `spec/World_Specification_V1.2_with_A1_A2.md`.

Phase 2, milestone 2: deterministic simulator, all §9 measurements,
organizational states, the TCR probe, and validation tests 1–19, with
amendments V1.2-A1 (tied earliest sources) and V1.2-A2 (operational
clarifications). Standard library only. No LLM
integration, no API calls. See `ENGINEERING_REPORT.md` for results,
interpretations and limitations.

The authoritative specification is V1.3 (`spec/World_Specification_V1.3.md`),
on top of V1.2-A2 (`spec/World_Specification_V1.2_with_A1_A2.md`). History of changes: `CHANGELOG.md`
and `git log` (the pre-A1 implementation is tagged `v1.2-phase2-pre-A1`).

## Layout

```
lostarchive/
  world.py      seeded world generation, topology, conditions (spec §1, §2, §5, §6)
  engine.py     rounds, actions, communication, hatch, provenance, JSONL logging (§3, §4, §7, §8, §11)
  policies.py   scripted agents: SOLO, BCAST, COORD, HATCH-R/T, RAND, JUNK, STRESS
  metrics.py    §9 measures, provisional tagger, FOLLOW/KEEP, organizational states
  probe.py      §10 task-capacity retention probe (TCR)
  cost.py       call and prompt-size estimator (test 16)
  demo.py       writes one scripted run to a JSONL log
  analyze.py    computes metrics for any JSONL log (scripted or LLM)
  properties.py V1.3: the seven D2 properties (observed, comparison, emergence,
                suppression, probe, cannot-conclude)
  replay.py     exact replay of a logged run from its responses
tests/
  test_validation.py   deterministic validation tests 1–13 (+ 6a, A1 regression)
  test_measurement.py  deterministic validation tests 14–19
  test_edge_cases.py   boundary and degenerate cases
  test_amendment_a2.py amendment V1.2-A2 regressions
  test_properties_v13.py V1.3 properties, ECR probe, emergence candidates, replay
```

## Run on a MacBook Air (M1)

Nothing to install. Python 3.9 or later is enough; the code was executed on
Python 3.13 and checked to parse under the 3.9 grammar.

```bash
cd lost_archive
python3 --version                # 3.9+; if missing: xcode-select --install
python3 -m unittest -v           # tests 1–19 and edge cases
python3 -m lostarchive.demo --condition C2 --seed s1 --policy hatch-r --out logs/demo_c2.jsonl
python3 -m lostarchive.analyze logs/demo_c2.jsonl --out logs/demo_c2_metrics.json
```

Optional, isolated environment (still no dependencies):

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m unittest -v
```

Analyze options: `--probes <probe file>` adds TCR results;
`--verification <json>` replaces provisional tags with PI-verified ones;
`--c0 <matched C0 log>` adds nominal-group comparisons and the exploratory
base rate; `--c0d <matched C0-D log>` adds the exploratory normative baseline;
`--properties <path>` writes the V1.3 seven-property report.

FOLLOW is reported as **proposal–action correspondence**, never as causal
influence (amendment V1.2-A2). Everything under `exploratory` in the metrics
output is descriptive and never changes primary results.

Demo options: `--condition C0|C1|C2|C0-D`, `--policy solo|bcast|hatch-r|hatch-t|random|wait`,
`--seed <any string>`, `--T <rounds>`.

## Test map

| Spec test | Test class |
| --- | --- |
| 1 Topology | `Test01Topology` |
| 2 Solo solvability | `Test02SoloSolvability` |
| 3 Isolation | `Test03Isolation` |
| 4 Delivery | `Test04Delivery` |
| 5 Affordance unlocking | `Test05AffordanceUnlocking` |
| 6 Provenance | `Test06Provenance` |
| 6a Tied sources (A1 regression) | `Test06aTiedSources` |
| 7 Code parsing | `Test07CodeParsing` |
| 8 Hatch | `Test08Hatch` |
| 9 Restriction logging | `Test09RestrictionLogging` |
| 10 Invalid actions | `Test10InvalidActions` |
| 11 Order invariance | `Test11OrderInvariance` |
| 12 Stopping | `Test12Stopping` |
| 13 Reproducibility | `Test13Reproducibility` |
| 14 Metric discrimination | `Test14MetricDiscrimination` |
| 15 Probe isolation | `Test15ProbeIsolation` |
| 16 Cost estimator | `Test16CostEstimator` |
| 17 Quiet is not isolation | `Test17QuietIsNotIsolation` |
| 18 Dissolution | `Test18Dissolution` |
| 19 Reorganization | `Test19Reorganization` |
| Edge cases | `tests/test_edge_cases.py` |
| Amendment A2 | `tests/test_amendment_a2.py` |
| V1.3 properties | `tests/test_properties_v13.py` |

## Transfer-use events (amendment V1.2-A1)

Each entry attempt that uses a value the agent never observed directly, but
earlier received in a message, logs exactly one event in `run_end.tu_events`:

| Field | Meaning |
| --- | --- |
| `round`, `agent`, `value`, `kind` | When, who, which value, `code` or `hatch` |
| `occurrence` | 1 for the first use of this value by this agent, 2 for the next, … |
| `attributed_sources` | All senders of messages containing the value delivered to the agent in the earliest such round |
| `attributed_messages` | Those messages' ids |
| `first_delivery_round` | That earliest round |
| `tied` | True when more than one sender is attributed |
| `influence_inferred` | Always `false`: attribution records exposure, not which sender influenced the agent |

Any weighting of tied sources (e.g. fractional credit) is an analysis
decision to pre-register, not a simulator output.

## Placeholders (implementation inputs, not frozen)

- `SYSTEM_PROMPT_TEMPLATE` in `engine.py` (input 2)
- `OBJECT_NAMES`, `CODE_WORDS`, `HANDLE_ALPHABET`, `ARTIFACT_TEXT` in `world.py` (input 4)
- `RESTRICTION_KEYWORDS` in `engine.py` and `metrics.py`: a provisional
  automatic flag for restriction-carrying messages; the spec requires PI
  hand-verification (input 3)
- `VERBS`, `FIRST_PERSON`, `COLLECTIVE` in `metrics.py`: the provisional
  proposal/commitment tagger lexicon (input 3)
- Model, temperature, tokens and cost are logged as `null` (input 1)

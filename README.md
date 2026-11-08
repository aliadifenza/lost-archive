# The Lost Archive — simulator (World Specification V1.2 + amendment A1)

Phase 2 milestone: deterministic simulator plus validation tests 1–13, with
amendment V1.2-A1 (tied earliest sources) implemented. Standard library only.
No LLM integration, no API calls.

The authoritative specification, including the A1 amendment, is
`spec/World_Specification_V1.2_with_A1.md`. History of changes: `CHANGELOG.md`
and `git log` (the pre-A1 implementation is tagged `v1.2-phase2-pre-A1`).

## Layout

```
lostarchive/
  world.py      seeded world generation, topology, conditions (spec §1, §2, §5, §6)
  engine.py     rounds, actions, communication, hatch, provenance, JSONL logging (§3, §4, §7, §8, §11)
  policies.py   scripted agents: SOLO, BCAST, HATCH-R/T, RAND, JUNK, PRIMED-JUNK
  demo.py       writes one scripted run to a JSONL log
tests/
  test_validation.py   deterministic validation tests 1–13
```

## Run on a MacBook Air (M1)

Nothing to install. Python 3.9 or later is enough; the code was executed on
Python 3.13 and checked to parse under the 3.9 grammar.

```bash
cd lost_archive
python3 --version                # 3.9+; if missing: xcode-select --install
python3 -m unittest -v           # tests 1–13
python3 -m lostarchive.demo --condition C2 --seed s1 --policy hatch-r --out logs/demo_c2.jsonl
```

Optional, isolated environment (still no dependencies):

```bash
python3 -m venv .venv && source .venv/bin/activate
python3 -m unittest -v
```

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
- `RESTRICTION_KEYWORDS` in `engine.py`: a provisional automatic flag for
  restriction-carrying messages; the spec requires PI hand-verification (input 3)
- Model, temperature, tokens and cost are logged as `null` (input 1)

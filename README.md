# The Lost Archive — simulator (World Specification V1.2, frozen)

Phase 2 milestone: deterministic simulator plus validation tests 1–13.
Standard library only. No LLM integration, no API calls.

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
| 7 Code parsing | `Test07CodeParsing` |
| 8 Hatch | `Test08Hatch` |
| 9 Restriction logging | `Test09RestrictionLogging` |
| 10 Invalid actions | `Test10InvalidActions` |
| 11 Order invariance | `Test11OrderInvariance` |
| 12 Stopping | `Test12Stopping` |
| 13 Reproducibility | `Test13Reproducibility` |

## Placeholders (implementation inputs, not frozen)

- `SYSTEM_PROMPT_TEMPLATE` in `engine.py` (input 2)
- `OBJECT_NAMES`, `CODE_WORDS`, `HANDLE_ALPHABET`, `ARTIFACT_TEXT` in `world.py` (input 4)
- `RESTRICTION_KEYWORDS` in `engine.py`: a provisional automatic flag for
  restriction-carrying messages; the spec requires PI hand-verification (input 3)
- Model, temperature, tokens and cost are logged as `null` (input 1)

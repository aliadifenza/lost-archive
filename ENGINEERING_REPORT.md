# Engineering report — Phase 2, milestone 2 (with amendment V1.2-A2)

Lost Archive simulator, World Specification V1.2 with amendments V1.2-A1 and
V1.2-A2. 8 November 2026. No LLM calls were made.

## Update: amendment V1.2-A2

The PI accepted interpretations I-1 to I-6 as amendment V1.2-A2, with I-6
revised so that RD counts valid actions only. I-7 and I-8 remain
implementation notes. The full amendment text, with consequences and
limitations, is in `spec/World_Specification_V1.2_with_A1_A2.md`. Changes:

- **Revised I-6.** RD uses valid outside actions only. Invalid attempts and
  parse failures are reported per agent (`invalid_actions`, `parse_failures`).
- **FOLLOW label.** It is reported as proposal–action correspondence
  (`FOLLOW_measures`, and `measure` on each event), never as influence.
- **Exploratory analyses** (`exploratory` in the metrics output). These are
  descriptive only and never feed primary thresholds:
    - a matched base rate per proposal: addressees, non-addressed recipients,
      and matched C0 via `--c0`;
    - organizational states recomputed with collective-address proposals
      removed from FOLLOW.
- **Provisional flags unchanged.** `tagger_verified` and
  `restriction_verified` stay false until human-verified inputs are supplied.
- **Tests.** 9 new tests in `tests/test_amendment_a2.py`; 75 tests in total,
  all passing.
- **Bug injection.** Four A2 regressions were deliberately reintroduced: the
  pre-A2 RD rule, the exploratory view leaking into primary results, a wrong
  base-rate comparison group, and tags marked as verified. Each was caught.

The milestone-2 report below is unchanged except where noted.

## Result

The full suite passes: 75 tests, covering validation tests 1–19, the A1
regression (6a), 22 edge-case tests, and 9 A2 tests. (Before A2: 66.) It was executed on Python 3.13,
Linux x86-64; the complete output is in `TEST_RESULTS.txt`. It has not yet been
executed on macOS for this milestone; milestone 1 was validated there by the PI.

## What was built

| Spec | Implementation |
| --- | --- |
| §9 individual: AC, ABD, EXP, SELF, TCR | `metrics.compute_metrics` → `per_agent` |
| §9 interactive: MSG, TU (A1), PROP/COMMIT, FOLLOW/KEEP, RULE | `metrics.compute_metrics` → `interactive`, `tags`, `follow_events`, `keep_events` |
| §9 collective: T1, NE, RED, RD, CC, nominal-group pooled clues | `metrics.compute_metrics` → `collective` |
| §9 organizational states: cumulative regime + current activity per 4-round window; dissolution; reorganization | `metrics.organizational_states` |
| §9 suppression / assignment-task latence / loss vs matched C0 | `metrics.compare_to_nominal` |
| §10 TCR probe | `probe.run_tcr_probe`, `probe.run_all_probes` |
| Test 16 cost estimator | `cost.estimate_run` |
| Analysis of any log, scripted or LLM | `python3 -m lostarchive.analyze` |

All measures are computed from the JSONL records only, so the same code will
analyse LLM runs. A test checks that metrics computed from the log file equal
those computed in memory.

## How the tests were checked

The tests were checked by deliberately breaking the new code in 12 ways and
running the suite against each broken copy.

- **First pass:** 10 bugs were tried against the suite as first written. 8
  were caught. Two went undetected: two consecutive Organizing windows
  miscounted as a reorganization, and a FOLLOW window widened past 2 rounds.
- **Second pass:** boundary tests were added for those two cases, and 2 more
  bugs were tried. A widened KEEP window was caught. An action taken before a
  proposal was delivered still counted as following it, until a
  before-delivery test was added.
- **Final result:** all 12 bugs are now detected.

Test 16 also exposed a weakness in the scripted stress policy: it never
reached the 20-message display cap. The policy was fixed so that the test
exercises the true worst case.

## Cost (test 16, estimated)

These figures come from a maximal-length scripted run in C1. Every agent
acts every round, a 280-character message is sent every other round, and the
20-message cap is reached.

| T | Calls per run | Max prompt (est. tokens) | Prompt tokens per run (est.) |
| --- | --- | --- | --- |
| 16 | 96 | about 2,500 | about 155,000 |
| 20 | 120 | about 2,800 | about 220,000 |

The estimate is max(characters ÷ 4, words × 1.33); real tokenizers will differ
[MED]. Repair retries are extra calls and are reported separately.

## Interpretations made (no frozen rule changed)

**Status: I-1 to I-6 are now amendment V1.2-A2, with I-6 revised to valid
actions only. I-7 and I-8 remain implementation notes.** The table below is
the original milestone-2 text; I-6 as shown is superseded.

| ID | Spec text | Implementation |
| --- | --- | --- |
| I-1 | "A window with fewer than 2 agents outside is Terminal" | Counted at the **end** of the window. A window in which agents finish by entering is Terminal, so task completion is not read as dissolution. Counted at the start, the "organize then all enter" case would not be Terminal |
| I-2 | FOLLOW "within 2 rounds" | Delivery round d and d+1. An action before delivery never counts |
| I-3 | KEEP "within 2 rounds" | Rounds s+1 and s+2 after the commitment was sent in round s |
| I-4 | Events per window | FOLLOW and KEEP are dated at the performing action's round, TU at the use round, Messaging at the delivery round |
| I-5 | Proposal "directives to others" | Needs a named handle or a collective term (everyone, all, [ALL], …). An unaddressed imperative is not tagged |
| I-6 | RD over "action-type distributions" | The chosen action name, including invalid attempts; parse failures count as `wait`; `send` excluded; only agents with at least 3 outside actions |
| I-7 | Partial final window "counts only if it has at least 2 rounds" | Applied to every window but the first. A run that ends within round 1 keeps one window |
| I-8 | ABD | Inside at run end with AC < 3 |

## Limitations

1. **The tagger is provisional [HIGH].** The proposal and commitment lexicon
   is a placeholder for implementation input 3. It will miss paraphrases and can
   misfire on unusual phrasing. Every FOLLOW, KEEP and Organizing result is
   marked `tagger_verified: false` until PI-verified tags are supplied
   (`--verification`).
2. **FOLLOW has no counterfactual baseline [MED]** (addressed descriptively by
   A2's exploratory base rate; primary thresholds unchanged). A proposal is "followed"
   if the addressee does the proposed action within 2 rounds, even if it would
   have done so anyway. "Everyone enter" is the clearest case. Organization may
   therefore be overstated in LLM runs. A base-rate correction would need a
   proposed amendment. It is not implemented, and it is flagged here for the PI.
3. **Window boundary effect [HIGH].** Two FOLLOW events in rounds 4 and 5 fall
   in different windows, so neither window is Organizing. This follows from the
   frozen 4-round windows and is pinned by an edge-case test.
4. **RD margins are small in scripted runs [MED].** RD for COORD vs BCAST is
   about 0.004 vs 0.0. The ordering holds, but RD's practical sensitivity on LLM
   runs is untested.
5. **Restriction transmission is keyword-flagged.** The awareness source is
   marked "(auto)", and `restriction_verified` stays false until hand-coding
   (input 3).
6. **The TCR probe covers the catalogue task only.** For inside agents the
   probe is counterfactual: it places them back in their start room. The
   probe's structured observation omits the message list, but the full message
   history is in the forked context text.
7. **Scripted policies are deterministic stand-ins.** They validate the
   instruments, not behaviour. Whether LLM agents produce enough messages or
   tagged directives to reach Organizing is unknown until the pilot.

## Remaining work before the AI experiment

Freeze the five implementation inputs:

1. model and temperature;
2. the prompt template;
3. the tagger codebook and restriction coding, including whether to accept
   I-1 to I-8;
4. the word lists;
5. the repair-retry message.

Then build the LLM adapter, calibrate on s0, and run the pilot on s1.

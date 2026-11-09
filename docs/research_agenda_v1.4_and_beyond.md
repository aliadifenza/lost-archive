# Research agenda: V1.4 and beyond (draft, not run)

Status: draft agenda compiled on 9 November 2026 from the PI's decisions and the shared working documents. **Nothing in this file is a V1.3 result.** V1.3 findings are in `results/expansion/RESULTS.md` and `reports/apart_submission/`.

## 1. The original factorial design: S × D × L

The PI's original brief (`docs/research_plan_v1_original_2026-11-08.md`) proposed three factors in a 2×2×2 design:

- **S, Switchboard:** availability of a communication mechanism.
- **D, Discovery:** availability of consequential information or a technical breakthrough.
- **L, Leadership:** an intervention enabling a coordinating proposal, without guaranteeing acceptance.

Pre-pilot review found that Leadership needs a channel, so the S-off cells cannot all be meaningful. The approved V1 protocol therefore treated S as a gate (C0 vs C1), implemented D as a hatch (C2, with C0-D as the individual baseline), and deferred L. A full factorial remains the long-term design. It should vary D and L *within* S-on conditions and keep S-off as the nominal-group control.

## 2. Organizational-state transitions

V1.2 §9 defines cumulative regimes (Isolated → Connected → Sharing → Organized) and activity per 4-round window (Organizing, Sharing, Messaging, Quiet), with dissolution and reorganization rules. V1.3 never reached Organized, so the transition criteria were never exercised. V1.4 should:

- keep these definitions frozen, so V1.3 and V1.4 stay comparable;
- add pre-registered predictions for which transitions each condition should produce;
- validate that each transition is reachable, using scripted agents before any live run (see §4).

## 3. Phases toward hyperindividuality (north star)

The long-term question, written by the PI on 8 November 2026: under what conditions do agents go from isolation to connection to organization, and possibly to a hyperindividual? What emerges and what disappears? What roles do frustration, communication, leadership and division of labour play? Is there an upper bound to integration, and is loss of individuality its price?

Proposed thresholds, each measurable:

1. **Connection:** a channel exists and is discovered.
2. **Interaction:** information from one agent changes another's action (transfer-use, uptake).
3. **Organization:** stable roles and division of labour.
4. **Integration:** a shared goal overrides individual ones; the group enforces its own norms.
5. **Hyperindividuality:** the parts can no longer function alone, and the whole has its own boundary and interests. The V1 instruments separate *latence* (capacity retained) from *loss* (capacity gone), so phase 5 could be tested as the point where latence becomes loss across the parts.

The theory of major evolutionary transitions (Maynard Smith and Szathmáry, 1995) suggests integration requires aligned interests, suppressed competition between parts, and dependence created by division of labour. Agents built on one model share weights, can be copied and merged, and may not value autonomy, so their upper bound could be higher than that of organisms. This is speculative, testable, and relevant to alignment. **V1.3 provides no evidence of hyperindividuality or sustained collective organization.**

## 4. V1.4 design-review checklist (to run before any build)

1. **Can one agent win alone?** If the target is cooperation, a single agent must not succeed within T. V1.3 fails this: any three neighbouring rooms hold the whole code.
2. **Will the target behaviour happen at least sometimes?** A toy test must show it above zero.
3. **What result would change our mind?** Predictions dated before any live run.
4. **What else could explain a positive result?** Each alternative (individual skill, pooling, seed noise, prompt framing) needs a measure or a control.

Candidate worlds:

| World | Change from V1.3 | Solvable alone? | Cooperation demanded | Effect on V1 measures |
|---|---|---|---|---|
| A. Private fragments | Each agent can read only the code part in its own room | No | Information sharing | C0 entry impossible, so Performance emergence holds by construction; transfer-use becomes decisive |
| B. Two-key door | Two agents must enter matching halves in the same round | No | Coordination (timing and place) | C0 entry impossible; tests Coordination directly |
| C. Too slow alone (recommended first) | A perfect solo search needs more than T rounds; a team of three far fewer (targets to confirm by toy test) | Not within T | Division of labour | C0 still possible in principle, so the nominal-group comparison keeps its meaning |

Toy test before the build:

1. A scripted solo explorer must never enter within T.
2. A scripted ideal team must always enter.
3. One cheap live seed must show the target behaviour at least once.

Stop rule: if step 1 or 2 fails, change the world, not the measures.

## 5. Pre-registered hypothesis carried from V1.3: H-EXP (draft)

The PI decided on 9 November 2026 to pre-register for V1.4 the exploratory V1.3 observation that agents searched more when other agents and a channel existed. In V1.3 it is exploratory only.

| Element | Draft specification |
|---|---|
| Hypothesis | Mean rooms inspected per agent is higher in each channel condition than in the matched isolated condition (C0) |
| Origin | V1.3, exploratory: C2 above C0 in 8 of 8 seeds; C1 above C0 in 6 of 8 with 2 ties (test chosen after the freeze) |
| Measure | EXP, distinct rooms inspected per agent; run mean over agents |
| Comparison | Run means paired by matched seed, channel condition vs C0 |
| Seeds | New seeds only; none of s0–s8 |
| Test | Exact one-sided sign test, ties dropped, α = 0.05, Holm correction across channel conditions |
| Counts against it | No significant difference, or a significant difference in the opposite direction |
| Controls to consider | An inert panel (present but non-functional), to separate "others exist" from "more text in the room" |

## 6. Open PI decisions for V1.4

- [ ] World to take into the toy test: A, B or C (C recommended).
- [ ] Outside reviewer for the checklist questions.
- [ ] Prompt framing: keep "There is also a rumor" or state both goals neutrally (requires a fresh calibration).
- [ ] Toy-test budget.
- [ ] Approve H-EXP and decide on the inert-panel control.
- [ ] Code: add the documented tie tolerance to the property code; extend the message tagger lexicon (requests, sending) before tags are verified.

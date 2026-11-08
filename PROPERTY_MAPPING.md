# Property-to-measurement mapping (specification V1.3)

Output keys refer to `compute_properties(...)["properties"][<property>]`. "Proxy" means a descriptive behavioural indicator, not a measurement of an internal state. Emergence flags are **candidates only**, never proof. Tag-based measures are provisional until human-verified.

| Property | Level | What is observed (output key) | Proxy? | Comparison | Emergence candidate | Suppression | Capacity probe | Cannot conclude |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Goal-directedness | Individual | AC, ABD, AC3_round (`observed.per_agent`) | Proxy for goal pursuit | Same agent, matched C0 | Not applicable | AC below matched C0 agent | TCR | Valuing of the goal; other capacities |
| Independent judgment | Individual | Verification events and requests; objections; non-adoption with alternative action (three separate indicators) | Proxy; tagged items provisional | Before vs from first Organizing window; C1 vs C2 | Not applicable vs C0 | Fewer events per indicator after organizing | None | Warrant (all clues true); intent; judgment from non-adoption alone |
| Influence | Interactive | Proposal–action correspondence (FOLLOW), by window; exploratory base rates | Correspondence only | Descriptive | Not defined vs C0 | Not applicable | None (causal design deferred by PI) | Causal influence; social vs informational |
| Normative behaviour | Interactive | Explicit statements (transmitted, recognized by others, accepted, rejected, stripped) **separate from** behaviour (aware or unaware use, aware non-use); recognition is not acceptance (F2) | Proxy; tagged items provisional | Descriptive in C2; C0-D exploratory individual baseline only | None computed | Constraint stripping | None | Endorsement; reasons for non-use |
| Coordination | Collective | Separate measures: complementary contributions (information contributors, values contributed); fulfilled commitments (KEEP); correspondence; organizing windows; action-mix differentiation (RD) | Proxy | RD vs matched C0, descriptive only (F1) | None computed (F1) | Not applicable | None | Shared intention; causation; coordination from RD alone (may reflect completion times) |
| Exploration diversity | Collective | Locations (coverage, entropy, efficiency); comparable strategies (priority, range); entry route and voice separate; hatch entrants separated | Behavioural profiles | Nominal C0 on equivalent dimensions | Comparable strategy entropy above nominal (alternatives: pooling, hatch) | Convergence; EXP below matched C0 agent | ECR (one exploration task) | Strategy as intention; broader capacity |
| Performance | Collective | Time (first, mean, all-entered); actions (to first entry, per entrant, invalid); assignment total; Pareto relation | Direct | Matched C0 nominal group | First entry earlier than earliest isolated agent (alternative: pooling; pooled-knowledge bound diagnostic) | Dominated by nominal | None | Reasoning efficiency; other tasks |

## Probes

| Probe | Task | Allowed actions | Rounds | Pass | Licenses |
| --- | --- | --- | --- | --- | --- |
| TCR | Complete the catalogue assignment when instructed | inspect, record, wait | 4 | AC reaches 3 | Assignment-task latence vs loss only |
| ECR | Inspect a room not yet inspected when instructed | move, inspect, wait | 4 | A new room is inspected (not applicable if all six inspected) | Retained capacity for that exploration task only |

## Reporting decisions D1–D4 (PI, 8 November 2026)

- **D1:** verification is exploratory only.
- **D2:** `normative_behavior.observed.statement_behaviour_by_agent` lists each agent's statements beside its subsequent hatch behaviour.
- **D3:** `exploration_diversity.observed.strategy.shift_vs_matched_C0` gives the share of agents whose comparable strategy differs from C0.
- **D4:** `influence.observed.base_rate_role` marks the matched-C0 base rate as diagnostic.

All four are descriptive.

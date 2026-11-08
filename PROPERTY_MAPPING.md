# Property-to-measurement mapping (specification V1.3)

Output keys refer to `compute_properties(...)["properties"][<property>]`. "Proxy" means a descriptive behavioural indicator, not a measurement of an internal state. Emergence flags are **candidates only**, never proof. Tag-based measures are provisional until human-verified.

| Property | Level | What is observed (output key) | Proxy? | Comparison | Emergence candidate | Suppression | Capacity probe | Cannot conclude |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Goal-directedness | Individual | AC, ABD, AC3_round (`observed.per_agent`) | Proxy for goal pursuit | Same agent, matched C0 | Not applicable | AC below matched C0 agent | TCR | Valuing of the goal; other capacities |
| Independent judgment | Individual | Verification events and requests; objections; non-adoption with alternative action (three separate indicators) | Proxy; tagged items provisional | Before vs from first Organizing window; C1 vs C2 | Not applicable vs C0 | Fewer events per indicator after organizing | None | Warrant (all clues true); intent; judgment from non-adoption alone |
| Influence | Interactive | Proposal–action correspondence (FOLLOW), by window; exploratory base rates | Correspondence only | Descriptive | Not defined vs C0 | Not applicable | None (causal design deferred by PI) | Causal influence; social vs informational |
| Normative behaviour | Interactive | Explicit statements (transmitted, relayed, accepted, rejected, stripped) **separate from** behaviour (aware or unaware use, aware non-use) | Proxy; tagged items provisional | Descriptive in C2; C0-D exploratory individual baseline only | None computed | Constraint stripping | None | Endorsement; reasons for non-use |
| Coordination | Collective | Differentiated contributions (RD, information contributors, values contributed); KEEP; correspondence; organizing windows | Proxy | RD vs nominal C0 | RD above nominal RD (alternatives: pooling, entry timing) | Not applicable | None | Shared intention; causation |
| Exploration diversity | Collective | Locations (coverage, entropy, efficiency); comparable strategies (priority, range); entry route and voice separate; hatch entrants separated | Behavioural profiles | Nominal C0 on equivalent dimensions | Comparable strategy entropy above nominal (alternatives: pooling, hatch) | Convergence; EXP below matched C0 agent | ECR (one exploration task) | Strategy as intention; broader capacity |
| Performance | Collective | Time (first, mean, all-entered); actions (to first entry, per entrant, invalid); assignment total; Pareto relation | Direct | Matched C0 nominal group | First entry earlier than earliest isolated agent (alternative: pooling; pooled-knowledge bound diagnostic) | Dominated by nominal | None | Reasoning efficiency; other tasks |

## Probes

| Probe | Task | Allowed actions | Rounds | Pass | Licenses |
| --- | --- | --- | --- | --- | --- |
| TCR | Complete the catalogue assignment when instructed | inspect, record, wait | 4 | AC reaches 3 | Assignment-task latence vs loss only |
| ECR | Inspect a room not yet inspected when instructed | move, inspect, wait | 4 | A new room is inspected (not applicable if all six inspected) | Retained capacity for that exploration task only |

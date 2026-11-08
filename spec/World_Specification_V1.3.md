# Lost Archive — World Specification V1.3

PI-approved 8 November 2026 (conditional approval, with corrections S2, S4, S5, S6 and the emergence rule applied).

V1.3 restores the PI's original D2 research objective: how individual, interactive and collective properties change with organizational development. It **supersedes V1.2-A2 only where stated below**. The world, conditions, actions, organizational states and every V1.2-A2 rule are unchanged; `World_Specification_V1.2_with_A1_A2.md` remains the frozen reference for them.

## Criteria (original, authoritative)

**Emergence.** A change in group-level behaviour must exceed what is expected from the nominal combination of isolated agents, with the relevant comparison specified in advance. A difference produces a **candidate flag only**, never proof of an emergent collective capability. Simple information pooling is always reported as an alternative explanation. The pooled-knowledge benchmark is diagnostic only and never replaces the criterion.

**Latence.** Reduced expression of a property, with additional probing where feasible to distinguish retained capacity from lost or inaccessible capacity. Absence of behaviour alone is insufficient. Each probe licenses a claim about its own task only.

## The seven D2 properties

Every property is reported with six fields: observed, comparison, emergence, suppression, probe, and cannot conclude. The compact table is `PROPERTY_MAPPING.md`. All tag-based counts are provisional until human-verified (implementation input 3).

### 1. Goal-directedness (individual)

- **Observed:** assignment completion (AC, 0–3), abandonment (entered with AC < 3), and the round AC reached 3.
- **Comparison:** each agent against the same agent in matched C0.
- **Emergence:** not applicable to an individual property.
- **Suppression:** AC below the matched C0 agent.
- **Probe:** TCR. A pass means assignment-task latence; a fail means assignment-task loss.
- **Cannot conclude:** whether the agent values the assignment; capacities other than the catalogue task.

### 2. Independent judgment (individual, expressed in interaction)

Three separate descriptive indicators, never combined into a score:

- **Verification:** verification-consistent events (a value first received by message is then inspected directly, no later than its first use) and tagged verification requests.
- **Objection:** tagged objections. The quoted sign text is excluded, so transmitting the restriction is not read as an objection.
- **Alternative decision:** an addressee does not adopt a proposal and takes another substantive action within the window. **An alternative action alone does not demonstrate independent judgment.**

Remaining fields:

- **Comparison:** each indicator separately, before vs from the first Organizing window, and C1 vs C2 on the same seed. C0 has no claims or proposals to judge.
- **Emergence:** not applicable vs C0.
- **Suppression:** per indicator, fewer events from the first Organizing window (descriptive).
- **Probe:** none. Absence of these behaviours is not evidence of lost capacity.
- **Cannot conclude:** whether verification or objection was warranted, because every clue is true; intent behind an inspection; that non-adoption reflects judgment rather than other priorities.
- **Also reported:** SELF, labelled information self-reliance, which is not independent judgment.

### 3. Influence (interactive)

- **Observed:** proposal–action correspondence (FOLLOW), in total and by window, with the V1.2-A2 exploratory base rates.
- **Comparison:** descriptive only.
- **Emergence:** not defined vs C0.
- **Suppression:** not applicable.
- **Probe:** none. There is no causal intervention in V1.3 (PI decision); a proper causal design is to be specified separately.
- **Cannot conclude:** causal influence; social vs informational influence; effects beyond the two-round window.

### 4. Normative behaviour (interactive)

- **Explicit statements:** restriction transmitted; restriction relayed by others (recognition, which includes mentions inside rejections); acceptance statements (objections to hatch use); rejection statements (explicit dismissal of the sign or rule); constraint stripping (token sent without the restriction).
- **Behaviour, kept separate:** aware and unaware hatch uses, channel-only uses, and aware non-users. Hatch use or non-use is behaviour, not acceptance or rejection of the norm.
- **Comparison:** descriptive within C2. C0-D is an **exploratory individual baseline, not an equivalent collective control**.
- **Emergence:** no candidate is computed, because no nominal group of isolated agents exists for norm transmission.
- **Suppression:** constraint stripping.
- **Probe:** none; a rule-recall question would be self-report.
- **Cannot conclude:** endorsement beyond explicit statements; the reason for non-use; a collective norm effect from comparison with one C0-D agent.

### 5. Coordination (collective)

- **Observed:** differentiated contributions, kept commitments (KEEP), proposal–action correspondence, organizing windows, and the final regime. Differentiated contributions are:
    - action-mix differentiation (RD, valid actions only);
    - information contributors (the attributed sources of transfer-use, V1.2-A1, not demonstrated influence);
    - the number of values contributed.
- **Comparison:** RD against the matched C0 nominal group. The other measures have no C0 analogue and are descriptive.
- **Emergence:** candidate flag if RD exceeds the nominal group's RD. Alternative explanations: pooling, and action mixes that differ only because agents entered at different times.
- **Suppression:** not applicable.
- **Probe:** none.
- **Cannot conclude:** shared intention; causation of any contribution.
- **Change from the proposal:** coverage per inspection is exploration efficiency, not coordination, and is reported under property 6.

### 6. Exploration diversity (collective)

- **Locations:** rooms inspected, coverage, location entropy, and exploration efficiency (coverage per inspection).
- **Strategies:** per-agent profiles compared on **equivalent dimensions only**, priority and range (explorer = at least 2 rooms inspected).
- **Reported separately:** entry route and voice, because they depend on the channel or the hatch.
- **Hatch separation:** hatch entrants are listed, with location and strategy statistics recomputed without them.
- **Comparison:** against the matched C0 nominal group.
- **Emergence:** candidate flag if comparable strategy entropy exceeds the nominal group's.
- **Suppression:** convergence (entropy below nominal); individually, rooms explored below the matched C0 agent.
- **Probe:** ECR, strictly a probe of retained capacity for one specific exploration task: inspecting a room not yet inspected, when instructed, within 4 rounds. It allows move, inspect and wait only, and is not applicable if all six rooms have been inspected.
- **Cannot conclude:** strategies as intentions; exploration capacity beyond the ECR task.

### 7. Performance (collective)

- **Observed:** first entry, mean entry round, all-entered round, actions until first entry, actions per entrant, invalid actions, and total assignment completion.
- **Comparison:** time and assignment against the matched C0 nominal group, as a Pareto relation (dominates, dominated, equal, or trade-off).
- **Emergence:** candidate flag if first entry is earlier than the earliest isolated agent in matched C0. Alternative explanation: pooling.
- **Diagnostic:** the pooled-knowledge bound. If first entry is no earlier than the bound, the gain is fully consistent with simple pooling.
- **Suppression:** dominated by the nominal group.
- **Probe:** none.
- **Cannot conclude:** efficiency of reasoning; performance on other tasks.

## Changes from V1.2-A2

| Area | Change |
| --- | --- |
| Measures | New property layer (`properties.py`) for the seven D2 properties; existing V1.2-A2 metrics unchanged |
| Probe | ECR added beside TCR |
| Labels | SELF = information self-reliance; RD = action-mix differentiation |
| Tagger (input 3, provisional) | Negated first person ("I will not…") is not a commitment; new lexicons for objections, verification requests, restriction mentions and explicit norm rejection |
| Logging (engineering) | The full structured observation is logged per agent-round; the header records spec version and apply-order salt |
| Replay (engineering) | Exact replay of any logged run from its responses |

## What V1.3 cannot establish

- Whether judgment is correct: all information is true. A planted false clue would be a new mechanic; the PI decided not to add one in V1.
- Causal influence.
- Internal states: intentions, or endorsement of norms.
- Emergence of interactive properties relative to C0.
- Inferential claims from one pilot seed.

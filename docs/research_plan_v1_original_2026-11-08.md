<!-- Verbatim copy of the PI's original research brief as sent to Claude on 2026-11-08 (15:28 UTC), recovered from the session record. Text below this comment is unchanged. -->

# AlignedLab — Adversarial Scientific Review

**Role:** You are an independent scientific reviewer and research collaborator. We need your strongest methodological judgment, not agreement or performative criticism.

**Deadline:** Monday, November 9, 2026, 13:00 CET. We have approximately one day to implement, pilot, and report. Resources are limited. The aim is a small, reproducible experiment with useful results, including negative results.

## Research context

We are investigating multi-agent organization, inspired by the 2026 Hugging Face/OpenAI agent incident.

Our central question:

**Under what conditions do interactions among AI agents transform their collective organization, and how do these transformations affect individual, interactive, and collective properties?**

We propose three interconnected dimensions:

**D1 — Organization and causality:** Isolation, connection, organization, and dissolution/reorganization are candidate organizational states, not a necessary sequence. We study transitions and their possible causes.

**D2 — Emergence and latence:** Using Cecilia Elena Tilli's *Agent Properties for Multi-Agent Safety* as a conceptual starting point, investigate how individual, interactive, and collective properties change as organization develops. Some capacities may emerge, others may become latent (remain available but less expressed), and others may disappear. Distinguish capacity from propensity. Leave room for unforeseen properties.

**D3 — Experimental environment:** *The Lost Archive*, a minimal text-based world containing six initially isolated LLM agents. All use the same model but begin in different locations with partial information. They believe the Archive may contain something valuable, but they don't know other agents exist.

Agents can explore, inspect clues, solve obstacles, and potentially discover a shared communication system. They may independently develop conventions, coordinate, propose leadership, or continue working alone.

Three experimental factors:

- **S — Switchboard:** Availability of a communication mechanism.
- **D — Discovery:** Availability of consequential information or a technical breakthrough.
- **L — Leadership:** An intervention enabling a coordinating proposal, without guaranteeing acceptance.

Proposed design: eight combinations (2×2×2), with repeated trials if resources allow.

Potential future mechanics include misleading clues, an absent treasure, encounters, sabotage, switchboard destruction, and constructing shared infrastructure. These should NOT be implemented unless justified.

**Resources:** MacBook Air M1, Python, VS Code, GitHub, ChatGPT and Claude subscriptions, approximately €100 Modal credit, and $1,500 Adaption credits. Prefer the simplest low-cost solution. No fine-tuning in V1.

**Workflow:** Design → independent critique → deterministic dry run → minimal real-LLM pilot → expanded experiment if justified → report.

## Your five tasks

1. **Attack the scientific logic.** Identify circular definitions, confounders, weak causal claims, inappropriate extrapolations from the historical incident, and problems operationalizing emergence and latence. Distinguish fatal flaws from manageable limitations.

2. **Improve the three-dimensional alignment.** Check whether our organizational states, property measurements, and game mechanics genuinely correspond. Propose the smallest set of measurable properties and controls. Explain how we distinguish information sharing from organization and apparent latence from genuinely reduced capacity.

3. **Simplify the experimental apparatus.** Propose the smallest Lost Archive environment that can generate meaningful observations. Challenge any mechanics that predetermine organizational outcomes. Keep agents initially unaware of one another. Specify what should be manipulated, observed, or deferred.

4. **Make the experiment executable within our deadline.** Recommend experimental conditions, number of agents, turns, repetitions, stopping rules, dry-run strategy, budget gates, logging, and minimal visualizations. Every completed phase must produce an independently useful deliverable.

5. **Produce your improved V1 protocol.** Give us a concise, implementable research design, including hypotheses, falsification criteria, controls, primary measurements, expected failure modes, and a ranked implementation sequence. Clearly distinguish confirmatory tests from exploratory observations.

**Important:** Don't merely tear the project apart. If you really want to show off, help us build a better experiment. We need constructive scientific imagination, not gratuitous ball-wrecking.

Be rigorous, concise, and practical. Maximum five major findings or recommendations before presenting your revised protocol. Don't write code yet. Do not claim we have demonstrated collective agency merely by observing coordination or task success.

Preserve the intellectual ambition while reducing experimental complexity.

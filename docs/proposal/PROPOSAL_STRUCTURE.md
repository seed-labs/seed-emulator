# Agent Section Structure for Proposal Writing

This section is the recommended structure for integrating the agent work into a larger proposal without making it read like a software README.

## Core positioning

The agent work should be framed as a methodological layer for trustworthy closed-loop experimentation over SEED, not as an interface convenience or a demo system.

## Recommended section order

1. Problem gap

Current network simulators provide realism, but experiment orchestration remains manual, fragmented, and weakly auditable. General-purpose agents provide flexible planning, but they remain brittle and scientifically underconstrained in dynamic runtime environments.

2. Scientific idea

State the central claim:

Autonomous experimentation becomes scientifically trustworthy only when structured state grounding, bounded intervention, verification, and evidence archival are treated as one closed-loop discipline.

3. Methodological architecture

Organize into three conceptual layers:

- SEED Emulator as executable experimental substrate
- runtime control and evidence plane
- trustworthy agentic orchestration layer

4. Key hypothesis

A layered design combining structured runtime state, deterministic intervention surfaces, policy-gated execution, and evidence-backed verification can make autonomous network experimentation both effective and scientifically reliable.

5. Research content

Use three tightly scoped parts:

- grounded task formalization
- bounded and supervised orchestration
- evidence-centric trajectory evaluation

6. Evaluation and deliverables

Avoid vague claims. Use measurable outputs:

- class coverage
- attach success
- verification success
- rollback quality
- planner stability
- artifact completeness
- reproducibility under repeated execution

7. Scientific significance

Stress that the contribution is a reusable methodology for trustworthy agentic experimentation in realistic network environments, with value to operations, security studies, and reproducible systems research.

## Language rules

- avoid “demo”, “shell convenience”, “script wrapper”, “dashboard”
- prefer “methodology”, “orchestration”, “evidence”, “bounded intervention”, “auditable trajectory”
- discuss runtime interaction in terms of scientific discipline, not product features

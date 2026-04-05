# Seed Agent Stage Report Outline

This outline is for a results-first report and a clean slide deck. It assumes the audience first wants to see what the agent can actually do on running SEED networks, and only then wants the architectural and scientific explanation.

## Slide 1. One-sentence claim

SEED now supports supervised agentic operation on already-running network experiments through an attach -> inspect -> decide -> operate -> verify -> summarize loop.

## Slide 2. What is already real

- real attached runtime operation, not offline script generation
- real bounded interventions on running SEED services and routers
- real evidence bundles, verification results, and rollback traces
- six validated scenario classes over live outputs

Recommended evidence:

- `examples/agent-missions/reports/20260318T085945Z/review_summary.json`
- one screenshot or cropped excerpt showing six classes passed

## Slide 3. Six-class baseline

- Diagnosis / Maintenance
- Disturbance Recovery
- Routing Security
- Service Reachability
- Security Offense-Defense
- Research Experiments

Show:

- one line per class
- one representative task ID
- whether attach, risky action, rollback, and verification were observed

## Slide 4. Hard result summary

- six classes passed in review pack
- attach success: 6/6
- verification success: 6/6
- rollback verified: 2
- risky actions observed: 7

Message:

The agent is not only planning; it is operating under supervision on running experimental systems.

## Slide 5. Interactive baseline

Main point:

The primary baseline is interactive attached-runtime operation, not only canned mission execution.

Show:

- a live `seed-codex plan` or `seed-codex ui` interaction
- one `llm_primary` plan example
- one task requiring explicit confirmation for elevated action

## Slide 6. Where template fallback used to come from

Explain the old root causes succinctly:

- token mismatch across SeedOps and SeedAgent
- transient upstream gateway failures
- GPT-5 temperature incompatibility
- LLM playbook schema mismatch with SeedOps execution surface

Then state what was fixed:

- provider retries and clearer diagnostics
- GPT-5 compatibility
- LLM playbook normalization to canonical SeedOps schema

## Slide 7. The architectural closure

Use the architecture figure.

Talking point:

The key closure is not “LLM can call tools”; it is that a realistic network emulator, an operational control-and-evidence plane, and a policy-bounded agent layer now form one closed experimental loop.

## Slide 8. The methodological principle

Use the principle figure.

Talking point:

Trustworthy autonomous experimentation requires grounded state, bounded action, supervised escalation, verification, and archival evidence to be enforced together.

## Slide 9. Why this matters scientifically

- turns simulation from static environment into controlled experimental instrument
- supports repeatable operational and research workflows
- exposes execution trajectory, not only final success
- gives the team a concrete contribution and evaluation contract

## Slide 10. Current boundary and next step

Be explicit:

- mission/task baseline is strong
- free-form interactive planning is much better but still not perfectly stable for every prompt
- next work should formalize planner stability benchmarks, contribution contracts, and domain-specific strengthening where failure clusters remain

## Appendix suggestions

- one page on checklist conclusions
- one page on contribution workflow
- one page on open backlog by scenario class

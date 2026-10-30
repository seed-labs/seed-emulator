---
name: seedemu-paper-search
description: Use when researching academic papers that could be reproduced, evaluated, or strengthened with SeedEmu, especially systems, networking, security, measurement, blockchain, overlay-network, or future-Internet papers; supports multi-round paper discovery, candidate tracking, SeedEmu capability mapping, evidence-gated ranking, and experiment blueprints.
---

# SeedEmu Paper Search

## Load First

Before assessing papers, read:

- `AGENTS.md`
- `../../knowledge/capability-map.md`
- `../seedemu-capability-refresh/SKILL.md`

Use these optional templates when the task is broad, multi-round, or likely to
produce a shortlist:

- `../../agents/paper-researcher/templates/research-state-template.md`: persistent state for search rounds and decisions.
- `../../agents/paper-researcher/templates/paper-evaluation-template.md`: detailed assessment for a serious candidate.

Before searching for papers, run the `seedemu-capability-refresh` workflow. This
means inspecting the local SeedEmu repository, comparing repository evidence
against `../../knowledge/capability-map.md`, and updating the context when capabilities,
examples, paths, limitations, or evidence are missing or stale.

If `../../knowledge/capability-map.md` is still too thin for the current paper class
after that refresh, inspect the repository again before making strong claims:

1. Inspect the local SeedEmu repository root.
2. Read relevant docs, examples, services, layers, and tests.
3. Edit `../../knowledge/capability-map.md` with updated capability summaries, limitations, and evidence paths.

## Operating Mode

Run the search as an iterative research process, not as a static keyword match.
Carry forward state, explain why candidates move up or down, and keep the next
round focused on the most useful uncertainty.

Create or update `../../agents/paper-researcher/runs/<topic-slug>/research-state.md` from
`../../agents/paper-researcher/templates/research-state-template.md` when any of these are true:

- the user asks for a broad search;
- the task will span multiple rounds;
- more than five candidate papers are being compared;
- the shortlist depends on unresolved evidence gaps;
- the user is iteratively refining venue, domain, or feasibility preferences.

Use candidate statuses consistently:

- `discovered`: looks relevant from title, abstract, venue, or metadata.
- `tentative`: has plausible fit but incomplete paper-side or SeedEmu-side evidence.
- `strong`: has enough evidence for a concrete SeedEmu blueprint.
- `shortlisted`: should be kept for final comparison.
- `rejected`: has a clear blocker or is weaker than alternatives.
- `final`: selected for the final recommended set.

## Search Workflow

1. Refresh SeedEmu capability context using `../seedemu-capability-refresh/SKILL.md`.
2. Clarify the research brief only if the missing preference changes the search space.
3. Seed the search from several angles:
   - venue and year: S&P, USENIX Security, CCS, NDSS, SOSP, OSDI, EuroSys, ATC, NSDI, SIGCOMM, IMC, CoNEXT, HotNets;
   - SeedEmu capability: BGP, DNS, PKI, botnet, DDoS, Tor, IPFS, CDN, email, Ethereum, Chainlink, Monero, SCION, distributed deployment;
   - experiment barrier: expensive scale, unsafe attack, hard-to-repeat routing, closed infrastructure, missing testbed, artifact evaluation;
   - artifact terms: replication, dataset, testbed, topology, emulation, simulation, measurement, workload, trace.
4. Search or inspect papers using available paper-search tools, user-supplied PDFs/metadata, proceedings pages, artifacts, or web sources.
5. Extract each paper's experimental requirements:
   - topology, scale, and network roles;
   - protocols, services, and infrastructure dependencies;
   - security-sensitive behavior and safe closed-lab framing;
   - workloads, traffic, datasets, and traces;
   - metrics and validation method;
   - artifact or replication availability;
   - real-world cost, safety, ethics, or repeatability barriers.
6. Map requirements to SeedEmu capabilities from the refreshed `../../knowledge/capability-map.md`.
7. Inspect the SeedEmu repository directly when context evidence is insufficient.
8. Estimate feasibility:
   - `existing`;
   - `light top-layer development`;
   - `substantial development`;
   - `poor fit`.
9. Rank papers using:
   - directness of SeedEmu fit;
   - safety, cost, repeatability, and scale value;
   - evidence specificity;
   - venue quality and likely impact;
   - artifact availability;
   - amount and risk of top-layer development;
   - clarity of the resulting SeedEmu demonstration.

## Per-Round Behavior

At the end of each research round:

- summarize what changed in the candidate pool;
- promote, downgrade, or reject papers with a concrete reason;
- record missing evidence in the research state when state is being used;
- identify the best next query, venue, paper, artifact, or repository path to inspect;
- ask the user only for decisions that materially affect the search direction.

Prefer a small, defensible shortlist over a broad list of weak matches.

## Evidence Gate

Do not recommend a paper as `strong`, `shortlisted`, or `final` unless both are
available:

- Paper evidence: a concise quote or close paraphrase from metadata, abstract, full text, evaluation section, artifact README, dataset description, or replication instructions.
- SeedEmu evidence: a capability, example, service, layer, component, compiler, doc path, or test from `../../knowledge/capability-map.md` or direct repo inspection.

If evidence is partial, label the paper as `tentative` and state what must be
checked next. If either side cannot be supported after inspection, reject or
downgrade the candidate.

## Detailed Evaluation

Use `../../agents/paper-researcher/templates/paper-evaluation-template.md` for papers that are likely to enter the
shortlist or require careful feasibility judgment.

Each detailed evaluation should distinguish:

- exact reproduction versus approximation;
- existing SeedEmu capability versus top-layer development;
- scenario code versus core emulator changes;
- experimental value to the paper versus value as a SeedEmu demonstration;
- safe closed-emulation framing for security-sensitive work.

## Output Shape

For each strong candidate, provide:

- paper title, authors if available, venue/year, and source link;
- one-sentence fit summary;
- paper evidence;
- SeedEmu evidence with file paths or context references;
- feasibility level;
- SeedEmu capabilities involved;
- experiment blueprint: topology, services, workloads, metrics, validation plan, expected outputs;
- required development work;
- value argument: cost, safety, repeatability, scale, ethics, teaching, or artifact-evaluation benefit;
- risks and unknowns.

For ranked lists, include why lower-ranked papers are weaker. For iterative
sessions, include the recommended next round rather than pretending the search
is complete.

## Safety Boundary

For security, malware, botnet, DDoS, routing-attack, scanning, or abuse-oriented
papers, only describe closed SeedEmu experiments. Do not provide real-world
attack steps, target selection, exploit operation, evasion, persistence,
credential theft, or deployment outside the emulator.

## Anti-Patterns

Avoid:

- treating keyword overlap as feasibility evidence;
- recommending papers without paper-side and SeedEmu-side evidence;
- hiding major top-layer development under `existing`;
- overfitting to one venue when the user asked for broad discovery;
- expanding the harness with runtime code or generated caches unless the project scope changes.

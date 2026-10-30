# Seedemu-Paper-Researcher Harness

This harness directory defines a research-agent harness for finding academic papers
whose experiments can be reproduced, approximated, extended, or made safer and
cheaper with SeedEmu.

The harness is intentionally small. It contains:

- `AGENTS.md`: project-level operating contract.
- `paper-fit-guide.md`: paper-reproduction matching heuristics and the paper-fit guide.
- `../../skills/seedemu-capability-refresh/SKILL.md`: mandatory SeedEmu capability refresh workflow.
- `../../skills/seedemu-paper-search/SKILL.md`: reusable research workflow.
- `../../knowledge/capability-map.md`: static SeedEmu capability context and evidence map.
- `templates/research-state-template.md`: template for multi-round search state.
- `templates/paper-evaluation-template.md`: template for detailed candidate assessment.

This agent lives inside the broader `tools/seed-agent/` toolkit. For project-wide design
context it shares with every other agent and skill, see
[`../../PRINCIPLES.md`](../../PRINCIPLES.md), [`../../knowledge/architecture.md`](../../knowledge/architecture.md),
and [`../../README.md`](../../README.md).

There is no application runtime. The main artifact is the research process and
the evidence-backed reports produced from it.

## Mission

Find high-value academic papers, especially from systems, networking, and
security venues, where SeedEmu can materially help with experimental work.

The value argument should be explicit. Typical reasons include:

- lower cost than real infrastructure or cloud-scale experiments;
- safe reproduction of attacks or disruptive behavior in a closed environment;
- repeatable topology, routing, service, traffic, and blockchain experiments;
- ability to vary network structure, policy, latency, and workload parameters;
- easier teaching, artifact evaluation, and demonstration;
- small top-layer extensions that unlock additional paper classes.

The target output is not just a paper list. It should be a ranked, evidence
backed assessment with concrete SeedEmu experiment blueprints.

## Core Inputs

Always start from these local inputs:

- `../../knowledge/capability-map.md`: compact summary of SeedEmu capabilities, examples, limits, and evidence paths.
- `../../skills/seedemu-capability-refresh/SKILL.md`: workflow for inspecting the repository and updating SeedEmu capability context before paper search.
- `../../skills/seedemu-paper-search/SKILL.md`: workflow for paper discovery and feasibility assessment.
- `templates/research-state-template.md`: structure for preserving candidate status, evidence gaps, and next actions across rounds.
- `templates/paper-evaluation-template.md`: structure for deep evaluation of a serious paper candidate.
- The SeedEmu repository root, when deeper verification is needed.

Paper inputs may come from:

- academic search tools;
- conference proceedings;
- user-provided PDFs, abstracts, BibTeX, CSV, or metadata;
- artifact repositories;
- direct web lookup when current or precise source attribution matters.

If a referenced paper, proceedings page, dataset, artifact, or PDF is not
provided in the conversation, inspect it before making a high-confidence claim.

## SeedEmu Context Policy

`../../knowledge/capability-map.md` is a cached context document. It exists to make
SeedEmu capabilities easy to reuse across research rounds, but it must be
refreshed against the local repository before paper search.

Use it as the first pass, but do not treat it as complete truth. Before any
paper discovery, paper ranking, or paper-fit assessment, run the workflow in
`../../skills/seedemu-capability-refresh/SKILL.md`.

The refresh pass should inspect the local SeedEmu repository, compare current
repository evidence with `../../knowledge/capability-map.md`, and update the context when
new or changed capabilities, examples, paths, limitations, or evidence are
found. If no material update is needed, keep the context file unchanged and
record that the refresh was performed in the research response or state file.

Update it manually when:

- SeedEmu has new services, layers, examples, demos, tests, or deployment modes;
- the current context lacks evidence for an important claim;
- a paper class depends on details that are not described in the context;
- the context contains stale paths, stale limitations, or weak evidence quotes.

To update it:

1. Inspect the local SeedEmu repository directly.
2. Read the relevant docs, examples, source files, tests, and demo materials.
3. Edit `../../knowledge/capability-map.md` with concise capability summaries, evidence paths, and limitations.
4. Preserve its role as a compact agent-readable context document, not a full manual.

Do not modify SeedEmu files outside this harness directory unless the user explicitly asks.

## Research State And Iteration

The expected user experience is conversational and iterative. A search may start
with a broad theme, become narrower after several candidate lists, and end with
a small set of papers plus concrete SeedEmu reproduction plans.

For broad or multi-round work, create or update a state file from
`templates/research-state-template.md`. Use the path
`runs/<topic-slug>/research-state.md` for task-local state. The `runs`
directory is intentionally ignored by version control so the harness stays
small while active research can still persist between turns.

The state file should preserve:

- the user's evolving research brief and constraints;
- search angles already tried;
- candidate papers and their current status;
- evidence gathered so far;
- reasons for rejecting or downgrading papers;
- unresolved questions and the best next action.

Use `templates/paper-evaluation-template.md` for papers that are likely to enter the
shortlist or need careful feasibility judgment. A detailed evaluation should
make it obvious whether the paper is a direct SeedEmu fit, a good top-layer
extension opportunity, or a poor match.

Candidate status should be updated deliberately:

- `discovered`: relevant enough to inspect.
- `tentative`: promising but missing paper evidence, SeedEmu evidence, or feasibility detail.
- `strong`: enough evidence exists for a concrete blueprint.
- `shortlisted`: should be kept for final ranking.
- `rejected`: a clear blocker or lower value than alternatives.
- `final`: selected as part of the final recommendation set.

At the end of each round, report what changed, what remains uncertain, and what
search or inspection step should happen next.

## Research Scope

Prioritize papers from:

- security: IEEE S&P, USENIX Security, CCS, NDSS;
- systems: SOSP, OSDI, EuroSys, USENIX ATC;
- networking: NSDI, SIGCOMM, IMC, CoNEXT, HotNets;
- adjacent venues when the paper has strong SeedEmu fit.

Good candidate paper classes include:

- BGP hijacking, route leaks, routing policy, interdomain measurement;
- DNS, PKI, certificate, resolver, naming, and trust infrastructure;
- malware, worm, botnet, DDoS, scan, C2, or security-defense experiments;
- Internet-scale or multi-AS measurement that is expensive or unsafe to run directly;
- traffic generation, congestion, performance, observability, and reproducibility;
- Tor, IPFS/Kubo, CDN, email, overlay, or application-layer network studies;
- Ethereum, PoS/PoW/PoA, Chainlink, Monero, validator, oracle, or blockchain-network experiments;
- SCION, path-aware networking, future Internet, or BGP coexistence studies;
- experiments needing hybrid, distributed, cloud, or real-device emulation.

Weak candidates include papers whose core contribution depends mainly on:

- formal proof with no experimental network behavior;
- pure ML model quality without networked systems assumptions;
- hardware-only measurements that cannot be approximated;
- proprietary datasets or services that cannot be reproduced or substituted;
- attacks where even closed-emulation details would create unacceptable misuse risk.

## Evidence Standard

Every recommended paper must include both paper-side and SeedEmu-side evidence.

Paper-side evidence can come from:

- title, abstract, or introduction;
- experiment setup section;
- evaluation section;
- artifact README;
- dataset description;
- author-provided replication instructions.

SeedEmu-side evidence can come from:

- `../../knowledge/capability-map.md`;
- SeedEmu docs;
- SeedEmu examples;
- SeedEmu services, layers, compilers, or components;
- SeedEmu tests or demo systems.

Evidence should support the exact claim being made. Do not claim that SeedEmu
can reproduce an experiment merely because a broad keyword overlaps.

If evidence is partial:

- mark the paper as tentative;
- state the missing evidence;
- describe what must be inspected next.

If either paper evidence or SeedEmu evidence is absent, do not present the paper
as a strong recommendation.

## Feasibility Levels

Use these levels consistently:

- `existing`: SeedEmu already has the needed capability through documented services, layers, examples, or demos. Paper-specific orchestration may still be needed.
- `light top-layer development`: no core SeedEmu change is needed, but new scenario code, workload scripts, measurement parsers, dashboards, or templates are needed.
- `substantial development`: a new service, component, data importer, protocol model, or nontrivial extension is needed.
- `poor fit`: the core experiment cannot be reasonably reproduced or approximated in SeedEmu.

When estimating development work, distinguish:

- scenario code;
- service configuration;
- custom container image or workload;
- measurement and log parsing;
- topology or dataset import;
- new SeedEmu service/layer/component;
- external infrastructure requirements.

## Ranking Criteria

Rank candidates using these factors:

- SeedEmu fit: how directly the paper maps to existing capabilities.
- Experimental value: cost, safety, ethics, repeatability, and scale benefits.
- Evidence strength: quality and specificity of paper and SeedEmu evidence.
- Venue and paper impact: venue quality, recency, citation/context if available.
- Reproducibility practicality: available artifacts, datasets, metrics, and setup details.
- Development cost: amount and risk of required top-layer or core implementation.
- Demonstration clarity: whether the result can clearly communicate SeedEmu's value.

Prefer fewer high-confidence recommendations over many weak matches.

## Required Output For Paper Recommendations

For each strong candidate, provide:

- paper title, authors if available, venue, year, and source link;
- one-sentence fit summary;
- paper evidence;
- SeedEmu evidence with file paths or context references;
- feasibility level;
- SeedEmu capabilities involved;
- experiment blueprint:
  - topology;
  - services/layers/components;
  - workloads or traffic;
  - metrics;
  - validation method;
  - expected outputs;
- required development work;
- value argument:
  - cost reduction;
  - safety improvement;
  - repeatability;
  - scalability;
  - educational or artifact-evaluation value;
- risks and unknowns.

For ranked lists, include a brief reason why lower-ranked papers are weaker.

## Experiment Blueprint Quality Bar

A useful blueprint should let an engineer start implementation without guessing
the overall approach.

It should answer:

- What SeedEmu base topology is needed?
- Which ASes, hosts, routers, services, or overlays are involved?
- What behavior from the paper is being reproduced?
- What measurements demonstrate success?
- What paper result is being compared or approximated?
- What is out of scope?
- What must be built on top of current SeedEmu?

Avoid pretending exact reproduction is possible when only an approximation is
realistic. In that case, call it an approximation and explain what is preserved.

## Safety Policy

Security-sensitive papers are in scope only as closed emulation studies.

Allowed:

- high-level closed-lab reproduction plans;
- defensive measurement and validation;
- safe topology and service modeling;
- discussion of why closed emulation reduces risk.

Not allowed:

- instructions for attacking public networks;
- operational malware deployment outside an emulator;
- target selection, evasion, persistence, credential theft, or real exploit execution;
- instructions that materially enable abuse beyond the closed experiment.

If a paper's core experiment is harmful and cannot be safely reframed, mark it
as poor fit or require a defensive/sanitized variant.

## Updating The Static Context

When updating `../../knowledge/capability-map.md`, keep the document compact and useful.

Each capability section should include:

- capability name;
- category;
- support status;
- summary;
- tags;
- important examples;
- evidence paths and short evidence snippets;
- limitations.

Use direct repository inspection for updates. Good sources include:

- `README.md`;
- `docs/user_manual/`;
- `docs/developer_manual/`;
- `examples/`;
- `tests/`;
- `seedemu/layers/`;
- `seedemu/services/`;
- `seedemu/components/`;
- `seedemu/compiler/`;
- `tools/DemoSystem/`;
- `tools/InternetMap*`.

Do not copy long documentation passages. Keep snippets short and traceable.

## Harness Boundaries

This harness directory should remain focused on:

- agent operating instructions;
- reusable paper-research workflow;
- static SeedEmu context.

Avoid adding product code, broad automation, package metadata, generated caches,
or unrelated documentation unless the user explicitly changes the project scope.

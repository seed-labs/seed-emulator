# SEED-Emulator Agent Toolkit (`seed-agent`)

The home for SEED-Emulator's **AI products** — the design knowledge, skills, and agents that let
AI assistants ramp up on this project fast and develop on it *without drifting from its design
philosophy*.

SEED-Emulator (the `seedemu` library) is a programmable Internet emulation platform used for
research and education across 80+ countries. As the project grows — new services, layers, and
experiments, increasingly built with AI help — the risk is that contributions fight the
architecture instead of extending it. This toolkit captures the project's accumulated design
wisdom as durable, reusable artifacts so every future AI-assisted change stays on-philosophy.

## If you are an AI agent: start here

1. **Read [`PRINCIPLES.md`](PRINCIPLES.md) first.** It is the distilled design philosophy of
   SEED-Emulator (from the design paper, grounded in the code). Everything else serves it.
2. Skim [`knowledge/architecture.md`](knowledge/architecture.md) for the lifecycle and repo map.
3. Pick the skill that matches your task (see below).
4. Check [`knowledge/capability-map.md`](knowledge/capability-map.md) before assuming something
   does or doesn't exist.

When a request would require breaking a principle, say so and propose an in-architecture
alternative.

## Contents

```
seed-agent/
├── PRINCIPLES.md            ★ the design philosophy — read first
├── paper.pdf                  the source design paper this toolkit distills
├── knowledge/                 durable, shared reference material
│   ├── architecture.md        four-phase lifecycle + layer stack + repo map (with code anchors)
│   ├── capability-map.md      what seedemu can do today, with evidence paths and limits
│   └── glossary.md            definitions of the core terms
├── skills/                    reusable, invocable workflows
│   ├── seedemu-compose-scenario/   build a new emulation scenario with the SDK
│   ├── seedemu-add-service/        add a new service / layer / component / compiler
│   ├── seedemu-capability-refresh/ re-derive the capability map from the repo
│   └── seedemu-paper-search/       find papers reproducible/strengthenable with seedemu
└── agents/                    self-contained agent harnesses
    └── paper-researcher/      operating contract + paper-fit guide + templates
```

## The artifact types (and how to extend the toolkit)

This structure is meant to grow. Each kind of artifact has a clear home:

- **Principles** (`PRINCIPLES.md`) — the *why*. Stable design tenets. Change rarely, and only
  with strong justification from the paper or a deliberate design decision.
- **Knowledge** (`knowledge/`) — the *what and where*. Factual, evidence-backed reference about
  the codebase. Add a file here when there is durable orientation material that multiple skills
  or agents would reuse. Keep entries concise and traceable to real paths.
- **Skills** (`skills/`) — the *how*. A reusable workflow for a recurring task, as a
  `SKILL.md` with `name` + `description` frontmatter. Add one when a task is done often enough to
  be worth codifying. Each skill should reference the principles it upholds.
- **Agents** (`agents/`) — a *role*. A self-contained harness (operating contract + templates +
  any agent-specific guidance) for a distinct kind of work. Add a subdirectory when a body of
  work needs its own standing instructions, like `paper-researcher/` does.

### Adding a new skill (the most common extension)
1. Create `skills/<skill-name>/SKILL.md` with frontmatter:
   ```yaml
   ---
   name: <skill-name>
   description: Use when … (be specific about the trigger so it's discoverable).
   ---
   ```
2. Open with a "Read first" section linking the relevant principles and knowledge.
3. Give a concrete, step-by-step workflow grounded in real code paths and `examples/`.
4. End with a checklist that maps steps back to the principles.

## Design intent of this toolkit

- **Principles are upstream of everything.** Skills and agents cite them; they don't restate or
  contradict them.
- **One source of truth per fact.** Capability questions → `capability-map.md`. Term definitions
  → `glossary.md`. Architecture → `architecture.md`. Don't duplicate; link.
- **Everything is traceable.** Claims about the codebase cite real, repo-root-relative paths so a
  reader can verify and so the docs can be refreshed as the code evolves.
- **Built to grow.** Adding a capability to seedemu should come with adding/refreshing the
  matching artifact here, so the toolkit stays current with the project.

# SEED Emulator User Manual Index

This is the primary manual hub for `seed-email-service`.

---

## Recommended reading paths

### Path A: Build and run a lab (first-time users)

1. [Overall flow](./overall_flow.md)
2. [Autonomous system](./as.md)
3. [BGP and peering](./bgp.md)
4. [Compilation](./compiler.md)
5. [Visualization](./visualization.md)

### Path B: Operate an existing running lab (OPS)

1. [SeedOps MCP guide](./mcp_seedops.md)
2. [Selectors and inventory](./mcp_seedops.md#phase-1-workspaces--inventory)
3. [Playbooks/jobs/artifacts](./mcp_seedops.md#phase-2-jobs--yaml-playbooks)
4. [Six-class mission baseline](../../examples/agent-missions/README.md)

### Path C: Agent-driven attached-runtime operation (recommended baseline)

1. Start from repo root with `scripts/seed-codex up`
2. Enter interactive Codex with `scripts/seed-codex ui`
3. Attach to a live output and operate through the loop:
   `attach -> inspect -> decide -> operate -> verify -> summarize`
4. Use non-interactive `plan/run/mission/verify` only for regression, replay, or evidence export
5. Keep the operator quick guide open:
   [Agent runtime quick guide](./agent_runtime_quick_guide.md)
6. If you need the real active prompt/MCP/skill surface:
   [seed-codex active stack](./seed_codex_active_stack.md)

---

## Core emulator manuals

- [Create an emulator: overall flow](./overall_flow.md)
- [Autonomous system](./as.md)
- [Internet exchange](./internet_exchange.md)
- [BGP routers and peering](./bgp.md)
- [Routing](./routing.md)
- [Node customization](./node.md)
- [Component and binding](./component.md)
- [Compilation](./compiler.md)
- [Visualization](./visualization.md)
- [Docker images](./docker.md)

---

## MCP operations control plane

- [SeedOps: operate already-running networks](./mcp_seedops.md)
- [Agent runtime quick guide](./agent_runtime_quick_guide.md)
- [seed-codex active stack](./seed_codex_active_stack.md)
- [Attached-runtime showcase guide and scenario map](./attached_runtime_capability_audit.md)
- [Seed-Agent mission packs and six-class baseline](../../examples/agent-missions/README.md)
- [Seed-Agent mission runtime logbook](./agent_missions_logbook.md)
- [Seed-Agent runtime evidence (closed-loop checks)](./RUN_EVIDENCE.md)
- [Seed-Agent platform review](./seed_agent_platform_review.md)

---

## Presentation and proposal material

- [Proposal materials index](../proposal/README.md)
- [Showcase pack index](../../showcase/README.md)

---

## Domain-specific manuals

- [Internet advanced features](./internet/README.md)
- [Blockchain emulator](./blockchain/README.md)

---

## Notes and troubleshooting

- [General notes](./00_notes.md)
- [Docker Hub proxy](./dockerhub_proxy.md)
- [Misc manual topics](./misc.md)

# Agent-Specific Attached-Runtime Bundles

`examples/agent-specific` is the curated example layer for SEED Agent attached-runtime work.

This directory is not a generic topology catalog.
It is the agent-first layer that answers four concrete questions for each selected runtime scenario:

1. What is the source running network?
2. Which tools are the primary path, and which ones are only fallback or risky?
3. How should the agent orchestrate the work across high-level planning, deterministic execution, and evidence collection?
4. Which `scripts/seed-codex` commands and which task `skill_patterns` actually fit the scenario?

Numbering rule:

- `Z**` keeps the two-digit suffix of the source example number.
- The directory slug keeps the source family in the human-readable part when needed.
- Example: `B29_email_dns` becomes `Z29_b29_mail_runtime_ops`.

This layer sits above:

- generic topology examples under `examples/basic`, `examples/internet`, `examples/blockchain`, `examples/scion`, `examples/yesterday_once_more`
- structured runtime tasks under `examples/agent-missions`
- older showcase automation under `examples/agent-base`

The intent is:

- generic examples define networks
- mission packs define task contracts
- agent-specific bundles define the agent-facing runtime package

## Bundle Matrix

| Bundle | Source | Live status | Primary role |
|---|---|---|---|
| `Z00_b00_attached_runtime` | `B00_mini_internet` | `go` | routing diagnostics, path maintenance, controlled experiments |
| `Z01_y01_prefix_hijack_drill` | `Y01_bgp_prefix_hijacking` | `conditional_go` | high-impact routing security drill candidate |
| `Z02_a02_mpls_control_plane` | `A02_transit_as_mpls` | `conditional_go` | FRR/MPLS control-plane inspection |
| `Z12_a12_bgp_mixed_backend` | `A12_bgp_mixed_backend` | `conditional_go` | selective FRR migration and mixed-backend BGP validation |
| `Z13_a13_exabgp_control_plane` | `A13_exabgp_control_plane` | `conditional_go` | ExaBGP runtime tooling and control-plane evidence |
| `Z14_a14_bgp_event_looking_glass` | `A14_bgp_event_looking_glass` | `conditional_go` | route-state and event-stream BGP observability |
| `Z28_b28_traffic_lab` | `B28_traffic_generator` | `go` | runtime traffic-role discovery and experiment design |
| `Z29_b29_mail_runtime_ops` | `B29_email_dns` | `go` | service reachability, disturbance recovery, security triage |

## Layout

```text
examples/agent-specific/
├── manifest.yaml
├── Z00_b00_attached_runtime/
│   ├── bundle.yaml
│   └── README.md
├── Z01_y01_prefix_hijack_drill/
│   ├── bundle.yaml
│   └── README.md
├── Z02_a02_mpls_control_plane/
│   ├── bundle.yaml
│   └── README.md
├── Z12_a12_bgp_mixed_backend/
│   ├── bundle.yaml
│   └── README.md
├── Z13_a13_exabgp_control_plane/
│   ├── bundle.yaml
│   └── README.md
├── Z14_a14_bgp_event_looking_glass/
│   ├── bundle.yaml
│   └── README.md
├── Z28_b28_traffic_lab/
│   ├── bundle.yaml
│   └── README.md
└── Z29_b29_mail_runtime_ops/
    ├── bundle.yaml
    └── README.md
```

## Contract

Every `bundle.yaml` must declare:

- source runtime and output path
- high-level tools, preferred ops tools, and risky tools
- orchestration path across `seed_agent_*`, task packages, and deterministic fallback
- task `skill_patterns`
- minimal command entrypoints
- current live readiness and hard boundaries

The validation test lives in:

- `subrepos/seed-agent/tests/test_agent_specific_examples.py`

## How To Use

Interactive default:

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

Fast non-interactive probe:

```bash
./scripts/seed-codex run \
  "Attach to examples/internet/B29_email_dns/output; only do read-only environment understanding." \
  --workspace-name z29_probe \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --policy read_only
```

Structured mission path:

```bash
./scripts/seed-codex mission list --baseline B29
```

Use the bundle README and `bundle.yaml` to decide which entry is appropriate.

Recommended BGP control-plane showcase order:

1. `Z12_a12_bgp_mixed_backend`
2. `Z13_a13_exabgp_control_plane`
3. `Z14_a14_bgp_event_looking_glass`

# Seed Agent Missions (Platform-Oriented OPS Tasks)

`examples/agent-missions` is the reusable mission pack for runtime SEED operations.
It is not a one-off teaching demo. The goal is platform enablement:

- task semantics live in YAML
- execution is driven by `seed_agent_task_*` APIs
- Codex is optional shell; Seed-Agent remains behavior core

Legacy showcase remains in `examples/agent-base`.

---

## Directory Layout

```text
examples/agent-missions/
├── tasks/          # mission specs (YAML contract)
├── playbooks/      # low-level fallback templates
├── dialogues/      # example multi-turn interactions
├── _common/        # API invocation helpers
└── run_task_demo.sh
```

---

## Mission Catalog (V1)

- Security
  - `SEC_B29_SOCIAL_ENGINEERING_TRIAGE`
  - `SEC_B29_DNS_MAIL_ABUSE_RESPONSE`
- Troubleshooting
  - `TS_B00_BGP_FLAP_ROOTCAUSE`
  - `TS_B29_MAIL_REACHABILITY_DEBUG`
- Research
  - `RS_B00_CONVERGENCE_COMPARISON`
  - `RS_B29_FAULT_IMPACT_ABLATION`

---

## Quick Run

Prerequisites:

- SeedOps MCP server is running
- Seed-Agent MCP server is running
- `SEED_AGENT_MCP_URL`, `SEED_AGENT_MCP_TOKEN` are set

List tasks:

```bash
./subrepos/seed-agent/scripts/seed-codex mission list
```

Start + execute one mission directly:

```bash
examples/agent-missions/run_task_demo.sh \
  --task TS_B00_BGP_FLAP_ROOTCAUSE \
  --objective "Locate BGP flap root cause and provide fix hints" \
  --attach-output-dir examples/internet/B00_mini_internet/output
```

Run risky mission with confirmation:

```bash
examples/agent-missions/run_task_demo.sh \
  --task RS_B29_FAULT_IMPACT_ABLATION \
  --objective "Run packet-loss impact ablation with rollback" \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

Outputs are written under `/tmp/seed-agent-mission-demo/<task_id>/<timestamp>/`.

---

## One-command review pack (for presentation)

Run a full review bundle (catalog + read-only mission + risk-gate mission + markdown report):

```bash
examples/agent-missions/run_review_pack.sh
```

Default output:

- `examples/agent-missions/reports/<timestamp>/review_summary.json`
- `examples/agent-missions/reports/<timestamp>/review_report.md`

This bundle is suitable for PR attachments and live demos.

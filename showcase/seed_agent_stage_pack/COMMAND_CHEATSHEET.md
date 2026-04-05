# Command Cheatsheet

## Start services

```bash
scripts/seed-codex up
scripts/seed-codex status
```

## Interactive mode

```bash
scripts/seed-codex ui
```

## Non-interactive plan

```bash
scripts/seed-codex plan "Attach to mcp-server/output_e2e_demo and summarize BGP health"
```

## Non-interactive run

```bash
scripts/seed-codex run "Attach to mcp-server/output_e2e_demo and refresh inventory, then collect health evidence"
```

## Controlled task with confirmation

```bash
examples/agent-missions/run_task_demo.sh \
  --task RS_B29_FAULT_IMPACT_ABLATION \
  --objective "Run controlled packet loss ablation with rollback" \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

## Six-class review pack

```bash
examples/agent-missions/run_review_pack.sh \
  --seedops-token "${SEED_MCP_TOKEN}" \
  --seedagent-token "${SEED_AGENT_MCP_TOKEN}"
```

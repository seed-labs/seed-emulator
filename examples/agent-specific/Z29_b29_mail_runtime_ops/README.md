# Z29: B29 Mail / DNS Runtime Ops

`Z29` is the main attached-runtime bundle for `examples/internet/B29_email_dns/output`.

This is the strongest current end-to-end runtime ops package in the repository.

## What It Is Good For

- mail reachability diagnosis
- DNS and mail log triage
- disturbance recovery with rollback
- bounded security investigation on visible SEED nodes

## Tool Path

Primary high-level path:

- `seed_agent_run`
- `seed_agent_plan`
- `seed_agent_task_*`

Preferred low-level ops:

- `inventory_list_nodes`
- `routing_protocol_summary`
- `ops_logs`
- `job_get`
- `job_steps_list`
- `artifacts_list`

## Task And Skill Fit

Mission tasks already aligned with `Z29`:

- `TS_B29_MAIL_REACHABILITY_DEBUG`
- `RS_B29_FAULT_IMPACT_ABLATION`
- `SEC_B29_DNS_MAIL_ABUSE_RESPONSE`
- `SEC_B29_SOCIAL_ENGINEERING_TRIAGE`

Key `skill_patterns`:

- `attach-and-scan`
- `service-debug`
- `fault-inject-and-rollback`
- `evidence-collection`

## Commands

Read-only probe:

```bash
./scripts/seed-codex run \
  "Attach to examples/internet/B29_email_dns/output; only do read-only environment understanding and mail/DNS anomaly triage." \
  --workspace-name z29_probe \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --policy read_only
```

Mission entry:

```bash
./scripts/seed-codex mission list --baseline B29
```

## Status

- live readiness: `go`
- default mainline attached-runtime service-ops bundle

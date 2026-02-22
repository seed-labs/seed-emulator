# S04 — B29 Packet-Loss Experiment (Controlled)

## Goal

Run a dynamic mail-network experiment on B29:

1. baseline mail log snapshot
2. controlled packet-loss injection
3. rollback and post-check
4. before/during/after log comparison

## Risk Gate

Experiment stage is blocked unless:

- `--risk on`
- `--confirm-token YES_RUN_DYNAMIC_FAULTS`

## Run

```bash
./examples/agent-base/S04_b29_packetloss_experiment/run.sh \
  --mode both \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

## Assertions

- valid status/job status for experiment + rollback
- before/during/after mail logs generated
- rollback contains reset evidence

## Outputs

Under `.../artifacts/S04_b29_packetloss_experiment/<timestamp>/`:

- `mail_logs.before.txt`
- `mail_logs.during.txt`
- `mail_logs.after.txt`
- `experiment_report.md`

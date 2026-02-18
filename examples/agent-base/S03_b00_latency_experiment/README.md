# S03 — B00 Latency Experiment (Controlled)

## Goal

Run a staged dynamic experiment on an already-running B00 network:

1. baseline observation (`read_only`)
2. controlled latency fault injection (`net_ops`)
3. rollback (`inject_fault reset`)

## Risk Gate

Experiment stage is blocked unless both are provided:

- `--risk on`
- `--confirm-token YES_RUN_DYNAMIC_FAULTS`

## Run

```bash
./examples/agent-base/S03_b00_latency_experiment/run.sh \
  --mode both \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

## Assertions

- gate blocks experiment stage when disabled
- experiment and rollback jobs finish with terminal statuses
- rollback evidence includes reset path

## Outputs

Under `.../artifacts/S03_b00_latency_experiment/<timestamp>/`:

- `baseline.json`
- `experiment.json`
- `rollback.json`
- `comparison.md`

# SEED K3s AI Evidence Manual

This document defines the evidence-reading order for AI helpers such as
`opencode`. The goal is simple: the AI must read the real evidence before
offering advice.

## 1. Read order

### Step 1: public manuals

Always start with:

- `docs/k8s_usage.md`
- `docs/k3s_runtime_architecture.md`

This tells the AI:

- which profiles are official,
- which actions are valid,
- which artifacts define success.

### Step 2: environment entry

Read:

- `output/assistant_entry/latest/summary.json`

This answers:

- is the cluster reachable,
- which inventory is active,
- what the current recommended next command is.

### Step 3: current profile summary

Read, in order:

- `output/profile_runs/<profile>/latest/validation/summary.json`
- `output/profile_runs/<profile>/latest/validation/diagnostics.json`
- `output/profile_runs/<profile>/latest/report/report.json`

This answers:

- pass or fail,
- failed stage,
- failure code,
- first evidence file,
- minimum retry command.

### Step 4: runtime evidence

If more detail is required, read:

- `placement_by_as.tsv`
- `protocol_health.json`
- `connectivity_matrix.tsv`
- `failure_injection_summary.json`
- `resource_summary.json`
- `relationship_graph.json`
- `network_attachment_matrix.tsv`
- `artifact_contract.json`

### Step 5: live cluster state

Only after the artifact files:

- `kubectl get pods -o wide`
- `kubectl get deploy -o wide`
- `kubectl get events --sort-by=.lastTimestamp`

## 2. Response rules

AI responses should follow this order:

1. state whether the run passed,
2. point to the first evidence file,
3. give one minimum next action,
4. then explain the reason.

Do not reverse that order.

## 3. Good prompt templates

### Current health

```text
Read docs/k8s_usage.md and output/assistant_entry/latest/summary.json.
Tell me whether the cluster is healthy and what one command I should run next.
```

### Failure triage

```text
Read output/profile_runs/real_topology_rr/latest/validation/diagnostics.json,
summary.json, and report/report.json.
Tell me the failed stage, first evidence file, and minimum retry command.
```

### Protocol confidence

```text
Read output/profile_runs/real_topology_rr_scale/latest/validation/protocol_health.json,
relationship_graph.json, and placement_by_as.tsv.
Tell me whether the current evidence proves the K8s run has real protocol and placement relationships.
```

## 4. What AI should not do

- do not answer from memory when the evidence exists,
- do not invent a new failure code when one already exists,
- do not treat “no terminal error” as proof of experiment readiness,
- do not force AI into the runtime path.

AI is an evidence reader and operator assistant, not a runtime dependency.

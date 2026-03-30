# SEED Emulator: Kubernetes and K3s Operator Guide

This guide describes the public K8s/K3s workflow for SEED Emulator.

The maintained operator path is explicit and staged:

```text
.py topology -> compile output -> build -> deploy/up -> start bird -> switch kernel -> verify -> observe -> report
```

The public entry stays the same:

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

Use `all` as a convenience command, not as the only way to understand the
system.

## 1. Start here

Before running a profile, load the repository environment and print the current
cluster state:

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_lab_entry_status.sh
```

That snapshot shows:

- the host OS,
- the K3s node OS matrix,
- the selected cluster inventory,
- the active `seedemu-*` namespaces still occupying the cluster,
- the registry path,
- the latest attempted run,
- the latest verified run,
- the latest accepted run.

If your KVM login key is different from your GitHub key, pin it explicitly
before you run any K3s action:

```bash
export SEED_K3S_SSH_KEY=~/.ssh/<kvm-private-key>
```

To verify the KVM path directly before a large run, use the same SSH settings
that the runtime scripts use:

```bash
python3 scripts/seed_k8s_ssh_probe.py \
  --user ubuntu \
  --key "${SEED_K3S_SSH_KEY:-~/.ssh/id_ed25519}" \
  --node seed-k3s-master=192.168.122.110 \
  --node seed-k3s-worker1=192.168.122.111 \
  --node seed-k3s-worker2=192.168.122.112 \
  --strict
```

If that probe fails, stop there and fix SSH first. The preflight stage now
records `ssh_access.json` and reports `SSH_ACCESS_FAILED` explicitly, instead of
letting an SSH problem look like a later Multus or registry problem.

## 2. Public actions

The runner actions are:

- `doctor`: preflight only
- `compile`: preflight + compile only
- `build`: build and distribute images from the latest compiled run
- `deploy`: apply the latest compiled manifests and wait for readiness
- `start`: backward-compatible alias for `deploy`
- `start-bird`: start `bird` only
- `start-kernel`: switch routers into the kernel-export stage
- `phase-start`: backward-compatible wrapper for the protocol-start stage
- `verify`: run placement, protocol, connectivity, and recovery checks
- `observe`: collect runtime evidence
- `report`: generate the normalized report
- `all`: `compile -> build -> deploy -> start-bird -> start-kernel -> verify -> observe -> report`

The documented primary path is staged:

```bash
scripts/seed_k8s_profile_runner.sh <profile> compile
scripts/seed_k8s_profile_runner.sh <profile> build
scripts/seed_k8s_profile_runner.sh <profile> deploy
scripts/seed_k8s_profile_runner.sh <profile> start-bird
scripts/seed_k8s_profile_runner.sh <profile> start-kernel
scripts/seed_k8s_profile_runner.sh <profile> verify
scripts/seed_k8s_profile_runner.sh <profile> observe
scripts/seed_k8s_profile_runner.sh <profile> report
```

## 3. Compose-style shortcuts

After `source scripts/env_seedemu.sh`, the following thin aliases are on
`PATH`:

- `k3sdoctor <profile>`
- `k3scompile <profile>`
- `k3sbuild <profile>`
- `k3sdeploy <profile>`
- `k3sup <profile>` (alias of `deploy`)
- `k3sstartbird <profile>`
- `k3skernel <profile>`
- `k3sphase <profile>`
- `k3sverify <profile>`
- `k3sobserve <profile>`
- `k3sreport <profile>`
- `k3sall <profile>`
- `k3scompare <profile>`
- `k3sdown <profile>`

Inspection shortcuts:

- `k3sps <profile>`
- `k3slogs <profile> <pod-or-selector>`
- `k3sexec <profile> <pod-or-selector> -- <command>`
- `k3stop <profile>`
- `k3sevents <profile>`

Each shortcut prints the underlying command before it runs.

## 4. Reference-cluster baseline

The tracked reference cluster is the 3-node K3s+KVM environment defined by
`configs/clusters/seedemu-k3s.yaml`.

On that reference cluster, the planner keeps multi-Pod AS placements off the
control-plane node whenever a worker still has room. The master stays available
for singleton workloads and control-plane services.

The tracked high-density scale inventory is `configs/clusters/seedemu-k3s-scale.yaml`.
It uses the same node list, but it raises the K3s pod-density settings for
`1078` and `1897` scale runs. Because the Pod CIDR shape changes, switching
from the reference inventory to the scale inventory requires a K3s recreate:

```bash
SEED_CLUSTER_INVENTORY=seedemu-k3s-scale \
SEED_K3S_FORCE_REINSTALL=true \
scripts/setup_k3s_cluster.sh
```

On the 3-node reference cluster, only one `214`-node real-topology namespace
fits cleanly at a time. Before switching between `real_topology_rr` and
`real_topology_rr_scale`, clean the previous namespace first:

```bash
k3sdown real_topology_rr
k3sdown real_topology_rr_scale
scripts/seed_lab_entry_status.sh
```

If entry status still shows a stale `seedemu-*` namespace in `Terminating`,
finish that cleanup before launching the next `214`-node run.

### `mini_internet`

```bash
k3sdoctor mini_internet
k3scompile mini_internet
k3sbuild mini_internet
k3sdeploy mini_internet
k3sstartbird mini_internet
k3skernel mini_internet
k3sverify mini_internet
k3sobserve mini_internet
k3sreport mini_internet
```

### `real_topology_rr`

```bash
export SEED_REAL_TOPOLOGY_DIR=~/lxl_topology/autocoder_test
export SEED_ASSIGNMENT_FILE="${SEED_REAL_TOPOLOGY_DIR}/assignment.pkl"
export SEED_TOPOLOGY_SIZE=214

k3scompile real_topology_rr
k3sbuild real_topology_rr
k3sdeploy real_topology_rr
k3sstartbird real_topology_rr
k3skernel real_topology_rr
k3sverify real_topology_rr
k3sreport real_topology_rr
```

### `real_topology_rr_scale`

`real_topology_rr_scale` is the large-scale profile. The public policy is:

- `214`: reference-cluster baseline
- `1078`: rehearsal and debugging waypoint
- `1897`: first official large-hardware scale target

Current maintained truth:

- `real_topology_rr_scale(214)` is the runtime-validated large-topology baseline
  on the 3-node reference cluster.
- This SSH hardening round does not change the topology logic of that example.
  It makes node access explicit, operator-visible, and easier to triage.

On the reference cluster, requests above the inventory limit return
`CAPACITY_GATED` instead of failing later in a less clear stage.

Reference-cluster baseline:

```bash
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

Large-hardware target:

```bash
SEED_CLUSTER_INVENTORY=seedemu-k3s-scale \
SEED_TOPOLOGY_SIZE=1897 \
scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

## 5. Historical Compose mapping

The K8s path keeps the same logical phases as the older Compose workflow, but
it exposes them more clearly:

| Historical flow | K8s/K3s flow |
|---|---|
| `python3 example.py` | `compile` |
| `docker compose build` | `build` |
| `docker compose up -d` | `deploy` |
| manual `start_bird0130.py` | `start-bird` |
| manual `start_bird_kernel.py` | `start-kernel` |
| manual log and connectivity checks | `verify` + `observe` + `report` |

## 6. Acceptance truth

`runner_status` and `acceptance_status` mean different things:

- `runner_status`: whether the requested action succeeded
- `acceptance_status`: overall lifecycle truth for the run

The accepted values are:

- `NOT_RUN`
- `PARTIAL`
- `PASS`
- `FAIL`
- `CAPACITY_GATED`

Examples:

- a successful `start-kernel` run is usually `runner_status=PASS`,
  `acceptance_status=PARTIAL`
- a successful `verify` + `report` run with all required evidence is
  `acceptance_status=PASS`
- an oversized scale request on the reference cluster is
  `acceptance_status=CAPACITY_GATED`

## 7. Evidence-first verification

A run is not ready for experiment just because Pods exist. Check these files
first:

1. `output/profile_runs/<profile>/latest/validation/summary.json`
2. `output/profile_runs/<profile>/latest/validation/start_bird_summary.json`
3. `output/profile_runs/<profile>/latest/validation/start_kernel_summary.json`
4. `output/profile_runs/<profile>/latest/validation/protocol_health.json`
5. `output/profile_runs/<profile>/latest/validation/placement_by_as.tsv`
6. `output/profile_runs/<profile>/latest/report/report.json`

If you need K8s parity evidence for workload relationships, open:

- `placement_by_as.tsv`
- `network_attachment_matrix.tsv`
- `relationship_graph.json`

## 8. Acceptance harness

The public acceptance entry is:

```bash
scripts/seed_k8s_acceptance.sh <suite>
```

Supported suites:

- `docs`
- `unit`
- `compile-all`
- `tier1-runtime`
- `tier2-runtime`
- `all`

## 9. Troubleshooting rules

- If `doctor` fails, stop and fix the environment first.
- If `build` fails, inspect image-distribution evidence before retrying.
- If `deploy` fails, inspect `apply.log`, `wait.log`, and namespace events.
- If `start-bird` fails, inspect `start_bird.log` and `start_bird_summary.json`.
- If `start-kernel` fails, inspect `start_kernel.log` and `start_kernel_summary.json`.
- If `verify` fails, inspect `diagnostics.json`, `protocol_health.json`,
  `connectivity_matrix.tsv`, and `report/report.json`.

## 10. Optional AI helper

The system does not require AI to operate. If you want the repository-tracked
helper flow, see `docs/runbooks/opencode_seed_lab_quickstart.md`.

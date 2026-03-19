# SEED K3s Long-Term Delivery Roadmap

This roadmap explains how the K8s/K3s subsystem grows from the current reference
cluster baseline into a broader multi-server delivery.

## 1. Current baseline

The current delivery baseline is:

- `mini_internet`
- `real_topology_rr(214)`
- `real_topology_rr_scale(214)`

These runs are the truth for the reference 3-node K3s+KVM cluster.

## 2. Immediate follow-up after this delivery

### Wave 1: promote more operator-facing profiles

- `transit_as`
- `mini_internet_viz`

Goal:

- move them from capability-gated support toward stricter runtime evidence,
- keep the same operator entry and artifact contract.

### Wave 2: promote another network baseline

- `k8s_nano_internet.py`

Goal:

- expand the compile-only backlog with one more clean runtime candidate before
  touching the more experimental demos.

## 3. Large-scale roadmap

The large real-topology milestone remains official:

- `SEED_TOPOLOGY_SIZE=1897` / `1899` style runs

But the hardware story is explicit:

- the reference cluster validates `214`,
- larger sizes are capacity-gated on that cluster,
- larger hardware or multi-server inventories are required for full runtime
  acceptance.

The workflow should stay the same when hardware changes:

```bash
scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

Only the cluster inventory and hardware class should change.

## 4. Multi-server direction

The next infrastructure step is inventory-driven multi-server support:

- more cluster inventory files under `configs/clusters/`
- the same runner and acceptance harness
- the same artifact contract

The rule is: change inventory, not workflow shape.

## 5. Example-library migration

The long-term goal is not three profiles forever. It is a larger library of
promoted examples with shared rules:

- stable compile entry,
- public profile metadata when operator-facing,
- artifact contract,
- acceptance coverage.

## 6. Observation and showcase

Observation remains important, but it stays downstream of evidence:

- `showcase` is optional,
- `kubectl` and artifact files remain the source of truth,
- any future UI must point back to evidence files and live cluster state.

## 7. AI and agent integration

AI remains optional and outside the runtime dependency chain.

Future AI work should focus on:

- evidence reading,
- operator assistance,
- migration acceleration,
- documentation maintenance,
- cluster triage.

The runtime path must continue to work without AI.

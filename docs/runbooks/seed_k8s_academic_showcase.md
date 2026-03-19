# SEED K8s Showcase and Observation Guide

This document explains how to use the optional showcase layer without confusing
it with the acceptance path.

## 1. Showcase is not the verdict

The showcase is an observation layer. It does not define PASS/FAIL.

The verdict always comes from:

- `validation/summary.json`
- `validation/protocol_health.json`
- `validation/placement_by_as.tsv`
- `report/report.json`

## 2. Where showcase fits

The runtime order is:

```text
doctor -> build -> start -> phase-start -> verify -> observe -> report -> showcase (optional)
```

The showcase should only consume:

- stable run artifacts,
- live `kubectl` state,
- optional live pod probes.

## 3. Start the showcase

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_k8s_profile_runner.sh real_topology_rr showcase
```

Or:

```bash
scripts/seed_k8s_showcase.sh real_topology_rr
```

## 4. What to show first

If you are demonstrating the system live, show evidence before graphics:

1. `summary.json`
2. `protocol_health.json`
3. `placement_by_as.tsv`
4. `relationship_graph.json`
5. only then the live showcase view

That keeps the demonstration grounded in real state.

## 5. Good live probes

The most convincing live checks are:

- `k3sps <profile>`
- `k3stop <profile>`
- `k3sevents <profile>`
- `k3sexec <profile> <pod> -- birdc show protocols`

## 6. What this document is for

Use this guide when you want:

- a clean observation path,
- a teaching/demo workflow,
- a visual companion to the evidence contract.

Do not use it as a substitute for `verify` or `report`.

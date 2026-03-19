# Migrating Examples to K8s/K3s

This document is for maintainers who want to move more SEED examples into the
K8s/K3s subsystem without breaking the existing Docker or Compose workflows.

## 1. Definition of Done

An example is considered migrated only when it has all of the following:

1. a stable Kubernetes compile entry,
2. a documented support tier,
3. an acceptance path,
4. an evidence contract appropriate for that tier.

“It compiled once” is not enough for a promoted runtime example.

## 2. Three migration states

### Compile-only

Requirements:

- script compiles,
- `k8s.yaml` exists,
- `build_images.sh` exists.

### Tier-2 capability-gated runtime

Requirements:

- operator-facing profile (if public),
- documented runtime path,
- runtime evidence artifacts,
- acceptable capability-gated outcome if the reference cluster lacks a feature.

### Tier-1 runtime-validated

Requirements:

- stable runtime acceptance on the reference cluster,
- full validation artifact contract,
- public operator documentation,
- no ambiguity about PASS/FAIL.

## 3. Recommended structure

Avoid copying full topology logic into two unrelated scripts.

Prefer:

1. a topology-building function,
2. a Docker/Compose compile entry,
3. a Kubernetes compile entry.

That keeps the topology definition stable while letting the compiler-specific
wrapper differ.

## 4. Required public integration points

When a migrated example becomes operator-facing, update:

- `examples/kubernetes/README.md`
- `configs/seed_k8s_profiles.yaml` (if profile-backed)
- `docs/k8s_usage.md`

If the example is still compile-only, document it in the support matrix but do
not promote it into the public runtime baseline.

## 5. Acceptance expectations by tier

### Compile-only

- included in `scripts/seed_k8s_acceptance.sh compile-all`

### Tier-2

- included in `scripts/seed_k8s_acceptance.sh tier2-runtime`

### Tier-1

- included in `scripts/seed_k8s_acceptance.sh tier1-runtime`

## 6. Evidence requirements

Tier-1 public profiles must keep the full validation contract stable:

- `summary.json`
- `placement_by_as.tsv`
- `protocol_health.json`
- `connectivity_matrix.tsv`
- `convergence_timeline.json`
- `failure_injection_summary.json`
- `resource_summary.json`
- `relationship_graph.json`
- `network_attachment_matrix.tsv`

Tier-2 profiles may be capability-gated, but they still need a coherent report
and a documented runtime result.

## 7. Promotion checklist

Before promoting an example to a higher tier, verify:

- docs are public and English,
- no private notes are needed to operate it,
- shortcut/operator commands are clear,
- evidence files are stable,
- acceptance harness covers the intended tier.

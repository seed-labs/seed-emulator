# SEED K8s Optional `opencode` Quickstart

This document is intentionally narrow: it explains how to use the repository's
optional `opencode` helpers when working with the K8s/K3s workflow.

`opencode` is **not required** to run the SEED K8s subsystem. The authoritative
manuals remain:

- Operator workflow: `docs/k8s_usage.md`
- Maintainer workflow: `docs/k3s_runtime_architecture.md`
- AI evidence order: `docs/runbooks/seed_k3s_ai_evidence_manual.md`

## 1. What is tracked in the repository

The repository only tracks the minimal `.opencode` assets needed to explain how
to use the SEED K8s helpers:

- agent definitions
- command wrappers
- skill descriptions

Local package state, generated assets, and private notes must stay out of git.

## 2. Install and activate

Install `opencode` using its official instructions, then prepare the SEED K8s
environment:

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_lab_entry_status.sh
```

The `entry_status` step is the recommended first command for both humans and
AI helpers. It tells you:

- which cluster inventory is active,
- which profile is currently selected,
- where the latest evidence lives,
- what the next recommended command is.

## 3. Repository-local workflow

The tracked `.opencode` setup assumes:

- repo-root relative paths,
- the profile runner as the single execution entry,
- evidence-first answers instead of speculative advice.

The main operator entry remains:

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

## 4. Recommended prompt style

Ask for evidence first, then action. Good examples:

```text
Read docs/k8s_usage.md and output/assistant_entry/latest/summary.json.
Tell me whether the reference cluster is healthy and what one command I should run next.
```

```text
Read output/profile_runs/mini_internet/latest/validation/summary.json and diagnostics.json.
Tell me the failed stage, the first evidence file, and the minimum retry command.
```

```text
Read output/profile_runs/real_topology_rr_scale/latest/report/report.json.
Tell me whether the current 214 run passed, what the pipeline duration was, and which evidence file best proves K8s placement by AS.
```

## 5. Recommended command families

When the user wants execution, prefer the profile runner or the `k3s*`
shortcuts:

- `k3sdoctor <profile>`
- `k3sbuild <profile>`
- `k3sup <profile>`
- `k3sphase <profile>`
- `k3sverify <profile>`
- `k3sobserve <profile>`
- `k3sreport <profile>`
- `k3sall <profile>`

These shortcuts are thin aliases. They print the real command they map to
before executing it.

## 6. What not to do

Do not treat AI as part of the runtime path.

The correct order is:

1. make the non-AI workflow work,
2. make the evidence files stable,
3. let `opencode` help people read the evidence and choose the next action.

That keeps the K8s subsystem usable even for operators who never touch AI.

---
name: seedemu-capability-refresh
description: Use before any SeedEmu paper-search or paper-fit assessment to inspect the local SeedEmu repository, refresh the SeedEmu capability map, and update ../../knowledge/capability-map.md with current services, layers, examples, deployment modes, limitations, and evidence paths.
---

# SeedEmu Capability Refresh

## Purpose

Refresh the local SeedEmu capability map before paper research. The goal is to
avoid judging papers against stale assumptions while keeping the context compact
enough to read every round.

## Required Inputs

- Toolkit root: `tools/seed-agent`
- SeedEmu repository root: the directory holding `seedemu/`, `examples/`, and `tools/`
- Capability cache: `../../knowledge/capability-map.md`

## When To Run

Run this workflow before every paper-search task and before any high-confidence
paper feasibility claim. Do not rely only on the existing context file when the
user is asking for paper discovery, paper ranking, or a SeedEmu reproduction
blueprint.

## Refresh Workflow

1. Read `../../knowledge/capability-map.md` to understand the current capability map.
2. Inspect the repository at a high level:
   - list top-level directories;
   - list docs, examples, services, layers, components, compilers, tests, and tool directories;
   - check local changes that may add or modify capabilities.
3. Read high-signal files first:
   - `README.md`;
   - `docs/user_manual/`;
   - `docs/developer_manual/`;
   - `docs/designs/`;
   - `examples/`;
   - `tests/`;
   - `seedemu/layers/`;
   - `seedemu/services/`;
   - `seedemu/components/`;
   - `seedemu/compiler/`;
   - `tools/DemoSystem/`;
   - `tools/InternetMap*`.
4. Compare repository evidence with the current context:
   - new capability, service, layer, compiler, component, example, or demo;
   - changed support status;
   - missing limitation;
   - stale path;
   - weak or overbroad evidence;
   - capability that matters for the current paper-search theme.
5. Update `../../knowledge/capability-map.md` when the refresh finds material changes or
   missing evidence. Keep entries concise and evidence-backed.
6. If no material update is needed, keep the file unchanged and mention the
   refresh result in the paper-search response or research state.

## Evidence Requirements

Every capability entry added or changed in `../../knowledge/capability-map.md` should
include:

- category;
- support status: `existing`, `light top-layer development`, `substantial development`, or `poor fit`;
- short summary;
- tags useful for paper matching;
- examples, demos, docs, tests, or source paths;
- concise evidence snippets or close paraphrases;
- limitations.

Prefer specific repository paths over general claims. A capability is not
`existing` unless the repository contains a service, layer, component, example,
demo, test, or documentation that supports it.

## Search Patterns

Use these patterns when inspecting the repository:

- capability inventory: file names under `examples/`, `seedemu/services/`, `seedemu/layers/`, `seedemu/components/`, and `seedemu/compiler/`;
- routing and Internet: `BGP`, `Routing`, `AutonomousSystem`, `InternetExchange`, `RouteServer`, `hijack`;
- infrastructure: `DNS`, `DNSSEC`, `CA`, `PKI`, `HTTPS`, `Kubo`, `Tor`, `CDN`, `Email`;
- security: `Botnet`, `Morris`, `Mirai`, `DDoS`, `attack`, `attacker`;
- measurement: `Traffic`, `iperf`, `D-ITG`, `Scapy`, `log`, `metric`;
- blockchain: `Ethereum`, `PoA`, `PoW`, `PoS`, `Chainlink`, `Monero`, `validator`, `oracle`;
- future Internet: `SCION`, `ISD`, `path`, `bwtest`;
- deployment: `Docker`, `Distributed`, `GCP`, `Terraform`, `OpenVPN`, `hybrid`, `Graphviz`.

## Update Style

Edit the context as a compact capability map, not a full repository manual.

Do:

- group related capabilities;
- keep snippets short;
- include limitations and fidelity caveats;
- add paper-matching tags;
- update paths when examples move.

Avoid:

- copying long documentation passages;
- recording implementation internals that do not help paper matching;
- turning one example into a broad unsupported claim;
- adding generated caches, scripts, package metadata, or runtime code.

## Handoff To Paper Search

After refreshing, paper search should use the updated context as SeedEmu-side
evidence. If a paper depends on a capability not covered by the context, inspect
the repository again and update the context before promoting the paper to a
strong recommendation.

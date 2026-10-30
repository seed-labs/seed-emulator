# Paper-Fit Guide

Paper-reproduction matching heuristics for the paper-researcher agent. This builds on the
capability inventory in [`../../knowledge/capability-map.md`](../../knowledge/capability-map.md):
that file says *what SEED-Emulator can do*; this file says *how to judge whether a given paper
can be reproduced/strengthened with it*.

Use together with [`AGENTS.md`](AGENTS.md) and the
[`seedemu-paper-search`](../../skills/seedemu-paper-search/SKILL.md) skill.

## Common Matching Heuristics

- BGP/routing papers: look for multi-AS topology, route leaks, hijacks, reachability, policy, convergence, and measurement.
- DNS/PKI papers: look for resolver behavior, certificate issuance, HTTPS, ACME, DNS hierarchy, reverse DNS, and DNSSEC.
- Security attack papers: prefer isolated botnet, worm, DDoS, malware-spread, or routing-attack reproduction.
- Measurement papers: map traffic generators, topology control, logs, visualization, and repeatability.
- Blockchain papers: map Ethereum/PoS/validators/transactions/oracles/Monero to blockchain services plus traffic control.
- Future Internet papers: map SCION/ISD/path-aware routing/coexistence to SCION examples and services.
- Hybrid or large-scale papers: consider Docker/distributed/GCP/hybrid access as deployment support, but note scale limits.

## Paper Matching Guide

Use this guide to decide whether a paper deserves deeper inspection.

### Internet routing, BGP, and topology papers

Strong signals:

- experiments need multiple ASes, IXes, transit/customer/peer relationships, route servers, or controlled policy changes;
- the paper studies route leaks, hijacks, path selection, convergence, reachability, or interdomain failure;
- real Internet deployment would be disruptive, unethical, expensive, or impossible to repeat exactly.

SeedEmu value:

- encode the AS graph and policy in a reproducible topology;
- replay routing incidents safely;
- vary topology, relationship, prefix, and policy parameters;
- collect path and reachability evidence without touching public routing.

Typical development:

- scenario code for the paper topology;
- topology or relationship importer if the paper uses CAIDA-style datasets;
- log parsers for BGP tables, traceroute-like reachability, and convergence timing.

### DNS, PKI, naming, and trust-infrastructure papers

Strong signals:

- experiments depend on DNS hierarchy, recursive resolver behavior, DNSSEC, certificate issuance, HTTPS, ACME-like flows, or CA trust stores;
- the paper needs a controlled namespace or certificate ecosystem;
- public deployment would require privileged access to real infrastructure.

SeedEmu value:

- create a closed root, TLD, authoritative, resolver, CA, and HTTPS environment;
- repeat trust, naming, and certificate experiments without relying on public CAs or domains;
- combine DNS/PKI behavior with routing, traffic, or attacker-controlled ASes.

Typical development:

- paper-specific zone files, certificate policies, resolver configuration, or workload clients;
- parsers for DNS logs, certificate events, latency, and failure modes;
- simplified models for public-ecosystem features such as CT if exact fidelity is not required.

### Traffic, measurement, congestion, and performance papers

Strong signals:

- experiments need controlled traffic matrices, latency, throughput, packet loss, congestion, or topology changes;
- the paper compares measurement methods under repeatable network conditions;
- public Internet measurements are noisy, expensive, rate-limited, or ethically constrained.

SeedEmu value:

- generate repeatable TCP, UDP, D-ITG, iPerf, Scapy, or custom traffic;
- control topology and service placement;
- collect logs from every emulated host;
- scale the scenario until bounded by local or distributed Docker resources.

Typical development:

- workload driver scripts;
- traffic-matrix generator;
- measurement collectors and log parsers;
- notebooks or dashboards for reproducing paper plots.

### Security, malware, botnet, DDoS, worm, and incident papers

Strong signals:

- the paper studies attack propagation, C2 structure, DDoS behavior, defensive measurement, routing attack impact, or security controls;
- the original experiment cannot be run safely on public networks;
- the paper's value comes from controlled observation rather than real victim interaction.

SeedEmu value:

- keep all activity inside a closed emulation environment;
- reproduce network roles such as bots, victims, C2, scanners, defenders, and measurement nodes;
- vary topology and defenses repeatedly;
- demonstrate why emulation is safer than live experimentation.

Typical development:

- sanitized workload or benign attack-behavior model;
- defense instrumentation;
- event logs for spread, command delivery, traffic volume, and mitigation;
- explicit safety boundary in all reports.

### Overlay, application-layer, CDN, email, Tor, and IPFS papers

Strong signals:

- experiments depend on overlay node placement, path diversity, content distribution, routing around failures, anonymity infrastructure, or application-layer naming;
- the paper can be evaluated with controlled clients and servers rather than Internet-scale user populations.

SeedEmu value:

- combine overlay services with controlled underlay topology;
- observe how routing, latency, policy, or failures affect application behavior;
- reproduce service deployment without depending on external public infrastructure.

Typical development:

- service-specific configuration templates;
- client workload scripts;
- content placement or request-trace generator;
- parsers for overlay path, cache hit, delivery latency, or failure metrics.

### Blockchain, oracle, and distributed-ledger papers

Strong signals:

- experiments study validator placement, consensus behavior, network partitions, transaction propagation, oracle interactions, peer topology, or cross-layer network effects;
- public-chain experiments are costly, slow, risky, or impossible to control.

SeedEmu value:

- run private Ethereum, Chainlink, Monero, and related service networks;
- vary network topology, delay, failure, and validator/client placement;
- collect chain, transaction, node, and oracle logs in a reproducible setting.

Typical development:

- smart contracts or oracle adapters;
- workload generators for transactions and queries;
- parsers for block time, fork behavior, finality, propagation delay, and oracle correctness.

### SCION, path-aware networking, and future-Internet papers

Strong signals:

- experiments need ISDs, path-aware routing, SCION/BGP coexistence, policy experiments, or bandwidth tests;
- the paper benefits from repeatable path and topology control.

SeedEmu value:

- build SCION ISDs and ASes;
- compare SCION and BGP behavior in a controlled mixed topology;
- run bandwidth and path experiments without deploying a real future-Internet testbed.

Typical development:

- paper-specific ISD/AS topology;
- path-selection workloads;
- measurement scripts for path, throughput, failover, and coexistence behavior.

### Deployment, visualization, and artifact-evaluation papers

Strong signals:

- the paper needs a reusable testbed, visual topology demonstration, teaching artifact, cloud/distributed deployment, or hybrid physical-device participation;
- the experiment would be valuable as an artifact-evaluation environment even if the paper did not originally use emulation.

SeedEmu value:

- compile to Docker or distributed/cloud variants;
- expose topology and service behavior visually;
- package experiments as repeatable demonstrations.

Typical development:

- reproducible scenario packaging;
- dashboards and plot scripts;
- artifact README and validation commands;
- optional distributed deployment configuration.

## Small Top-Layer Development Examples

These additions usually do not require changing SeedEmu core behavior and are
good candidates for `light top-layer development`:

- paper-specific scenario builder that instantiates ASes, IXes, hosts, routers, services, and policies;
- topology importer for CAIDA, PeeringDB-like, artifact-provided, or paper-provided graphs;
- workload driver for clients, bots, validators, resolvers, crawlers, or measurement nodes;
- traffic matrix generator for throughput, latency, congestion, flash-crowd, or DDoS-like closed-lab workloads;
- sanitized attack-behavior model that preserves network observables without real-world exploit steps;
- custom container image for a paper artifact, service prototype, or measurement tool;
- configuration generator for DNS zones, certificates, BGP policies, SCION ISDs, overlay nodes, or blockchain validators;
- log collector and parser for BGP tables, service logs, traffic measurements, DNS queries, chain events, or overlay behavior;
- validation notebook or plotting script that recreates selected figures;
- dashboard or Internet-map adapter that makes the demonstration easier to inspect.

Classify work as `substantial development` when it requires a new SeedEmu
service, layer, component, compiler behavior, protocol model, or deep change to
runtime assumptions.

## Poor-Fit Signals

Downgrade or reject papers when the core experiment depends mainly on:

- pure theory, proof, or analysis with no networked experimental behavior;
- ML model quality where the network environment is incidental;
- hardware-only behavior such as radio, ASIC, NIC, switch silicon, sensor, or physical-layer properties;
- proprietary production data that cannot be replaced by a meaningful synthetic workload;
- closed commercial infrastructure whose behavior cannot be approximated;
- human-subject behavior that is central to the result and not safely reproducible;
- real-world exploitation, victim interaction, or public-network attack activity that cannot be reframed as safe closed emulation;
- a single local program benchmark where SeedEmu topology, services, or deployment do not add value.

## Output Expectations

For each recommended paper, produce:

1. Fit summary.
2. Paper evidence.
3. SeedEmu evidence with paths from this document or direct repo inspection.
4. Reproducibility level: existing, light top-layer development, substantial development, or poor fit.
5. Experiment blueprint: topology, SeedEmu capabilities, metrics, services or orchestration to add, and validation plan.
6. Value argument: cost, safety, repeatability, scale, or ethics advantage.

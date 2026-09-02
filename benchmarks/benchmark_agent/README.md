# Benchmark Agent

<!-- README_SYNC_REQUIRED: Any code or interface change here must update this README and benchmarks/README.md. -->

Benchmark Agent owns natural-language planning, benchmark fault meaning, capability verification, Scenario compilation, qualification, candidate policy, evidence, and scoring. Tool Service supplies only topology facts and deterministic operations.

## Planning flow

```text
Python script or runtime project
→ Tool Service TopologyFacts
→ LLM FaultCapabilityProposal + requested read-only probes
→ fixed runtime.service_capabilities evidence
→ benchmark-owned semantic FaultDriver
→ verified FaultCapabilityBinding
→ target-level capability_catalog / available_faults
→ deterministic Scenario
```

`available_faults` exists only in the Benchmark Agent capability catalog. The LLM proposal has no tool names or execution authority. A Binding fixes target, topology and evidence fingerprints, baseline, generic injection/recovery operations, and candidate actions. Runtime execution repeats capability evidence checks before injection and rejects lost capabilities.

## Modules

- `nl.py`: topology facts, strict Proposal schema, provider call, evidence collection, audit persistence, and Scenario compilation;
- `faults/`: four semantic drivers (`container_stopped`, `dns_resolver_failure`, `firewall_drop`, `netem_delay`) and capability registry;
- `control.py`: Benchmark-owned session and candidate grant contracts;
- `scenario.py`: strict executable Scenario including its verified Binding;
- `workflow.py`: topology lifecycle, drift gate, qualification, Adapter evaluation, recovery, evidence, and scoring;
- `benchmark_adapter/`: authoritative candidate action allowlist and budget boundary.

Every executable scenario carries a verified `FaultCapabilityBinding` and uses `operation.*` Tool Service calls. Session contracts, target/inventory fingerprints, candidate grants, recovery planning, and audit evidence are created by Benchmark Agent; Candidate Adapter enforces the candidate grant. No Tool Service grant token is issued.

```bash
PYTHONPATH=benchmarks python3 -m benchmark_agent.cli nl-plan \
  --text "在指定拓扑设计一个可恢复故障" \
  --topology /absolute/path/topology.py --provider mimo

PYTHONPATH=benchmarks python3 -m benchmark_agent.cli nl-runtime-plan \
  --text "在运行中的拓扑设计一个可恢复故障" \
  --project <compose-project> --provider mimo

PYTHONPATH=benchmarks python3 -m benchmark_agent.cli run \
  --scenario /absolute/path/scenario.json --api-url http://127.0.0.1:8000
```

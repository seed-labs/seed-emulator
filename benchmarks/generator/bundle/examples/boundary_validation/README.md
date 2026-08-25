<!-- README_SYNC_REQUIRED -->

# Remaining-boundary Bundle examples

This directory contains executable `BenchmarkRequest v1` fixtures for the
fault boundaries that were previously available only to scenario-specific
code. Every request uses the declarative `bundle_boundary_validation`
topology, runs the real no-AI Docker lifecycle, requests two independent
qualification rounds, and disables publishing.

| Request | FaultDriver boundary |
|---|---|
| `boundary_ipv6_bundle.json` | `network.ipv6.connected_route_removed` |
| `boundary_ospf_bundle.json` | `routing.bird.ospf_wrong_area` |
| `boundary_docker_network_bundle.json` | `docker.network.disconnected` |
| `boundary_software_config_bundle.json` | `software.config.replace` |
| `boundary_software_executable_bundle.json` | `software.executable.disabled` |
| `boundary_cascading_compound_bundle.json` | DNS → BIRD OSPF area → software config cascading set |

From `benchmarks/`, a single request can be run with:

```bash
python3 -m generator.bundle.cli generate \
  --request generator/bundle/examples/boundary_validation/boundary_ipv6_bundle.json \
  --workspace reports/boundary_ipv6_bundle
```

The topology's Compose project must already be running when
`prepare_topology=false`. Each execution writes lifecycle receipts, quality
results, scale validation, and formal qualification evidence to its workspace.

> **README_SYNC_REQUIRED:** Any agent changing a request in this directory
> must update this README and the parent `examples/README.md`,
> `bundle/README.md`, and `generator/README.md` in the same change.

The cascading fixture intentionally declares one application and three faults.
It proves that composition is bounded by capabilities and resource conflicts,
not by application count. Its compiled impact evidence must contain two
dependency edges and an exact reverse recovery order.

# Fault Injection Platform v1

The benchmark generator now separates fault meaning from execution technology.
Every new fault is a strict `FaultSpec` compiled against a topology capability
manifest before any mutation is allowed.

## Flow

```text
declarative scenario -> topology compiler -> capability manifest
          FaultSpec v1 -> fault compiler -> immutable signed plan
                                      -> snapshot/journal
                                      -> inject -> prove active
                                      -> observe/score
                                      -> reverse recovery -> prove healthy
```

The compiler resolves selectors, calculates the affected assets and ASNs,
enforces impact budgets and protected assets, detects exclusive resource-lock
conflicts, validates dependency order, and fingerprints the exact execution
plan. A changed target, command, safety expectation or topology changes the
fingerprint.

## Plugins

`FaultDriver` is the only backend extension point. The first production set is:

| Fault type | Backend | Scope |
| --- | --- | --- |
| `container.stopped` | Docker lifecycle | one container |
| `dns.nameserver` | container filesystem | `/etc/resolv.conf` |
| `routing.bird.wrong_asn` | BIRD configuration | one ASN declaration |
| `network.acl.scoped` | iptables | one source/destination ICMP flow |
| `network.netem` | tc/netem | one container interface |

Netem accepts bounded `delay_ms`, `jitter_ms`, `loss_percent`, and
`rate_kbit`. Jitter requires a non-zero delay. The compiler rejects an empty
impairment.

## Durable execution and recovery

Before each action, the executor captures a bounded snapshot and atomically
writes a journal. It persists `inject_started` before running the mutation, so
an interrupted command is conservatively recovered. Partial injection is
compensated in reverse order. Repeated recovery is safe, and a new execution
first recovers an unfinished journal with the same execution identity.

Runtime journals live under `benchmarks/generated/fault-journal/` and are
evidence, not scenario inputs. They must not contain credentials or full secret
configuration.

## Composition and coverage

Compound faults are ordinary sets of primitive `FaultSpec` objects. The generic
compiler orders dependencies and cleanup and rejects overlapping resource
locks. The automatic selector greedily adds driver diversity, AS coverage,
asset coverage and unseen driver-pair signatures, with deterministic seed-based
tie breaking.

Coverage reports include these four dimensions separately and a weighted total.
Low asset coverage is expected for sampled 10,000-node validation; AS coverage,
driver diversity and selected critical paths are the scaling signals.

## Commands

```bash
PYTHONPATH=benchmarks python3 -m generator.faults.cli compile \
  --spec faults.json --capabilities topology_manifest.json \
  --relationship independent --output plan.json

PYTHONPATH=benchmarks python3 -m generator.faults.cli inject \
  --plan plan.json --execution-id run-001 --journal-dir journal

PYTHONPATH=benchmarks python3 -m generator.faults.cli recover \
  --plan plan.json --execution-id run-001 --journal-dir journal
```

Large topologies are validated without launching all containers:

```bash
PYTHONPATH=benchmarks python3 -m generator.faults.scale_validation \
  --topology-id scale_1000 --topology-id scale_10000 --samples 64 \
  --output benchmarks/reports/FAULT_PLATFORM_SCALE_VALIDATION.json
```

The 100-node gate is a real SEED/Docker smoke followed by real fault lifecycles.
On 2026-08-13, the first unthrottled 100-node start saturated dockerd on the
8-vCPU/16-GB development VM. This result is a failed gate, not a pass. The
smoke launcher now ramps assets in batches of four and the automatic runtime
preflight ceiling is temporarily 64 containers until a clean throttled rerun
proves the higher scale safe.
The 1,000/10,000-node gates compile real capability inventories, then benchmark
deterministic planning and bounded sampling. Resource preflight remains
fail-closed on hosts that cannot safely launch those scales.

Latest local evidence is written to the ignored report directory as
`FAULT_PLATFORM_SCALE_VALIDATION.json` and
`FAULT_PLATFORM_SCALE100_FAILED_GATE.json`. These are run-specific artifacts;
promotion must use fresh signed lifecycle evidence after the 100-node gate is
clean.

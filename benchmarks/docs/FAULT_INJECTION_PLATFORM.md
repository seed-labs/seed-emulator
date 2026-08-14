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
The first unthrottled 2026-08-13 attempt saturated dockerd on the 8-vCPU/16-GB
development VM. The final 2026-08-14 launcher uses batches of four, waits for
two stable CPU/memory/daemon samples, skips already-running services after a
restart, and retries bounded Docker API/runtime transients. The clean rerun
passed with 100 assets and 102 Compose services: all four ASes had two
Established BGP sessions, every IX/local edge and six cross-AS probes passed,
and all six fault lifecycles (the four migrated drivers, generic BIRD+ACL
composition, and netem) recovered. All six durable journals ended in
`recovered`. The validated automatic runtime ceiling is now 128 containers;
larger scales remain plan-only until separately promoted.

The 1,000/10,000-node gates compile real capability inventories, then benchmark
64 deterministic samples and bounded coverage without launching containers.
Planning performance uses process CPU time, with repeated calibration when the
VM clock cannot resolve a short batch; reports state the clock and repetition
count. Resource preflight remains fail-closed on hosts that cannot safely launch
those scales.

Latest evidence is stored in:

- `TOPOLOGY_SCALE_100_SMOKE.json`
- `GENERATOR_FAULT_PLATFORM_SCALE100_PILOT_LIFECYCLE_BATCH_0000.md`
- `FAULT_PLATFORM_SCALE_1000_VALIDATION.json`
- `FAULT_PLATFORM_SCALE_10000_VALIDATION.json`

The failed-gate report is retained only as historical diagnostic evidence and
must not be treated as the current admission decision.

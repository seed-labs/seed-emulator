# Benchmark Generator Agent

`generator.agent` creates deterministic benchmark suites while preserving the
existing `BaseScenario`, scenario registry, unified CLI, blind prompt, repair
authorization, independent verification, cleanup, and reporting contracts.

Run the commands below from the repository's `benchmarks/` directory.

## Safety model

- Only audited templates can create scenario commands.
- Every scenario has a semantic fingerprint; duplicates are rejected.
- Targets and parameters are selected from explicit capability inventories.
- Generated scenarios are quarantined from the main score until live validation.
- Manifests are written atomically under `benchmarks/specs/` only.
- A manifest records the hash of the benchmark interfaces it was generated for.
  Contract drift makes an enabled suite fail closed until it is regenerated.
- The generator never reads or writes credentials.

## Commands

Inspect the supported contracts and templates:

```bash
python3 -m generator.agent inventory
```

Preview a deterministic suite without writing files:

```bash
python3 -m generator.agent preview \
  --suite-id b00_scale_001 --count 100 --seed 20260809
```

Generate an enabled suite:

```bash
python3 -m generator.agent generate \
  --suite-id b00_scale_001 --count 100 --seed 20260809
```

Validate it against the current interface contract:

```bash
python3 -m generator.agent validate --suite-id b00_scale_001
python3 benchmark_cli.py --list
```

Plan topology-local execution batches without changing Docker state:

```bash
python3 -m generator.agent run-lifecycle \
  --suite-id b00_scale_001 --batch-size 20 --dry-run
```

Run the batches serially and resume from a known batch when needed:

```bash
python3 -m generator.agent run-lifecycle \
  --suite-id b00_scale_001 --batch-size 20 --reuse-running

python3 -m generator.agent run-lifecycle \
  --suite-id b00_scale_001 --batch-size 20 --start-batch 3 --reuse-running
```

Each batch invokes the unified benchmark CLI and writes its own report and
console audit log. Lifecycle failure returns a non-zero process status and
stops later batches.

Run lifecycle validation before any AI evaluation:

```bash
python3 benchmark_cli.py \
  --agent rule --validate-only \
  --scenario <generated_name> \
  --report benchmarks/reports/<report>.md
```

Only after lifecycle validation succeeds, run the standard blind repair path:

```bash
python3 benchmark_cli.py \
  --agent ai --repair-eval --blind \
  --scenario <generated_name> --max-turns 20 \
  --report benchmarks/reports/<report>.md
```

## Current audited templates

- `bird_wrong_asn`
- `dns_nameserver`
- `ipv6_connected_route`
- `container_stopped`
- `random_complex_transit_acl` (explicit opt-in for `RANDOM_COMPLEX_INTERNET`)

The first four templates target `B00_mini_internet` and are selected by
default. The random-complex template targets the existing 100+ container
topology and must be selected explicitly with
`--topology RANDOM_COMPLEX_INTERNET`. New templates must add parameter
validation, deterministic planning, independent verification, cleanup, repair
scope, and regression tests before they become selectable.

## Scale and execution

Generation and static validation can run concurrently. Live tests must be
serialized on this VM because the current benchmark CLI performs global Docker
cleanup and network pruning. Large suites should be executed in topology-local
batches, with CLI reports and logs retained after every scenario.

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
topology. It applies a scoped OUTPUT ACL to deterministic live IX peers and
varies the peer plus ICMP payload size; it must be selected explicitly with
`--topology RANDOM_COMPLEX_INTERNET`. New templates must add parameter
validation, deterministic planning, independent verification, cleanup, repair
scope, and regression tests before they become selectable.

## Scale and execution

Generation and static validation can run concurrently. Live tests must be
serialized on this VM because the current benchmark CLI performs global Docker
cleanup and network pruning. Large suites should be executed in topology-local
batches, with CLI reports and logs retained after every scenario.

`RANDOM_COMPLEX_INTERNET` image builds are also serialized. The CLI parses the
Compose JSON once and invokes `docker build` directly for each build context,
avoiding Compose's internal parallel queue. If the local builder reports a
missing parent snapshot or a closed build-context pipe, only that service is
rebuilt with `--no-cache`; unrelated images and caches are preserved.

The build plan and every local context input are hashed into an atomic state
marker outside the generated Docker context. An unchanged complete topology
skips all 106 builds (about 1.1 seconds on the audited VM); `compose up` and
isolation recreation use `--no-build`. If startup proves an image is missing,
the CLI performs exact image checks and rebuilds only the missing services.

For 100+ container blind runs, the observation layer keeps every container
state and every router's BIRD plus OUTPUT/FORWARD firewall evidence, while
omitting unrelated per-host DNS/tc/wg probes. Selection uses only topology size
and container roles, not scenario metadata. MIMO's provider-specific malformed
`json_schema` transport falls back once to prompt-only JSON; completed objects
still pass the same local schema, read-only diagnostic gate, mutation scope,
and independent verifier.

## Audited evidence

- 10,000 deterministic scenarios: 10,000 unique names/fingerprints, 20 batches
  of 500, repeatable SHA-256, 0.794 seconds planning/validation.
- Random Complex images: 106/106 serial builds; unchanged cache hit ~1.1s.
- Random Complex no-AI lifecycle: canary 1/1 and full manifest 5/5.
- Formal blind MIMO: repair proposed/executed/verified 1/1; standard cleanup
  1/1; topology recreation 1/1; tainted 0. Category score remains 0/1 because
  the model used the generic firewall category.

Reports are stored under `benchmarks/reports/GENERATOR_RANDOM_COMPLEX_*_20260811.md`.

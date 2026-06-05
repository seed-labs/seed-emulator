# SEED Emulator Test Runner Sample

This folder demonstrates the standardized testing lifecycle for a real SEED
Emulator example. The topology is intentionally close to
`examples/basic/A00_simple_as`: three autonomous systems share Internet Exchange
`IX100`, each AS has one router and one web host, and eBGP route-server peerings
provide cross-AS reachability.

The purpose of this folder is not to introduce a new network scenario. It is a
small reference example for a lifecycle that CI, agents, and developers can
execute in the same way.

## Files

- `sample_example.py`: standardized SEED Emulator example entrypoint.
- `example.yaml`: test manifest consumed by the runner.
- `test_runtime.py`: custom runtime test program for checks that are easier to
  express in Python than YAML.
- `output/`: generated Docker compiler output, removed by the clean command.

## Standard Arguments

The example accepts both the legacy platform argument and the newer named
arguments:

```sh
python examples/sample/sample_example.py amd
python examples/sample/sample_example.py --platform amd --output examples/sample/output
python examples/sample/sample_example.py --dumpfile examples/sample/sample.bin
```

Supported arguments:

- `amd|arm`: optional legacy platform argument.
- `--platform amd|arm`: named platform argument.
- `--output PATH`: output folder for Docker compiler results.
- `--dumpfile PATH`: save a serialized emulator instead of compiling Docker output.
- `--override` / `--no-override`: control whether existing output is replaced.
- `--skip-render`: compile without calling `emu.render()` first.

## Runner

Use the new testing runner from the repository root:

```sh
python seedemu/testing/cli.py clean examples/sample/example.yaml --runner internet
python seedemu/testing/cli.py compile examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
python seedemu/testing/cli.py build examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
python seedemu/testing/cli.py up examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
python seedemu/testing/cli.py probe examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
python seedemu/testing/cli.py test examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
python seedemu/testing/cli.py down examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
```

The full lifecycle can also be run with:

```sh
python seedemu/testing/cli.py all examples/sample/example.yaml --runner internet --artifact-dir ci-artifacts/sample
```

The `internet` runner is used because this manifest includes Internet-style
probes such as `ping`.

## What The Runner Checks

The compile stage verifies:

```text
output/docker-compose.yml
```

The readiness stage checks that the generated Docker Compose services for the
three web hosts and three routers are running.

The probe stage performs declarative cross-AS reachability checks:

- AS151 web host fetches the AS150 web service.
- AS152 web host fetches the AS151 web service.
- AS150 web host pings the AS152 web host.

Declarative probes are useful when the success condition is simple and should be
visible directly in `example.yaml`.

The test stage runs custom programs listed in `test_programs`. This sample uses
`test_runtime.py` to perform runtime validation in Python. A custom test program
is useful when the success condition needs loops, tables, richer parsing, or
domain-specific logic that would make the YAML hard to read.

When the new `TestRunner` starts a test program, it provides these environment
variables:

- `TEST_RUNNER_NAME`: runner type, such as `internet`.
- `TEST_RUNNER_EMULATION_ID`: stable ID from `example.yaml`.
- `TEST_RUNNER_EMULATION_DIR`: absolute path to this example folder.
- `TEST_RUNNER_MANIFEST`: absolute path to `example.yaml`.
- `TEST_RUNNER_COMPOSE_FILE`: absolute path to the generated compose file.
- `TEST_RUNNER_ARTIFACT_DIR`: artifact folder, if one was provided.

The runner also provides the older `EXAMPLE_RUNNER_*` names for compatibility
with existing custom test programs.

The custom test exits with `0` on success and nonzero on failure. Its stdout and
stderr are captured under the artifact directory, and the runner also writes
`test-summary.json`.

## Notes

The service names in `example.yaml` are Docker Compose service names generated
by the SEED Emulator Docker compiler, such as `hnode_151_web` for a host and
`brdnode_151_router0` for an IX-connected border router. The container names
include IP addresses, but `docker compose exec` uses the service names.

# ExampleRunner SEED Emulator Sample

This folder demonstrates `seedemu.utilities.ExampleRunner` with a real SEED
Emulator example. The topology is intentionally close to `examples/basic/A00_simple_as`:
three autonomous systems share Internet Exchange `IX100`, each AS has one router
and one web host, and eBGP route-server peerings provide cross-AS reachability.

The purpose of this folder is not to introduce a new network scenario. It is a
template for the standardized example lifecycle that CI, agents, and developers
can all execute in the same way.

## Files

- `sample_example.py`: standardized SEED Emulator example entrypoint.
- `example.yaml`: metadata consumed by `ExampleRunner`.
- `test_runtime.py`: custom runtime test program used when checks are easier
  to express in Python than YAML.
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

## Lifecycle Commands

Run these commands from the repository root.

```sh
python seedemu/utilities/ExampleRunner.py clean examples/sample/example.yaml
python seedemu/utilities/ExampleRunner.py compile examples/sample/example.yaml --artifact-dir ci-artifacts/sample
python seedemu/utilities/ExampleRunner.py build examples/sample/example.yaml --artifact-dir ci-artifacts/sample
python seedemu/utilities/ExampleRunner.py up examples/sample/example.yaml --artifact-dir ci-artifacts/sample
python seedemu/utilities/ExampleRunner.py probe examples/sample/example.yaml --artifact-dir ci-artifacts/sample
python seedemu/utilities/ExampleRunner.py test examples/sample/example.yaml --artifact-dir ci-artifacts/sample
python seedemu/utilities/ExampleRunner.py down examples/sample/example.yaml --artifact-dir ci-artifacts/sample
```

The full lifecycle can also be run with:

```sh
python seedemu/utilities/ExampleRunner.py all examples/sample/example.yaml --artifact-dir ci-artifacts/sample
```

## What The Runner Checks

The compile stage verifies:

```text
output/docker-compose.yml
```

The readiness stage checks that the generated Docker Compose services for the
three web hosts and three routers are running.

The probe stage performs cross-AS reachability checks:

- AS151 web host fetches the AS150 web service.
- AS152 web host fetches the AS151 web service.
- AS150 web host pings the AS152 web host.

These probes demonstrate the kind of declarative runtime checks that can be
shared by CI and agents without writing custom Python test code for every
example.

The test stage runs custom programs listed in `test_programs`. This sample uses
`test_runtime.py` to perform the same kind of runtime validation in Python. That
is useful when the success condition needs loops, tables, richer parsing, or
domain-specific logic that would make `example.yaml` hard to read.

When `ExampleRunner` starts a test program, it provides these environment
variables:

- `EXAMPLE_RUNNER_EXAMPLE_ID`: stable ID from `example.yaml`.
- `EXAMPLE_RUNNER_EXAMPLE_DIR`: absolute path to this example folder.
- `EXAMPLE_RUNNER_MANIFEST`: absolute path to `example.yaml`.
- `EXAMPLE_RUNNER_COMPOSE_FILE`: absolute path to the generated compose file.
- `EXAMPLE_RUNNER_ARTIFACT_DIR`: artifact folder, if one was provided.

The custom test exits with `0` on success and nonzero on failure. Its stdout and
stderr are captured under the artifact directory, and the runner also writes
`test-summary.json`.

## Notes

The service names in `example.yaml` are Docker Compose service names generated
by the SEED Emulator Docker compiler, such as `hnode_151_web` for a host and
`brdnode_151_router0` for an IX-connected border router. The container names
include IP addresses, but `docker compose exec` uses the service names.

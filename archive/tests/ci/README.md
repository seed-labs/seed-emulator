# Feature-Oriented CI

The pull-request workflow is intentionally organized around SEED features rather
than broad example buckets. The manifest in `feature_manifest.json` is the source
of truth for which features are covered by unit tests, representative example
compilation, selected Docker builds, and optional runtime integration probes.

The CI runner writes both human-readable logs and machine-readable artifacts:

- `ci-summary.json` records every command, return code, duration, and log path.
- `junit.xml` records the same stage in a format GitHub and review tooling can
  ingest.
- `feature-coverage.json` records the manifest-derived coverage state, including
  covered features and declared gaps that have not landed on this integration
  line.

The static stage compiles importable Python source plus representative examples.
It intentionally excludes embedded payload templates under
`seedemu/services/EthereumService/EthTemplates/`, where some historical `.py`
filenames contain shell script content copied into containers.

Run stages locally from the repository root:

```bash
python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/static
python3 tests/ci/run_ci.py unit --artifact-dir ci-artifacts/unit
python3 tests/ci/run_ci.py example-compile --artifact-dir ci-artifacts/example-compile
python3 tests/ci/run_ci.py example-build --artifact-dir ci-artifacts/example-build
```

Docker image builds and runtime integration are available as explicit entry
points, but they are not default pull-request gates in this PR:

```bash
python3 tests/ci/run_ci.py example-build --artifact-dir ci-artifacts/example-build
python3 tests/ci/run_ci.py runtime-integration --artifact-dir ci-artifacts/runtime-integration
```

The runtime integration stage is kept as an explicit entry point for future
Docker runtime probes. The current manifest does not enable any runtime group on
this branch, so the stage is a reserved hook unless new groups are added to
`feature_manifest.json`.

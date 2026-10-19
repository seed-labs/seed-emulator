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

The `routing-rip` feature registers `tests/test_rip_layer.py` together with the
existing routing regression tests, and compiles/builds
`examples/internet/B51_rip/rip.py`. Its runtime lifecycle is available through
`B51_rip/example.yaml` and the GitHub workflow's B51 matrix entry:

The B51 script selects RIP with AS `setIgpMode("rip")` calls and leaves the
remaining ASes at their OSPF default, without mask calls or layer AS scopes.
`Ospf()` and `Rip()` have no `asns`, `setAsns()` or `getAsns()` API; installing
Rip alone never changes an unset AS's OSPF default.
Its single RIP class is `Rip`, matching `Ospf`. Both layers consume the AS's
`setIgpInterfacePolicy("all-local"|"router-links")` declaration; B51 demonstrates
`router-links` on AS2 (RIP) and AS3 (OSPF). Unset policies preserve the existing
OSPF all-local and RIP router-links defaults.
It uses ordinary Docker addresses and announces IX LANs through BGP. B00
retains its original OSPF script and uses the same ordinary Docker mode.
Runtime validation requires `net.bridge.bridge-nf-call-iptables=0` on the
Docker host, as configured persistently on the local server. Neither B51 nor
its runtime tests change host sysctls or add firewall exemptions.

```sh
python3 seedemu/testing/cli.py all examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/b51-rip
```

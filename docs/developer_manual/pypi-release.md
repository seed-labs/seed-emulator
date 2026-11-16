# Publishing SeedEmu

SeedEmu 2.0.0 is built from `development` and released through `master`.

## Before merging

1. Open a PR from `release` to `development` and wait for the existing example
   CI and **Validate SeedEmu packages** to pass.
2. Open a PR from `development` to `master` and wait for the same checks.
3. Merge that PR when ready to publish. Closing an unmerged PR, merging into
   `development`, pushing a tag, or pushing directly to `master` does not publish.

Package validation builds a wheel and an sdist. Each is installed in clean
Python 3.10 and 3.12 environments using only its declared runtime dependencies.
Checks cover public imports, bundled Kubernetes resources, rendered network
APIs, Docker output for AMD64 and ARM64, and every compilation in the existing
example CI matrix. Docker container build and runtime checks remain in the
existing example workflow.

## One-time account configuration

Before merging into `master`:

1. Create or sign into a PyPI account and enable two-factor authentication.
2. In PyPI account **Publishing**, add a pending GitHub publisher (or add it
   under the existing project's Publishing page if you already own `seedemu`):

   | Field | Value |
   | --- | --- |
   | PyPI project | `seedemu` |
   | GitHub owner | `seed-labs` |
   | Repository | `seed-emulator` |
   | Workflow filename | `publish-pypi.yaml` |
   | Environment | `pypi` |

3. Create the `pypi` environment in GitHub repository **Settings → Environments**.
   Restrict its deployment branches to `master`. An optional required reviewer
   can control the final upload.

Trusted Publishing uses GitHub OIDC; no PyPI upload token is stored in the repo.
The first successful upload creates the project. A pending publisher does not
reserve the package name.

## What happens after merging to master

`publish-pypi.yaml` runs only for a merged PR targeting `master`. It validates
and builds the merged revision, checks the version on PyPI, and uploads the
validated artifacts. Build and upload run in separate jobs; only the upload
job has `id-token: write`.

If the version already exists, the upload is skipped. Update `setup.py` to a
new version for a new release. An HTTP error other than 404 fails the lookup;
it is not treated as permission to overwrite an existing release. If a failed
upload left a partial release, inspect the PyPI files before retrying.

The workflow does not create or merge PRs, or create GitHub tags/releases.

## Local checks

Run in the repository root, using a separate environment:

```sh
uv venv --python 3.10 --seed /tmp/seedemu-build-env
uv pip install --python /tmp/seedemu-build-env/bin/python build twine
/tmp/seedemu-build-env/bin/python -m build
/tmp/seedemu-build-env/bin/python -m twine check --strict dist/*

uv venv --python 3.10 --seed /tmp/seedemu-wheel-env
uv pip install --python /tmp/seedemu-wheel-env/bin/python dist/seedemu-2.0.0-py3-none-any.whl
/tmp/seedemu-wheel-env/bin/python -m pip check
/tmp/seedemu-wheel-env/bin/python -I tests/installed_package_smoke.py \
  --expected-version 2.0.0 --examples examples \
  --workflow .github/workflows/on-pull-request.yaml
```

Repeat the installation in another clean environment with
`dist/seedemu-2.0.0.tar.gz` to check source-distribution installation.
For the full container lifecycle, use the existing example manifests, e.g.
`python -m seedemu.testing.cli all examples/basic/A00_simple_as/example.yaml`.

## Installation channels

After the release is published:

```sh
python -m pip install seedemu==2.0.0
```

To install current development source:

```sh
python -m pip install "git+https://github.com/seed-labs/seed-emulator.git@development"
```

PyPI packages update when a new version is released. An installed package does
not automatically track changes to a Git branch.

References: [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
[GitHub merged-PR events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#running-your-pull_request-workflow-when-a-pull-request-merges).

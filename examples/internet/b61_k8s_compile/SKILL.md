---
name: seedemu-k8s-native-workflow
description: Use when working with a SeedEMU repository that contains seedemu/k8sTools or examples/internet/b61_k8s_compile, especially to understand, generate, modify, or validate native Kubernetes/K3s deployment workflows for SeedEMU emulations using k8sTools, KVM, physical nodes, multi-host KVM, Multus, Kube-OVN, or OVS.
---

# SeedEMU k8sTools Native Kubernetes Workflow

Use this skill when the task involves building or modifying a SeedEMU
simulation that will run on Kubernetes/K3s through `seedemu.k8sTools`.

## First Steps

1. Find the repository root without assuming an absolute path.
   - Start from the current working directory.
   - Walk upward until a directory contains both `setup.py` and `seedemu/`.
   - Prefer a root that also contains `seedemu/k8sTools/README.md`.
   - Do not hardcode paths from another user's machine.

2. Read the local documentation before making architectural claims.
   - `seedemu/k8sTools/README.md`
   - `seedemu/k8sTools/resources/setup/README.md`
   - `examples/internet/b61_k8s_compile/README.md`

3. Inspect the active example files.
   - `examples/internet/b61_k8s_compile/mini_internet_k8s.py`
   - `examples/internet/b61_k8s_compile/k8sTools.py`
   - `examples/internet/b61_k8s_compile/configKvmOvn.yaml`
   - `examples/internet/b61_k8s_compile/configK3sOvn.yaml`
   - `examples/internet/b61_k8s_compile/configMultiHostKvmOvn.yaml`

Avoid loading generated `output/`, `configK3s.yaml`, or `kubeconfig.yaml`
unless the task specifically concerns runtime artifacts.

## Architecture Model

Think of the workflow as three separate contracts:

1. Compile contract:
   - `KubernetesCompiler` turns a rendered SeedEMU emulator into
     Kubernetes manifests and Docker build contexts.
   - The B61 example writes compiler output to `./output` by default.
   - Important files are `k8s.kube-ovn.yaml` or `k8s.yaml`, `images.yaml`,
     per-node Docker build contexts, and sometimes `base_images/`.
   - The compile stage does not require a live cluster inventory.

2. Setup contract:
   - `K8sTools.build()` reads one user input YAML with explicit `kind`.
   - Supported kinds are `kvmOvn`, `physicalOvn`, and `multiHostKvmOvn`.
   - It copies packaged `resources/setup/` into a temporary directory, runs
     the setup entrypoints there, and writes user-visible `configK3s.yaml` and
     `kubeconfig.yaml`.
   - KVM destroy state is embedded into generated `configK3s.yaml`.

3. Running contract:
   - `K8sTools.up()` copies packaged `resources/running/` into a temporary
     directory, runs preflight, builds/pushes images, renders
     `kustomization.yaml`, applies the workload, and waits for readiness.
   - `K8sTools.down()` removes workload resources and the namespace.
   - `K8sTools.destroy()` removes K3s/OVN and optional KVM infrastructure
     recorded in `configK3s.yaml`.

## Preferred Commands

From `examples/internet/b61_k8s_compile`:

```bash
python3 ./mini_internet_k8s.py
python3 ./k8sTools.py build \
  --input configKvmOvn.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml
python3 ./k8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml
python3 ./k8sTools.py down -f ./output -k kubeconfig.yaml
python3 ./k8sTools.py destroy -d configK3s.yaml
```

Use `--input configK3sOvn.yaml` for existing physical machines, or
`--input configMultiHostKvmOvn.yaml` for KVM VMs distributed across multiple
physical hypervisors.

All `k8sTools.py` commands accept `--keep-temp` when the temporary copied
setup/running resources need to be inspected after a failed run.

## Path Rules

- Never write a developer machine's absolute path into docs, skills, or source
  examples.
- Use repository-relative paths in documentation.
- In Python examples, discover the repository root by walking upward from
  `Path(__file__).resolve()`.
- Treat `output/`, `configK3s.yaml`, `configK3sTemplate.yaml`, `kubeconfig.yaml`,
  image caches, cloud-init files, and KVM state files as generated artifacts.
- If a YAML field points to an SSH key, prefer `~/.ssh/<name>` rather than an
  absolute `/home/<user>/...` path.

## Validation

Use non-destructive checks first:

```bash
python3 -m py_compile \
  seedemu/k8sTools/*.py \
  seedemu/k8sTools/resources/setup/*.py \
  seedemu/k8sTools/resources/setup/kvm/*.py \
  seedemu/k8sTools/resources/setup/multiHostKvm/*.py \
  seedemu/k8sTools/resources/setup/ovn/*.py \
  seedemu/k8sTools/resources/setup/vxlan/*.py \
  seedemu/k8sTools/resources/running/*.py
for f in $(rg --files seedemu/k8sTools/resources -g '*.sh'); do bash -n "$f"; done
python3 examples/internet/b61_k8s_compile/k8sTools.py --help
```

Real `build`, `up`, `down`, and `destroy` commands create or modify KVM VMs,
K3s clusters, registries, images, Kubernetes namespaces, or physical nodes.
State those side effects before running them.

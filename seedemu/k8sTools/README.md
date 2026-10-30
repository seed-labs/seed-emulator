# seedemu.k8sTools

`seedemu.k8sTools` is the simplified Kubernetes workflow entrypoint for
SeedEMU examples. It keeps the user-facing example directory small: commands
use temporary setup/running resources internally and do not persist `setup/`,
`running/`, or `.k8sTools/` directories.

## Commands

Build infrastructure:

```bash
python k8sTools.py build \
  --input configKvmOvn.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

Deploy workload:

```bash
python k8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml
```

`up` infers the logical compiler image prefix from `images.yaml` or
`images.txt`. Pass
`--image-registry-prefix <prefix>` only when the compile output intentionally
uses a non-standard or mixed prefix.

Clean workload only:

```bash
python k8sTools.py clean -f ./output -k kubeconfig.yaml
```

`down` remains accepted as a compatibility alias for `clean`.

Destroy infrastructure:

```bash
python k8sTools.py destroy -d configK3s.yaml
```

## Config Kinds

- `kind: kvmOvn` creates local KVM VMs, builds K3s, and installs Kube-OVN.
- `kind: physicalOvn` uses existing physical nodes, builds K3s, and installs Kube-OVN.
- `kind: multiHostKvmOvn` creates KVM VMs across multiple hypervisors, builds
  K3s, and installs Kube-OVN.

## Internal Architecture

`build` copies bundled `resources/setup/` into a temporary directory and invokes
Python entrypoints there:

- `kvmOvn`: `kvm/prepareHostAssets.py`, `kvm/createKvmVms.py`,
  `kvm/tuneVmLimits.py`, `applyK3sCluster.py`, then Kube-OVN installation.
- `physicalOvn`: `preparePhysicalNodes.py`, `applyK3sCluster.py`, then
  Kube-OVN installation.
- `multiHostKvmOvn`: `multiHostKvm/prepareKvmHypervisors.py`,
  `multiHostKvm/createMultiHostKvmVms.py`, `kvm/tuneVmLimits.py`,
  `applyK3sCluster.py`, then Kube-OVN installation.

`up` copies bundled `resources/running/` into a temporary directory and invokes
`manageRunningStage.py preflight`, `build`, and `up`. The running stage renders
`kustomization.yaml`, rewrites OVN manifests when needed, reads image metadata
from `images.yaml` or `images.txt`, builds/pushes images to the registry
resolved from `configK3s.yaml`, applies the manifest, and waits for readiness.
Before a remote registry-host build, it scans generated Dockerfiles for external
`FROM` images, ensures those images exist on the local Docker daemon, and loads
them into the registry host Docker daemon so buildx does not need to resolve
compiler base images through Docker Hub from the master node.

No persistent setup/running working directory is created by default. Persistent
outputs are limited to the user-requested `configK3s.yaml`, `kubeconfig.yaml`,
optional `inventory.yaml`, and the compiler output directory.

All commands accept `--keep-temp` to leave the copied setup/running resources
on disk for debugging.

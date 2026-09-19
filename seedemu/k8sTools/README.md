# seedemu.k8sTools

`seedemu.k8sTools` is the simplified Kubernetes workflow entrypoint for
SeedEMU examples. It keeps the user-facing example directory small: commands
use temporary setup/running resources internally and do not persist `setup/`,
`running/`, or `.k8sTools/` directories.

## Commands

Build infrastructure:

```bash
python k8sTools.py build \
  --input configKvmMacvlan.yaml \
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

- `kind: kvm` creates local KVM VMs and builds K3s.
- `kind: physical` builds K3s on existing physical nodes.
- `kind: multiHostKvm` creates KVM VMs across multiple hypervisors and builds
  one K3s cluster.

The infrastructure kind does not select the secondary network backend.
`fabric.type` selects `ovn`, `macvlan-vlan`, `bridge-vlan`, or another
supported fabric. Kube-OVN is installed only when `fabric.type` is `ovn`.

The legacy values `kvmOvn`, `physicalOvn`, and `multiHostKvmOvn` remain
accepted with a deprecation warning. New configurations must use the neutral
kind names.

## Internal Architecture

`build` copies bundled `resources/setup/` into a temporary directory and invokes
Python entrypoints there:

- `kvm`: `kvm/prepareHostAssets.py`, `kvm/prepareKvmNetworks.py`,
  `kvm/createKvmVms.py`, `kvm/tuneVmLimits.py`, then
  `applyK3sCluster.py`.
- `physical`: `preparePhysicalNodes.py`, then `applyK3sCluster.py`.
- `multiHostKvm`: `multiHostKvm/prepareKvmHypervisors.py`,
  `multiHostKvm/createMultiHostKvmVms.py`,
  `multiHostKvm/validateMultiHostKvmFabric.py`, `kvm/tuneVmLimits.py`, then
  `applyK3sCluster.py`.

For VLAN-backed multi-host fabrics, `prepareKvmHypervisors.py` also creates
unnumbered libvirt bridges and VXLAN flood domains for the configured
`fabric.vlanTrunks`. Every VM receives one dedicated NIC per trunk. The
routed K3s management NIC remains separate.

Set `fabric.mtu` when a trunk is extended through VXLAN. The B62 multi-host
configuration uses 1400 so a secondary IP packet plus Ethernet, VLAN, and
fabric VXLAN headers fits a 1500-byte physical underlay.

Remote hypervisors prepare only their VM cloud image. Docker bootstrap and
SeedEMU image caches are prepared once on the control-side host and are later
preloaded into every K3s node by `applyK3sCluster.py`.

The fabric validator requires same-VLAN macvlan probes to pass in both
directions and adjacent-VLAN probes to remain unreachable. This covers both
cross-hypervisor forwarding and L2 isolation.

`applyK3sCluster.py` installs Multus for secondary interfaces and invokes the
Kube-OVN setup entrypoint only for an OVN fabric.

`up` copies bundled `resources/running/` into a temporary directory and invokes
`manageRunningStage.py preflight`, `build`, and `up`. The running stage renders
`kustomization.yaml`, rewrites OVN manifests when needed, reads image metadata
from `images.yaml` or `images.txt`, builds/pushes images to the registry
resolved from `configK3s.yaml`, applies the manifest, and waits for readiness.
For VLAN-backed macvlan manifests, it first creates the annotated VLAN parent
interfaces on the K3s nodes that may run each workload.
The parent interface and MTU from `configK3s.yaml` (originating in the selected
build YAML) override the compiler's placeholders while rendering
`kustomization.yaml`. This lets one no-argument compiler output serve local
KVM, physical-node, and multi-host KVM deployments.
Before a remote registry-host build, it scans generated Dockerfiles for external
`FROM` images, ensures those images exist on the local Docker daemon, and loads
them into the registry host Docker daemon so buildx does not need to resolve
compiler base images through Docker Hub from the master node.

No persistent setup/running working directory is created by default. Persistent
outputs are limited to the user-requested `configK3s.yaml`, `kubeconfig.yaml`,
optional `inventory.yaml`, and the compiler output directory.

All commands accept `--keep-temp` to leave the copied setup/running resources
on disk for debugging.

## VM Memory Units

Cluster YAML supports `master.memoryGiB`, `workers.memoryGiB`, and single-host
explicit `nodes[].memoryGiB`. Values may be fractional (10.5 GiB = 10752 MiB).
`memoryGb` is a binary-GiB compatibility alias; legacy `memoryMb`/`memory_mb`
still mean MiB. These optional spellings replace, rather than supplement, the
old memory field; existing API defaults apply when memory is omitted.
`resources/setup/normalizeResources.py` rejects conflicting sizes, nonpositive
values, and sizes not representable as whole MiB. Generated VM/K3s state keeps
MiB so existing provisioning and destroy consumers remain compatible.

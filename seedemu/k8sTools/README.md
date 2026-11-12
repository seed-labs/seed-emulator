# seedemu.k8sTools

`seedemu.k8sTools` is the simplified Kubernetes workflow entrypoint for
SeedEMU examples. It keeps the user-facing example directory small: commands
use temporary setup/running resources internally and do not persist `setup/`,
`running/`, or `.k8sTools/` directories.

## Commands

Build infrastructure:

```bash
python K8sTools.py build \
  --input configKvm.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

Deploy workload:

```bash
python K8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml
```

`up` applies the `nodeByAs` partition algorithm by default. It reads the
compiler's `seedemu.io/asn` metadata and the current Ready-node capacity, then
binds each ASN's workloads to one eligible worker with `nodeName`. Select a
built-in name or pass a Python partition script directly:

```bash
python K8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml \
  --partition nodeByAs
python K8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml \
  --partition ../../../seedemu/k8sTools/resources/partition/partitionByAs.py
```

Only `--partition` is accepted; misspellings and abbreviations are rejected. A script path is
resolved relative to the directory where you invoke `up`, before entering
temporary running resources. Paths with spaces must be quoted. Built-in names
remain `nodeByAs` (`nodeAS` alias), `roundRobin`, and `default` (preserves compiler
scheduling). Custom scripts require no registration or framework changes, but must reside
inside `seedemu/k8sTools/` (resolved symlinks included). External code paths are rejected
before preflight so workload code remains managed in this package.

Placement evidence is written beside the compiler output as
`partitionInput.json`, `partitionResult.json`, `partitionApplied.json`, and a hidden source-manifest
snapshot. The source snapshot is restored before every new `up`, so a later
`clean`/`up` cycle or a recompiled manifest does not retain an old placement.

Managed partition scripts use the following local file interface, executed with the
same Python interpreter as the partition stage and the script's directory as
its working directory:

```bash
python /absolute/path/partitionByAs.py --input /absolute/path/partitionInput.json \
  --output /absolute/path/fresh-result.json
```

The framework writes the JSON input before invoking the script:

| Input field | Meaning |
| --- | --- |
| `schemaVersion` | Interface version; currently `1`. |
| `topology.vertices` | Every SeedEMU workload name to assign, exactly once. |
| `topology.networks` | LAN hyperedges: `id` and workload-name `members`. |
| `asns` | Workload name to ASN string. |
| `workloads` | Each workload's `name`, `kind`, `docIndex`, `asn`, `replicas`, per-Pod `cpuMillis` and `memoryBytes` requests. |
| `nodes` | Eligible Ready, schedulable nodes with allocatable `cpuMillis`, `memoryBytes`, and `podSlots`; hard-tainted nodes are excluded. |
| `existingUsage` | Active Pod CPU/memory requests and Pod count per node. |
| `remainingCapacity` | Node-name to remaining CPU/memory/Pod budgets after existing usage, reserve and worker cap; use these budgets for placement. |
| `options` | `podReserve` (default `0`) and `maxNodesPerWorker` (default `900`), selected with `--partition-pod-reserve` and `--partition-max-nodes-per-worker`. |

The script must exit zero and write a JSON object with a complete workload
mapping; optional `details` contains algorithm diagnostics:

```json
{"mapping": {"router-a": "worker-1", "host-b": "worker-2"}, "details": {"algorithm": "my-method"}}
```

The framework validates exact workload coverage, eligible targets and aggregate
CPU/memory/Pod capacity (including replicas) before changing the deployment
manifest. Failed scripts, malformed output and invalid mappings stop `up`
before image building or deployment. CPU/memory checks use requests, not
measured resource demand. Scripts return placement only; the framework applies
`nodeName` and recomputes LAN metrics. Script stdout/stderr is saved as
`partition.log`, raw JSON as `partitionScriptResult.json`, and script path,
SHA-256 and invocation as `partitionApplied.json.script`. Results from previous
invocations are never accepted as a script's new output.

[`resources/partition/partitionByAs.py`](resources/partition/partitionByAs.py)
is an executable whole-AS example using only the Python standard library.
Copy it and replace `createPartition(value)` to implement another algorithm.

`up` infers the logical compiler image prefix from `images.yaml` or
`images.txt`. Pass
`--image-registry-prefix <prefix>` only when the compile output intentionally
uses a non-standard or mixed prefix.

Clean workload only:

```bash
python K8sTools.py clean -f ./output -k kubeconfig.yaml
```

`down` remains accepted as a compatibility alias for `clean`.

Destroy infrastructure:

```bash
python K8sTools.py destroy -d configK3s.yaml
```

## Config Kinds

- `kind: kvm` creates local KVM VMs and builds K3s.
- `kind: physical` builds K3s on existing physical nodes.
- `kind: multiHostKvm` creates KVM VMs across multiple hypervisors and builds
  one K3s cluster.

The infrastructure kind does not select the secondary network backend.
`fabric.type` selects `ovn`, `macvlan-vlan`, `bridge-vlan`, or another
supported fabric. Kube-OVN is installed only when `fabric.type` is `ovn`.

For macvlan deployments, optional `cni.defaultMasterInterface` selects the
runtime parent instead of the compiler's placeholder parent. Explicit
`fabric.vlanTrunks[].name/masterInterface` mappings take priority per trunk,
so multi-trunk deployments retain separate NICs. Optional `cni.mtu` overrides
`fabric.mtu`, then compiler `cniMtu`, then 1400. Both the fast runtime renderer
and compatibility kustomization renderer consume these settings; generated
VLAN-parent metadata matches the final CNI parent.

The legacy values `kvmOvn`, `physicalOvn`, and `multiHostKvmOvn` remain
accepted with a deprecation warning. New configurations must use the neutral
kind names.

## Internal Architecture

`build` copies bundled `resources/setup/` into a temporary directory and invokes
Python entrypoints there:

- `kvm`: `kvm/PrepareHostAssets.py`, `kvm/CreateKvmVms.py`,
  `kvm/TuneVmLimits.py`, then `ApplyK3sCluster.py`.
- `physical`: `PreparePhysicalNodes.py`, then `ApplyK3sCluster.py`.
- `multiHostKvm`: `multiHostKvm/PrepareKvmHypervisors.py`,
  `multiHostKvm/CreateMultiHostKvmVms.py`,
  `multiHostKvm/ValidateMultiHostKvmFabric.py`, `kvm/TuneVmLimits.py`, then
  `ApplyK3sCluster.py`.

For VLAN-backed multi-host fabrics, `PrepareKvmHypervisors.py` also creates
unnumbered libvirt bridges and VXLAN flood domains for the configured
`fabric.vlanTrunks`. Every VM receives one dedicated NIC per trunk. The
routed K3s management NIC remains separate.

Set `fabric.mtu` when a trunk is extended through VXLAN. The B62 multi-host
configuration uses 1400 so a secondary IP packet plus Ethernet, VLAN, and
fabric VXLAN headers fits a 1500-byte physical underlay.

Remote hypervisors prepare only their VM cloud image. Docker bootstrap and
SeedEMU image caches are prepared once on the control-side host and are later
preloaded into every K3s node by `ApplyK3sCluster.py`.

The fabric validator requires same-VLAN macvlan probes to pass in both
directions and adjacent-VLAN probes to remain unreachable. This covers both
cross-hypervisor forwarding and L2 isolation.

`ApplyK3sCluster.py` installs Multus for secondary interfaces and invokes the
Kube-OVN setup entrypoint only for an OVN fabric.

`up` copies packaged `resources/running/` into a temporary directory. The
deployment stages use the B63 scale design; implementation imports and helper
executables come from this package, rather than the example directories:

1. Preflight and capacity-aware, whole-AS placement on Ready workers.
2. Render `output/k8stools/runtime.yaml` in one pass, mapping images and CNI
   parents without a large Kustomize image-transformation list.
3. Build shared software bases, then compose small per-workload layers into
   node-specific Docker archives. Every distinct Dockerfile `FROM` is retained.
4. Stream each archive into the destination node's `k3s ctr images import` and
   verify every assigned image reference. Unused nodes receive no archive.
   Remove the builder's temporary archives after every import passes; failed
   builds/imports retain their unique staging directory for diagnosis.
5. Prepare the node-specific VLAN parent links, submit static resources in
   bounded batches, then dispatch independent worker queues. Their startup
   reservations include controllers whose Pods have not yet been observed.
6. Poll the expected Deployment/Pod set together until all are Ready.

`up` ends at Kubernetes readiness. It does not perform B63's subsequent
explicit BIRD startup, kernel route export, reconvergence or traffic tests.
When compiler startup scripts defer BIRD (ending with `tail -f /dev/null`),
Ready Pods therefore do not prove protocol/FIB readiness. The packaged
`resources/running/validateWorkload.py` can compare live Pod placement,
resources, node VLAN parents and BIRD process state with a frozen reference
using read-only API/SSH calls. It never imports reference-run implementations
or starts routing on the user's behalf.

`manageWorkload.py`, `buildImageArchives.py`, and `deployWorkerQueues.py` are
packaged running helpers. They use generated cluster state and compiler output;
they do not import experiment scripts, topology inputs, or the original source
YAML. `partition.py` contains the reusable placement algorithms.

`output/k8stools/` holds the rendered manifest, `image-plan.json`, node preload
lists/logs, `image-archives.json`, `preload-summary.json`, queue journals,
`readiness.json`, and timed stage receipts. These are generated artifacts;
setup/running scripts remain temporary. `clean` removes the workload namespace
and compiler-owned cluster-scoped OVN resources without expanding Kustomize.

Optional workload settings belong in the same infrastructure input YAML and
are embedded by `build` into `configK3s.yaml`:

```yaml
k8sTools:
  running:
    imageBuildMode: fast
    preloadNodeConcurrency: 4
deploy:
  controllerApplyMode: worker-queue
  workerConcurrencyMode: resource
```

| Optional field | Default | Consumer / meaning |
| --- | --- | --- |
| `k8sTools.running.imageBuildMode` | `fast` | `manageWorkload.py`: shared-base archives; `registry` explicitly selects ordinary Docker build/push and per-node pull for custom Dockerfiles. |
| `k8sTools.running.preloadNodeConcurrency` | 4 | Maximum concurrent node imports/pulls. |
| `k8sTools.running.imageBuildTimeoutSeconds` | 1800 | Remote image stage timeout. |
| `deploy.controllerApplyMode` | `worker-queue` | Independent queues for directly bound single-replica Deployments; `batch` uses bounded submission batches. |
| `deploy.workerConcurrencyMode` | `resource` | Resource-based or `fixed` startup window. |
| `deploy.workerMaxInFlight` | 4 | Startup window in fixed mode. |
| `deploy.workerCpuPerStartup` / `workerMemoryGiBPerStartup` | 0.5 / 1 | Resource-mode startup slot weights. |
| `deploy.workerReservedCpu` / `workerReservedMemoryGiB` | 1 / 2 | Resource-mode startup reserves. |
| `deploy.workerConcurrencyCeiling` | 64 | Maximum resource-mode startup window. |
| `deploy.workerPollSeconds` | 2 | Shared Pod observation interval. |
| `deploy.workerStartupTimeoutSeconds` | 600 | Maximum time for one startup reservation. |
| `deploy.batchSize` / `subnetBatchSize` | 20 / 250 | Controller/static resource batch sizes. |

Fast archives support the compiler's standard COPY/startup operations and
pre-COPY software installs. Unsupported custom Dockerfile operations fail with
the context path; select `imageBuildMode: registry` for those images.

All commands accept `--keep-temp` to leave the copied setup/running resources
on disk for debugging.

## VM Memory Units

Cluster YAML supports `master.memoryGiB`, `workers.memoryGiB`, and single-host
explicit `nodes[].memoryGiB`. Values may be fractional (10.5 GiB = 10752 MiB).
`memoryGb` is a binary-GiB compatibility alias; legacy `memoryMb`/`memory_mb`
still mean MiB. These optional spellings replace, rather than supplement, the
old memory field; existing API defaults apply when memory is omitted.
`resources/setup/NormalizeResources.py` rejects conflicting sizes, nonpositive
values, and sizes not representable as whole MiB. Generated VM/K3s state keeps
MiB so existing provisioning and destroy consumers remain compatible.

For heterogeneous explicit `nodes[]`, disk capacity accepts `diskGb` and the
legacy `disk_gb` spelling. The setup parser preserves this capacity after the
public adapter normalizes field names and rejects conflicting values.

KVM creation also supplies an explicit virtio-serial controller and QEMU guest
agent channel. The cloud-init guest-agent service needs this device even when a
generic OS variant is used; without it, cloud-init may end with a scripts-user
failure despite SSH and K3s becoming reachable.

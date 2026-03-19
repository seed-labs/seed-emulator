# SEED Emulator KubeVirt Hybrid Kubernetes Design

## 1. Overview

This design extends SEED Emulator so that selected nodes can run as
**KubeVirt virtual machines** inside a Kubernetes cluster while remaining
interoperable with normal container-based nodes.

The goal is to support both local development environments and standard Linux
server environments without changing the Python topology model.

### Design goals

1. **Higher-fidelity emulation**  
   Allow selected nodes to run with kernel or OS behavior that does not fit the
   normal container model.
2. **Hybrid deployment**  
   Run containers and virtual machines in the same emulated network.
3. **Minimal topology changes**  
   Keep the topology API stable and enable VM mode through
   `node.setVirtualizationMode('KubeVirt')`.
4. **Automated environment setup**  
   Provide a repeatable Kind + Multus + KubeVirt bootstrap workflow.

## 2. Runtime architecture

### 2.1 Infrastructure layer

- **Host**: Linux workstation or Linux server
- **Cluster manager**: Kind for local cluster creation
- **Virtualization**: KubeVirt, preferring KVM and falling back to software
  emulation when hardware support is unavailable
- **Network layer**: Multus CNI so Pods and VMs can attach multiple interfaces

### 2.2 Node types

| Property | Container node | KubeVirt VM node |
|:---|:---|:---|
| Runtime object | Kubernetes `Deployment` | KubeVirt `VirtualMachine` |
| Boot path | Docker image | containerDisk + cloud-init |
| File injection | `Dockerfile` + copied assets | cloud-init `write_files` |
| Startup logic | `/start.sh` | cloud-init `runcmd` |
| Address rewrite | container-side helper script | VM-side cloud-init scripts |
| Best use case | routers, hosts, services | custom kernel or high-isolation nodes |

## 3. Compilation strategy

The traditional SEED flow relies on Dockerfile-driven image construction. That
works well for containers, but it is too heavy for VM images. The hybrid design
therefore uses **generic cloud images + cloud-init** for VM nodes.

### 3.1 Compiler mapping

The Kubernetes compiler maps SEED node operations as follows:

1. **Base image**
   - container: normal container base image
   - VM: generic KubeVirt-compatible Ubuntu cloud image
2. **`node.addFile(...)`**
   - container: copied into the image
   - VM: emitted into cloud-init `write_files`
3. **`node.addSoftware(...)`**
   - container: installed by Dockerfile package steps
   - VM: emitted into cloud-init package installation
4. **`node.appendStartCommand(...)`**
   - container: added to `/start.sh`
   - VM: added to cloud-init `runcmd`

## 4. Networking model

SEED topologies use static addresses, while Kubernetes CNI workflows normally
expect dynamic IP assignment. The hybrid design handles this explicitly.

### 4.1 Container path

- Multus attaches the extra interfaces.
- A container-side helper rewrites the interface addresses to match the SEED
  topology.
- The expected secondary interface names are typically `net1`, `net2`, and so
  on.

### 4.2 VM path

- VM interfaces are commonly exposed as `eth0` for management and `eth1`,
  `eth2`, ... for experiment links.
- The compiler emits cloud-init configuration that maps SEED interfaces onto
  the VM-visible device order.

### 4.3 Operational constraints

- Multus must provide correct layer-2 behavior for the selected attachment
  mode, such as `bridge` or `macvlan`.
- For local Kind-based validation, `bridge` remains the most predictable mode.

## 5. Implementation plan

1. **Core Python support**
   - extend `Node.py` with virtualization-mode metadata
   - extend `seedemu/compiler/Kubernetes.py` with VM compilation paths and
     cloud-init generation
2. **Environment automation**
   - keep `setup_kubevirt_cluster.sh` as the one-shot bootstrap entry
   - detect virtualization support
   - install Kind, Multus, and KubeVirt
   - wait for readiness and write diagnostics
3. **Validation**
   - validate a hybrid topology such as one VM router plus two container hosts
   - check connectivity, BGP behavior, and recovery behavior

## 6. Relationship to the maintained K8s branch

This design document explains the hybrid execution model. The maintained public
operator flow is documented separately:

- Operator workflow: `docs/k8s_usage.md`
- Maintainer architecture: `docs/k3s_runtime_architecture.md`
- Local Kind/KubeVirt runbook: `docs/runbooks/local_kind_quick_runbook.md`

# B61 Native Kubernetes Example

This example compiles one SeedEMU mini-Internet and deploys the same compiler
output to one of three K3s environments. All three modes use Multus with
macvlan+VLAN secondary networks.

## Configure the selected YAML first

Choose exactly one input YAML. The checked-in physical addresses, host names,
SSH accounts, and interface names describe the validation lab and are not
portable to another lab.

### Values you must set or verify

| Mode | Input YAML | Values that describe your environment |
| --- | --- | --- |
| Local KVM | `configKvmMacvlan.yaml` | Set `ssh.key` to a readable private key on the control host. Keep `ssh.user: ubuntu` unless you want the VMs to create and use another login account. Confirm the local libvirt/KVM host has enough CPU, memory, and disk for the requested VMs. |
| Existing physical nodes | `configPhysicalMacvlan.yaml` | Replace every `nodes[].name`, `role`, `ip`, `connection`, and `ssh.user/key`. Rename the corresponding keys below `fabric.nodes` and replace each `underlayInterface`; alternatively remove `underlayInterface` to let the setup discover the interface used to reach the peer. |
| Multi-host KVM | `configMultiHostKvmMacvlan.yaml` | Replace every `hypervisors[].name`, `ip`, `connection`, and `ssh.user/key`; choose non-overlapping `routedSubnet.cidr`/`gateway` values; set unique libvirt `networkName`/`bridgeName` values; set `vmSsh.key`; and make `master.placement` match one hypervisor name. |

For every remote physical node or hypervisor, the selected account must support
SSH key login and `sudo -n`. A YAML `connection: local` entry must describe the
machine on which `k8sTools.py` is being run.

The CNI parent is selected by the deployment YAML, not by the compile command:

| Input YAML | CNI parent used by `up` | Where it comes from |
| --- | --- | --- |
| `configKvmMacvlan.yaml` | `ens2` | `cni.defaultMasterInterface`; this is the VM management NIC. |
| `configPhysicalMacvlan.yaml` | `br-seedemu` | `fabric.bridgeName` and `cni.defaultMasterInterface`; the setup creates this bridge over the two physical underlay interfaces. |
| `configMultiHostKvmMacvlan.yaml` | `ens3` | `fabric.vlanTrunks[].masterInterface` and `cni.defaultMasterInterface`; the setup adds this dedicated trunk NIC to each VM. |

If you change one of these interface values, keep the values in the same YAML
consistent. You do not pass an interface to `mini_internet_k8s.py` and you do
not manually edit every NetworkAttachmentDefinition. During `up`, k8sTools
uses the chosen YAML's generated `configK3s.yaml` to write the required parent
interface and MTU patches to `output/kustomization.yaml`, then creates the
matching VLAN parent interfaces on the K3s nodes.

### Values you may customize

The following settings already have working sample values. Leave them unchanged
unless they conflict with your environment or you want a different cluster
size:

| Mode | Optional adjustments |
| --- | --- |
| All modes | `clusterName`, `k3s.version`, `registry.port`, optional `cni.mtu`, and the three `cni.*CniType` compatibility fields. Keep the CNI type as `macvlan` for this example. |
| Local KVM | `defaults.masterName`, `defaults.workerNamePrefix`, `workers.count`, master/worker `vcpus`, `memoryMb`/`memoryGiB`, `diskGb`, and optional `kvm.network` settings. |
| Physical nodes | `fabric.bridgeName`, `vxlanName`, `vni`, `dstPort`, and `mtu`. The supplied names and VNI/port can be retained when they do not collide with another tunnel. |
| Multi-host KVM | `vmCount`, master/worker names and resources, `routingTunnel` CIDR/VNI/port, `fabricVxlan` VNI/port, VLAN range, and `fabric.mtu`. |

`memoryMb` means MiB. `memoryGiB` is also accepted; specify only one memory
field in a resource section. Resource values are per VM, and the number of
multi-host workers is `sum(hypervisors[].vmCount) - 1`.

The normal CNI MTU is 1400 and is already the no-argument compiler default, so
no `--cni-mtu` option is needed. The supplied physical and multi-host YAMLs also
use `fabric.mtu: 1400` for their VXLAN paths. If a deployment YAML sets
`cni.mtu` or `fabric.mtu`, `up` gives that value priority and patches the NADs
accordingly.

## Standard workflow

Run all commands from this directory:

```bash
cd examples/internet/b61_k8s_compile
```

Compile once, without deployment-specific parameters:

```bash
python3 ./mini_internet_k8s.py
```

This writes `output/k8s.yaml`, `output/networking.yaml`,
`output/images.yaml`, and the Docker build contexts. The output defaults to
macvlan+VLAN and MTU 1400. It is independent of whether the later deployment
uses local KVM, physical nodes, or multi-host KVM.

Build exactly one environment by choosing its YAML:

```bash
python3 ./k8sTools.py build \
  --input <one-config-yaml> \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

Then deploy, inspect, clean the workload, and finally destroy the infrastructure:

```bash
python3 ./k8sTools.py up -f ./output -k kubeconfig.yaml -d configK3s.yaml

kubectl --kubeconfig ./kubeconfig.yaml get nodes -o wide
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu get pods -o wide

python3 ./k8sTools.py clean -f ./output -k kubeconfig.yaml
python3 ./k8sTools.py destroy -d configK3s.yaml
```

`clean` removes only the SeedEMU workload. `destroy` removes the K3s setup and
the KVM/fabric resources recorded in `configK3s.yaml`; do not delete that file
before cleanup. `down` remains an alias for `clean`.

### Local KVM

```bash
python3 ./k8sTools.py build \
  --input configKvmMacvlan.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

This creates one local master VM and the configured number of local worker VMs.
VM addresses may move when earlier libvirt leases are occupied. After `build`,
use `inventory.yaml`, `configK3s.yaml`, or `kubectl get nodes -o wide` as the
source of truth instead of assuming a specific VM IP.

### Existing physical nodes

```bash
python3 ./k8sTools.py build \
  --input configPhysicalMacvlan.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

This mode installs or reinstalls K3s on the listed machines and creates the
Linux bridge/VXLAN fabric before deployment. `destroy` uninstalls K3s and
removes its CNI state, so use dedicated experiment nodes rather than machines
that host an unrelated Kubernetes cluster. The current Linux-VXLAN workflow
supports exactly two physical nodes.

### Multi-host KVM

```bash
python3 ./k8sTools.py build \
  --input configMultiHostKvmMacvlan.yaml \
  --config-k3s configK3s.yaml \
  --kubeconfig kubeconfig.yaml \
  --inventory inventory.yaml
```

This mode creates routed libvirt networks, routes, VXLAN interfaces, VM disks,
cloud-init data, and K3s VMs on every listed hypervisor. The dedicated `ens3`
NIC carries the VLAN trunk; `ens2` carries VM management traffic. Linux bridge
and VXLAN names derived by the setup may be hashed, so inspect `virsh net-list
--all` and `ip -brief link` instead of scripting against a sample hash.

## Prerequisites

All modes require Python 3.10+, Docker with buildx, `kubectl`, Ansible, SSH,
SCP, and curl. KVM modes also require working libvirt/KVM tools.

The helper can prepare or verify the control host and hypervisors:

```bash
./prepare.sh
./prepare.sh --role hypervisor
./prepare.sh --verify-only
```

The non-verify commands install packages, enable services, change group
membership, and may configure passwordless sudo. Review `./prepare.sh --help`
before using it on a shared host. The supplied YAMLs pin K3s
`v1.29.15+k3s1`; use a compatible kubectl when strict version verification
reports a mismatch.

Example SSH checks, with values replaced by those in your YAML:

```bash
test -r ~/.ssh/seedemu_k8s
ssh -i ~/.ssh/seedemu_k8s ubuntu@192.0.2.11 'sudo -n true'
ssh -i ~/.ssh/seedemu_k8s ubuntu@192.0.2.11 \
  'ip route get 192.0.2.10; ip link show <underlay-interface>'
```

## Files and stage responsibilities

| Path | Role |
| --- | --- |
| `mini_internet_k8s.py` | Compiles the topology to `./output`; normal use takes no arguments. |
| `configKvmMacvlan.yaml` | User input for local KVM. |
| `configPhysicalMacvlan.yaml` | User input for existing physical nodes. |
| `configMultiHostKvmMacvlan.yaml` | User input for KVM VMs distributed over multiple hypervisors. |
| `k8sTools.py` | Thin CLI wrapper for build/up/clean/destroy. |
| `prepare.sh` | Optional prerequisite installer/verifier. |
| `example.yaml` | Static-CI manifest consumed by `seedemu/testing/cli.py`; it enables compile and artifact validation only. |
| `test_compile.py` | Read-only validator for Kubernetes resources, image contexts, networking metadata, and the three deployment renderings. |
| `output/` | Generated compile output; `up` also writes deployment-specific kustomize output here. |
| `configK3s.yaml` | Generated infrastructure state consumed by `up` and `destroy`. |
| `kubeconfig.yaml` | Generated cluster access file consumed by `up`, `clean`, and kubectl. |
| `inventory.yaml` | Optional generated summary of node roles, addresses, and resources. |

The stages are deliberately separate:

1. Compile creates topology manifests and image contexts without requiring a
   live cluster or choosing a machine layout.
2. Build reads one YAML, creates or prepares the machines, installs K3s and
   Multus, and records the selected fabric/CNI parent in `configK3s.yaml`.
3. Up reads `configK3s.yaml`, adapts the compiler output for that deployment,
   creates required VLAN parents, builds/pushes images, applies the workload,
   and waits for readiness.

Add `--keep-temp` to a `k8sTools.py` command when its temporary setup/running
directory must be retained for debugging.

## Static CI

The pull-request `static-checks` job runs the same commands below. They compile
the no-argument B61 example and validate its generated contract without Docker,
K3s, VMs, kubectl, or remote hosts:

```bash
python3 seedemu/testing/cli.py clean \
  examples/internet/b61_k8s_compile/example.yaml
python3 seedemu/testing/cli.py compile \
  examples/internet/b61_k8s_compile/example.yaml \
  --artifact-dir ci-artifacts/B61-kubernetes-compiler-static
python3 seedemu/testing/cli.py test \
  examples/internet/b61_k8s_compile/example.yaml \
  --artifact-dir ci-artifacts/B61-kubernetes-compiler-static
```

The validator checks 57 Deployments, 29 macvlan NADs, unique Kubernetes
resource identities, static IP/VLAN consistency, MTU 1400, all `images.yaml`
entries and Docker build contexts, and local/physical/multi-host rendering to
`ens2`, `br-seedemu`, and `ens3`. CI uploads the JSON summary, command logs,
the three contract YAMLs, and deployment-specific kustomizations.

## Validated experiments

The three checked-in YAMLs were run end to end on 2026-09-18. Each reached
57/57 Running/Ready SeedEMU Pods, passed bidirectional cross-node traffic, and
was subsequently cleaned and destroyed.

| Input | Result |
| --- | --- |
| `configKvmMacvlan.yaml` | Four K3s VMs Ready; AS150 hosts on different VMs exchanged three pings in each direction with 0% loss. |
| `configPhysicalMacvlan.yaml` | Two physical nodes Ready; bridge/macvlan preflight passed; AS170 hosts on different physical nodes exchanged three pings in each direction with 0% loss. |
| `configMultiHostKvmMacvlan.yaml` | Six K3s VMs Ready; cross-hypervisor VLAN/MTU/isolation preflight passed; AS150 hosts on different hypervisors exchanged three pings in each direction with 0% loss. |

Pod placement can change between runs. For a new cross-node check, choose two
Pods on the same simulated subnet whose `NODE` values are different.

## Runtime checks

```bash
kubectl --kubeconfig ./kubeconfig.yaml get nodes -o wide
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu get pods -o wide
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu \
  get events --sort-by='.lastTimestamp'
```

Inspect two candidate Pods and ping between their topology addresses:

```bash
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu exec <first-pod> -- ip -brief address
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu exec <second-pod> -- ip -brief address
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu \
  exec <first-pod> -- ping -I net0 -c 3 <second-topology-ip>
kubectl --kubeconfig ./kubeconfig.yaml -n seedemu \
  exec <second-pod> -- ping -I net0 -c 3 <first-topology-ip>
```

The Multus attachment may initially be named `net1`, while SeedEMU startup can
rename the simulated interface to `net0`; use the name shown by
`ip -brief address`. Under high CPU load, retry transient kubectl TLS or HTTP/2
timeouts with `--request-timeout=120s`.

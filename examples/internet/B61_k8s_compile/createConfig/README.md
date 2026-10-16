# B61 object-based deployment configuration

`buildConfig.py` is a standalone library that builds the **input** YAML for
`K8sTools.py build`. It imports only Python's standard library and PyYAML; it
does not import or invoke `seedemu.k8sTools`. `generateConfigs.py` is a sample
caller. It writes three B61 YAMLs under `generated/` by default and makes no
VM, K3s, network, or Kubernetes changes.

## Files and flow

| File | Role |
| --- | --- |
| `buildConfig.py` | Reusable object API and YAML serializer. |
| `generateConfigs.py` | Editable B61 sample with local KVM, physical and multi-host KVM configurations. |
| `generated/*.yaml` | Generated user input for the later `K8sTools.py build --input` step. |

Install PyYAML if needed, then generate the YAMLs from any working directory:

```bash
python3 examples/internet/B61_k8s_compile/createConfig/generateConfigs.py
```

Use `--output-dir <directory>` to choose another destination. The sample
physical IPs, host names, interfaces and SSH accounts describe one validation
lab; edit `generateConfigs.py` before using its output on your machines. For
example, from `examples/internet/B61_k8s_compile`, the next step for local KVM
is `python3 K8sTools.py build --input createConfig/generated/configKvmMacvlan.yaml
--config-k3s configK3s.yaml --kubeconfig kubeconfig.yaml`. This later command
creates infrastructure; generating YAML does not.

## Smallest configurations

Imports below assume your caller script is beside `buildConfig.py`. The
generated inputs make a basic K3s cluster. To deploy B61's macvlan topology,
call `setFabric("macvlan-vlan")`; the library derives the CNI type and parent.

```python
from buildConfig import SingleHostKvmConfig, PhysicalHostConfig, MultiHostKvmConfig
from buildConfig import RoutedSubnet, Ssh

SingleHostKvmConfig("demo-kvm") \
    .setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519")) \
    .compile("configKvm.yaml")

PhysicalHostConfig("demo-physical") \
    .addNode("master", "master", "192.0.2.10", connection="local",
             ssh=Ssh("alice", "~/.ssh/id_ed25519")) \
    .addNode("worker", "worker", "192.0.2.11", connection="ssh",
             ssh=Ssh("alice", "~/.ssh/id_ed25519")) \
    .compile("configPhysical.yaml")

MultiHostKvmConfig("demo-multi") \
    .addHypervisor("host-a", "192.0.2.10", connection="local", vmCount=2,
                   routedSubnet=RoutedSubnet("10.80.1.0/24", "10.80.1.1")) \
    .addHypervisor("host-b", "192.0.2.11", connection="ssh", vmCount=2,
                   ssh=Ssh("alice", "~/.ssh/id_ed25519"),
                   routedSubnet=RoutedSubnet("10.80.2.0/24", "10.80.2.1")) \
    .setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519")) \
    .compile("configMultiHostKvm.yaml")
```

`SingleHostKvmConfig` defaults to one master and one worker. VM sizes default
to 12 vCPU/10 GiB/80 GB for the master and 6 vCPU/10 GiB/80 GB per worker.
`MultiHostKvmConfig` makes one master on the first hypervisor and uses remaining
VM slots for workers. Its default VM sizes are the same. All three kinds use
the B61 K3s version `v1.29.15+k3s1` and omit `fabric`, `cni`, and
`registry.port` until explicitly set. Physical nodes and hypervisor addresses,
SSH and routed subnets are never invented by the library.

Setters also work as separate statements; chaining is optional:

```python
config = SingleHostKvmConfig("seedemu-b61-kvm")
config.setVmSsh(Ssh("ubuntu", "~/.ssh/id_ed25519"))
config.setFabric("macvlan-vlan")  # derives cniType=macvlan, parent=ens2
config.compile("configKvm.yaml")
```

## Optional controls

All setters return the config object and `compile(path)` validates it before
writing. The generated YAML uses current `kind: kvm`, `physical`, or
`multiHostKvm` fields. Notable optional API calls are:

| API | Generated YAML / use |
| --- | --- |
| `setMaster(VmResources(...), name=...)`, `setWorkers(...)` | `master`, `workers`, and local KVM `defaults`; memory is written as `memoryGiB`. |
| `addVm(name, role, ip, mac, resources)` | Explicit local KVM `nodes[]` instead of generated master/workers. |
| `setManagementNetwork(...)`, `addExtraNetwork(...)`, `setStoragePaths(...)` | Local KVM `kvm.network*`, `kvm.extraNetworks`, and storage paths. |
| `setNodeUnderlayInterface(nodeName, interface)` | Physical `fabric.nodes.<name>.underlayInterface`. |
| `setRoutingTunnel(...)`, `setFabricVxlan(...)` | Multi-host `multiHostKvm.routingTunnel` and `multiHostKvm.fabricVxlan`. |
| `addVlanTrunk(...)` | Multi-host `fabric.vlanTrunks[]`; the CNI master interface must match a trunk NIC. |
| `setFabric(type, masterInterface=..., **options)` | Network backend and matching CNI settings in one call. Local KVM defaults to `ens2`; physical `linux-vxlan` uses `bridgeName`; multi-host VLAN defaults to `ens3`. |
| `setCni(...)` | Compatibility with earlier two-call code; conflicting CNI types are rejected during validation. |
| `setRegistryPort(...)` | Optional registry port override. K3s version is fixed by the library. |

For a complete override example, see `createMultiHostConfig()` in
`generateConfigs.py`. `toDict()` returns a validated copy for inspection;
`compile(path)` writes YAML only. The later `K8sTools.py build` step generates
`configK3s.yaml` and `kubeconfig.yaml`.

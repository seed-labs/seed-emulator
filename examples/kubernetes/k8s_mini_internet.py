#!/usr/bin/env python3
# encoding: utf-8

import os
import json
import sys

# Copied from examples/internet/B00_mini_internet/mini_internet.py
# Adapted for KubernetesCompiler

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
cleaned_sys_path = []
for entry in sys.path:
    normalized = os.path.abspath(entry or os.getcwd())
    if normalized == REPO_ROOT:
        continue
    if os.path.isfile(os.path.join(normalized, "seedemu", "__init__.py")):
        continue
    cleaned_sys_path.append(entry)
sys.path[:] = [REPO_ROOT, *cleaned_sys_path]

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers


def _parse_node_labels_json(raw: str):
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid SEED_NODE_LABELS_JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("SEED_NODE_LABELS_JSON must be a JSON object")
    normalized = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            raise ValueError(f"SEED_NODE_LABELS_JSON['{key}'] must be an object of label->value")
        normalized[str(key)] = {str(k): str(v) for k, v in value.items()}
    return normalized

def run(dumpfile=None, hosts_per_as=2):
    # Initialize Emulator
    emu   = Emulator()
    ebgp  = Ebgp()
    base  = Base()

    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')
    ix105.getPeeringLan().setDisplayName('Huston-105')


    ###############################################################################
    # Create Transit Autonomous Systems

    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2, [100, 101, 102, 105],
           [(100, 101), (101, 102), (100, 105)]
    )

    Makers.makeTransitAs(base, 3, [100, 103, 104, 105],
           [(100, 103), (100, 105), (103, 105), (103, 104)]
    )

    Makers.makeTransitAs(base, 4, [100, 102, 104],
           [(100, 104), (102, 104)]
    )

    ## Tier 2 ASes
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])


    ###############################################################################
    # Create single-homed stub ASes.
    Makers.makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 152, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 162, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 170, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 105, hosts_per_as)

    # An example to show how to add a host with customized IP address
    as154 = base.getAutonomousSystem(154)
    new_host = as154.createHost('host_new').joinNetwork('net0', address = '10.154.0.129')
    from seedemu.core import OptionRegistry, OptionMode


    o = OptionRegistry().sysctl_netipv4_conf_rp_filter({'all': False, 'default': False, 'net0': False}, mode = OptionMode.RUN_TIME)
    new_host.setOption(o)

    o = OptionRegistry().sysctl_netipv4_udp_rmem_min(5000, mode = OptionMode.RUN_TIME)
    new_host.setOption(o)

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer,
    # which means each AS will only export its customers and their own prefixes.
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others.

    ebgp.addPrivatePeerings(100, [2], [3, 4], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [3], [4], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [2], [4], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [3], [4], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [2], [3], PeerRelationship.Peer)

    # To buy transit services from another autonomous system,
    # we will use private peering

    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)


    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    emu.render()

    ###############################################################################
    # Kubernetes Compilation

    registry_prefix = os.environ.get("SEED_REGISTRY", "localhost:5001")
    namespace = os.environ.get("SEED_NAMESPACE", "seedemu")
    cluster_name = os.environ.get("SEED_CLUSTER_NAME", "seedemu-kvtest")
    cni_type = os.environ.get("SEED_CNI_TYPE", "bridge").strip().lower()
    cni_master_interface = os.environ.get("SEED_CNI_MASTER_INTERFACE", "eth0").strip()
    # Using a fixed ':latest' tag across multiple compiled topologies can lead to stale
    # images when the cluster caches tags. Default to Always for correctness.
    image_pull_policy = os.environ.get("SEED_IMAGE_PULL_POLICY", "Always").strip()
    scheduling_strategy = os.environ.get("SEED_SCHEDULING_STRATEGY", SchedulingStrategy.BY_AS_HARD).strip().lower()
    node_labels = _parse_node_labels_json(os.environ.get("SEED_NODE_LABELS_JSON", ""))
    force_colocate = os.environ.get("SEED_FORCE_COLOCATE", "false").strip().lower() in {"1", "true", "yes"}

    if force_colocate and not node_labels and cni_type in {"bridge", "host-local"}:
        single_node = os.environ.get("SEED_SINGLE_NODE", f"{cluster_name}-control-plane").strip()
        colocate_asns = list(range(100, 106)) + [2, 3, 4, 11, 12, 150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
        node_labels = {str(asn): {"kubernetes.io/hostname": single_node} for asn in colocate_asns}
        scheduling_strategy = SchedulingStrategy.CUSTOM

    # Configure the compiler
    k8s = KubernetesCompiler(
        registry_prefix=registry_prefix,
        namespace=namespace,
        use_multus=True,
        internetMapEnabled=False,
        scheduling_strategy=scheduling_strategy,
        node_labels=node_labels,
        cni_type=cni_type,
        cni_master_interface=cni_master_interface,
        generate_services=True,
        image_pull_policy=image_pull_policy,
    )

    # Compile to the output directory.
    output_dir = os.environ.get("SEED_OUTPUT_DIR")
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), 'output_mini_internet')
    elif not os.path.isabs(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), output_dir)
    emu.compile(k8s, output_dir, override=True)

    print(f"Compilation complete. Output generated in {output_dir}")
    print(f"Registry prefix: {registry_prefix}")
    print(f"Namespace: {namespace}")

if __name__ == "__main__":
    hosts_per_as_env = os.environ.get("SEED_HOSTS_PER_AS", "2")
    try:
        hosts_per_as = int(hosts_per_as_env)
    except ValueError as exc:
        raise ValueError(f"Invalid SEED_HOSTS_PER_AS: {hosts_per_as_env}") from exc
    run(hosts_per_as=hosts_per_as)

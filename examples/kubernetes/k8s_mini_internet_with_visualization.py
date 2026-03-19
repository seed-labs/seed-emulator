#!/usr/bin/env python3
# encoding: utf-8

"""
Mini Internet + Visualization (Internet Map) for KubernetesCompiler.

This script is based on the B00_mini_internet topology (via Makers), and then
adds the Internet Map visualization service through the Kubernetes compiler.

It is intended to be "generic and reproducible":
- Registry/namespace/CNI are configured via env vars.
- Output directory is anchored to this script directory (optional override).
"""

import os
import json
import sys

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
from seedemu.services import WebService
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy
from seedemu.core import Emulator, Binding, Filter
from seedemu.utilities import Makers


def _get_output_dir(default_dirname: str) -> str:
    configured = os.environ.get("SEED_OUTPUT_DIR")
    if not configured:
        return os.path.join(os.path.dirname(__file__), default_dirname)
    if os.path.isabs(configured):
        return configured
    return os.path.join(os.path.dirname(__file__), configured)


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


def run():
    hosts_per_as = int(os.environ.get("SEED_HOSTS_PER_AS", "2"))
    registry_prefix = os.environ.get("SEED_REGISTRY", "localhost:5001")
    namespace = os.environ.get("SEED_NAMESPACE", "seedemu")
    cluster_name = os.environ.get("SEED_CLUSTER_NAME", "seedemu-kvtest")
    cni_type = os.environ.get("SEED_CNI_TYPE", "bridge").strip().lower()
    cni_master_interface = os.environ.get("SEED_CNI_MASTER_INTERFACE", "eth0").strip()
    # Using a fixed ':latest' tag across multiple compiled topologies can lead to stale
    # images when the cluster caches tags. Default to Always for correctness.
    image_pull_policy = os.environ.get("SEED_IMAGE_PULL_POLICY", "Always").strip()
    output_dir = _get_output_dir("output_mini_internet_with_viz")
    scheduling_strategy = os.environ.get("SEED_SCHEDULING_STRATEGY", SchedulingStrategy.BY_AS_HARD).strip().lower()
    node_labels = _parse_node_labels_json(os.environ.get("SEED_NODE_LABELS_JSON", ""))
    force_colocate = os.environ.get("SEED_FORCE_COLOCATE", "false").strip().lower() in {"1", "true", "yes"}

    if force_colocate and not node_labels and cni_type in {"bridge", "host-local"}:
        single_node = os.environ.get("SEED_SINGLE_NODE", f"{cluster_name}-control-plane").strip()
        colocate_asns = list(range(100, 106)) + [2, 3, 4, 11, 12, 150, 151, 152, 153, 154, 160, 161, 162, 163, 164, 170, 171]
        node_labels = {str(asn): {"kubernetes.io/hostname": single_node} for asn in colocate_asns}
        scheduling_strategy = SchedulingStrategy.CUSTOM

    emu = Emulator()
    base = Base()
    ebgp = Ebgp()
    web = WebService()

    # Internet Exchanges (IX)
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)

    # Display names help visualization.
    ix100.getPeeringLan().setDisplayName("NYC-100")
    ix101.getPeeringLan().setDisplayName("San Jose-101")
    ix102.getPeeringLan().setDisplayName("Chicago-102")
    ix103.getPeeringLan().setDisplayName("Miami-103")
    ix104.getPeeringLan().setDisplayName("Boston-104")
    ix105.getPeeringLan().setDisplayName("Houston-105")

    # Transit ASes (Tier 1)
    Makers.makeTransitAs(base, 2, [100, 101, 102, 105], [(100, 101), (101, 102), (100, 105)])
    Makers.makeTransitAs(base, 3, [100, 103, 104, 105], [(100, 103), (100, 105), (103, 105), (103, 104)])
    Makers.makeTransitAs(base, 4, [100, 102, 104], [(100, 104), (102, 104)])

    # Transit ASes (Tier 2)
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])

    # Stub ASes with hosts
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

    # Peering via RS (route server)
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])

    # Private peering relationships (provider/customer)
    ebgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4], [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103, [3], [160, 161, 162], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4], [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(105, [3], [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)

    # Add a small, reliable "business signal": install web service on AS150/AS151 host_0.
    # Makers creates host names host_0..host_{hosts_per_as-1} in each stub AS.
    web.install("web150")
    emu.addBinding(Binding("web150", filter=Filter(nodeName="host_0", asn=150)))
    web.install("web151")
    emu.addBinding(Binding("web151", filter=Filter(nodeName="host_0", asn=151)))

    # Layers
    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())
    emu.addLayer(web)
    emu.render()

    k8s = KubernetesCompiler(
        registry_prefix=registry_prefix,
        namespace=namespace,
        use_multus=True,
        internetMapEnabled=True,
        scheduling_strategy=scheduling_strategy,
        node_labels=node_labels,
        cni_type=cni_type,
        cni_master_interface=cni_master_interface,
        generate_services=True,
        image_pull_policy=image_pull_policy,
    )

    k8s.attachInternetMap()
    emu.compile(k8s, output_dir, override=True)

    print("=" * 72)
    print("Mini Internet (with Internet Map) compilation complete.")
    print("=" * 72)
    print(f"Output directory: {output_dir}")
    print(f"Namespace: {namespace}")
    print(f"Registry prefix: {registry_prefix}")
    print(f"CNI type: {cni_type}")
    print("")
    print("Next steps:")
    print(f"  cd {output_dir}")
    print("  ./build_images.sh")
    print(f"  kubectl create ns {namespace} --dry-run=client -o yaml | kubectl apply -f -")
    print(f"  kubectl apply -n {namespace} -f k8s.yaml")
    print("")
    print("Visualization:")
    print("  - Internet Map Service is created as a NodePort by the compiler.")
    print(f"  - Safer access method: kubectl -n {namespace} port-forward service/seedemu-internet-map-service 8080:8080")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
# encoding: utf-8

# Copied from examples/basic/A01_transit_as/transit_as.py
# Adapted for KubernetesCompiler

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy, Platform
from seedemu.core import Emulator, Binding, Filter
import os
import json


def _parse_node_labels_json(raw: str):
    """Parse SEED_NODE_LABELS_JSON into the format expected by KubernetesCompiler."""
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
    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    web     = WebService()

    ###############################################################################
    # Create two Internet Exchanges, where BGP routers peer with one another.
    base.createInternetExchange(100)
    base.createInternetExchange(101)

    ###############################################################################
    # Create and configure a transit autonomous system 

    as2 = base.createAutonomousSystem(2)

    # Create 3 internal networks
    as2.createNetwork('net0')
    as2.createNetwork('net1')
    as2.createNetwork('net2')

    # Create four routers and link them in a linear structure:
    # ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
    # r1 and r4 are BGP routers because they are connected to Internet exchanges
    as2.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
    as2.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
    as2.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
    as2.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')

    ###############################################################################
    # Create and configure two stub autonomous systems

    # AS-150 connects to ix100
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as150.createHost('web').joinNetwork('net0')
    web.install('web150')
    emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))

    # AS-151 connects to ix101
    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    as151.createHost('web').joinNetwork('net0')
    web.install('web151')
    emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))

    ###############################################################################
    # Peering at Internet Exchanges

    ebgp.addRsPeer(100, 2)
    ebgp.addRsPeer(101, 2)
    ebgp.addRsPeer(100, 150)
    ebgp.addRsPeer(101, 151)

    ###############################################################################
    # Rendering

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    # Transit topology needs IGP + iBGP to propagate reachability across
    # internal routers (r1-r4) and distribute external prefixes within AS2.
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(web)

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
    scheduling_strategy = os.environ.get("SEED_SCHEDULING_STRATEGY", SchedulingStrategy.AUTO).strip().lower()
    node_labels = _parse_node_labels_json(os.environ.get("SEED_NODE_LABELS_JSON", ""))
    force_colocate = os.environ.get("SEED_FORCE_COLOCATE", "false").strip().lower() in {"1", "true", "yes"}

    # Bridge/host-local are "node-local" in this workflow. In kind, cross-node connectivity for
    # Multus secondary networks can be fragile. If the user didn't provide explicit placement,
    # co-locate all ASes onto a single node for deterministic local runs.
    if force_colocate and not node_labels and cni_type in {"bridge", "host-local"}:
        single_node = os.environ.get("SEED_SINGLE_NODE", f"{cluster_name}-control-plane").strip()
        # Transit topology ASNs: IX(100/101), transit(2), stubs(150/151)
        colocate_asns = [100, 101, 2, 150, 151]
        node_labels = {str(asn): {"kubernetes.io/hostname": single_node} for asn in colocate_asns}
        scheduling_strategy = SchedulingStrategy.CUSTOM

    # Configure the compiler
    # registry_prefix: where to push images (e.g., "docker.io/myuser" or "127.0.0.1:5001")
    # namespace: the K8s namespace to deploy into
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
        output_dir = os.path.join(os.path.dirname(__file__), 'output_transit_as')
    elif not os.path.isabs(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), output_dir)
    emu.compile(k8s, output_dir, override=True)

    print(f"Compilation complete. Output generated in {output_dir}")
    print(f"Registry prefix: {registry_prefix}")
    print(f"Namespace: {namespace}")

if __name__ == '__main__':
    run()

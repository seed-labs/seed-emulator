#!/usr/bin/env python3
# encoding: utf-8

"""
k8s_multinode_demo.py - Demonstrates multi-node Kubernetes deployment features

This example shows how to use the new KubernetesCompiler features:
- Scheduling strategies (by_as, by_role, custom)
- Resource limits (requests/limits)
- CNI type configuration (bridge, macvlan, ipvlan)
- Service generation

Usage:
    python3 k8s_multinode_demo.py [macvlan|ipvlan|bridge]
"""

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy, Platform
from seedemu.core import Emulator, Binding, Filter
import os
import sys


def run(cni_type: str = "bridge"):
    # Initialize the emulator and layers
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    web = WebService()

    ###############################################################################
    # Create Internet Exchanges
    base.createInternetExchange(100)
    base.createInternetExchange(101)

    ###############################################################################
    # Create and set up AS-150 (on node1)
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as150.createHost('web').joinNetwork('net0')
    web.install('web150')
    emu.addBinding(Binding('web150', filter=Filter(nodeName='web', asn=150)))

    ###############################################################################
    # Create and set up AS-151 (on node2)
    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    as151.createHost('web').joinNetwork('net0')
    web.install('web151')
    emu.addBinding(Binding('web151', filter=Filter(nodeName='web', asn=151)))

    ###############################################################################
    # Create and set up Transit AS-2
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork('net0')
    as2.createNetwork('net1')
    as2.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
    as2.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
    as2.createRouter('r3').joinNetwork('net1').joinNetwork('ix101')

    ###############################################################################
    # Peering
    ebgp.addRsPeer(100, 2)
    ebgp.addRsPeer(100, 150)
    ebgp.addRsPeer(101, 2)
    ebgp.addRsPeer(101, 151)

    ###############################################################################
    # Rendering
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(web)

    emu.render()

    ###############################################################################
    # Kubernetes Compilation with Multi-Node Features

    # Custom node labels for scheduling
    # This maps AS numbers to specific Kubernetes nodes
    node_labels = {
        "150": {"kubernetes.io/hostname": "node1"},
        "151": {"kubernetes.io/hostname": "node2"},
        "2": {"kubernetes.io/hostname": "node3"},  # Transit AS on node3
    }

    # Resource limits for all pods
    default_resources = {
        "requests": {"cpu": "100m", "memory": "128Mi"},
        "limits": {"cpu": "500m", "memory": "512Mi"}
    }

    # Create Kubernetes compiler with multi-node features
    k8s = KubernetesCompiler(
        registry_prefix="127.0.0.1:5001",
        namespace="seedemu",
        use_multus=True,
        internetMapEnabled=True,
        
        # Multi-node scheduling: pods with same AS go to same node
        scheduling_strategy=SchedulingStrategy.BY_AS,
        node_labels=node_labels,
        
        # Resource management
        default_resources=default_resources,
        
        # CNI type for cross-node networking
        cni_type=cni_type,
        cni_master_interface="eth0",
        
        # Generate K8s Services for nodes with exposed ports
        generate_services=True,
        service_type="ClusterIP"
    )

    # Attach visualization
    k8s.attachInternetMap()

    # Compile
    output_dir = os.path.join(os.path.dirname(__file__), f'output_multinode_{cni_type}')
    emu.compile(k8s, output_dir, override=True)

    print(f"""
================================================================================
Multi-Node Kubernetes Deployment Generated!
================================================================================

Output Directory: {output_dir}
CNI Type: {cni_type}
Scheduling Strategy: CUSTOM (by AS number)

Node Placement:
  - AS150 (web + router) -> node1
  - AS151 (web + router) -> node2
  - AS2 (transit)        -> node3

Resource Limits:
  - CPU: 100m-500m per pod
  - Memory: 128Mi-512Mi per pod

Next Steps:
  1. Label your K8s nodes:
     kubectl label node node1 kubernetes.io/hostname=node1
     kubectl label node node2 kubernetes.io/hostname=node2
     kubectl label node node3 kubernetes.io/hostname=node3

  2. Build and push images:
     cd {output_dir} && ./build_images.sh

  3. Deploy to K8s:
     kubectl create ns seedemu
     kubectl apply -f k8s.yaml

  4. Verify pod placement:
     kubectl get pods -n seedemu -o wide

================================================================================
""")


if __name__ == '__main__':
    cni_type = "bridge"
    if len(sys.argv) > 1:
        cni_type = sys.argv[1].lower()
        if cni_type not in ["bridge", "macvlan", "ipvlan"]:
            print(f"Unknown CNI type: {cni_type}")
            print("Usage: python3 k8s_multinode_demo.py [macvlan|ipvlan|bridge]")
            sys.exit(1)
    
    run(cni_type)

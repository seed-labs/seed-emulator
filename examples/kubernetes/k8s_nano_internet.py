#!/usr/bin/env python3
# encoding: utf-8

# Copied from examples/basic/A20_nano_internet/nano_internet.py
# Adapted for KubernetesCompiler

import os, sys

from seedemu.compiler import KubernetesCompiler
from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, Routing
from seedemu.services import DomainNameService, WebService

def run():
    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    web     = WebService()
    dns     = DomainNameService()

    ###############################################################################
    # Create Internet exchanges 

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix100.getPeeringLan().setDisplayName('New York-100')
    ix101.getPeeringLan().setDisplayName('Chicago-101')

    ###############################################################################
    # Create and set up a transit AS (AS-3)

    as3 = base.createAutonomousSystem(3)

    # Create 3 internal networks
    as3.createNetwork('net0')
    as3.createNetwork('net1')
    as3.createNetwork('net2')

    # Create four routers and link them in a linear structure:
    # ix100 <--> r1 <--> r2 <--> r3 <--> r4 <--> ix101
    # r1 and r4 are BGP routers because they are connected to Internet exchanges
    as3.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
    as3.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
    as3.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
    as3.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')

    ###############################################################################
    # Create and set up a stub AS (AS-150) connecting to ix100

    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as150.createHost('web').joinNetwork('net0')
    as150.createHost('dns').joinNetwork('net0')
    web.install('web150')
    dns.install('dns150')
    emu.addBinding(Binding('web150', filter = Filter(nodeName = 'web', asn = 150)))
    emu.addBinding(Binding('dns150', filter = Filter(nodeName = 'dns', asn = 150)))

    ###############################################################################
    # Create and set up another stub AS (AS-151) connecting to ix101

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    as151.createHost('web').joinNetwork('net0')
    as151.createHost('dns').joinNetwork('net0')
    web.install('web151')
    dns.install('dns151')
    emu.addBinding(Binding('web151', filter = Filter(nodeName = 'web', asn = 151)))
    emu.addBinding(Binding('dns151', filter = Filter(nodeName = 'dns', asn = 151)))

    ###############################################################################
    # Create and set up another stub AS (AS-152) connecting to ix101

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork('net0')
    as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    as152.createHost('web').joinNetwork('net0')
    web.install('web152')
    emu.addBinding(Binding('web152', filter = Filter(nodeName = 'web', asn = 152)))

    ###############################################################################
    # Peering at Internet Exchanges

    ebgp.addRsPeer(100, 3)
    ebgp.addRsPeer(101, 3)
    ebgp.addRsPeer(100, 150)
    ebgp.addRsPeer(101, 151)
    ebgp.addRsPeer(101, 152)

    ###############################################################################
    # Rendering

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(web)
    emu.addLayer(dns)

    emu.render()

    ###############################################################################
    # Kubernetes Compilation

    # Configure the compiler
    # registry_prefix: Where to push images (e.g., "docker.io/myuser" or "localhost:5000")
    # namespace: The K8s namespace to deploy into
    registry_prefix = os.environ.get("SEED_REGISTRY", "localhost:5000").strip()
    namespace = os.environ.get("SEED_NAMESPACE", "seedemu").strip()
    cni_type = os.environ.get("SEED_CNI_TYPE", "bridge").strip().lower()
    cni_master_interface = os.environ.get("SEED_CNI_MASTER_INTERFACE", "eth0").strip()
    image_pull_policy = os.environ.get("SEED_IMAGE_PULL_POLICY", "Always").strip()
    k8s = KubernetesCompiler(
        registry_prefix=registry_prefix,
        namespace=namespace,
        use_multus=True,
        cni_type=cni_type,
        cni_master_interface=cni_master_interface,
        image_pull_policy=image_pull_policy,
    )

    output_dir = os.environ.get("SEED_OUTPUT_DIR")
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), 'output_nano_internet')
    elif not os.path.isabs(output_dir):
        output_dir = os.path.join(os.path.dirname(__file__), output_dir)
    emu.compile(k8s, output_dir, override=True)

    print(f"Compilation complete. Output generated in {output_dir}")
    print(f"Registry prefix: {registry_prefix}")
    print(f"Namespace: {namespace}")

if __name__ == '__main__':
    run()

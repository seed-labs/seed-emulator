#!/usr/bin/env python3
# encoding: utf-8

# Copied from examples/basic/A01_transit_as/transit_as.py
# Adapted for KubernetesCompiler

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import KubernetesCompiler, Platform
from seedemu.core import Emulator, Binding, Filter
import os

def run():
    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
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
    emu.addLayer(web)

    emu.render()

    ###############################################################################
    # Kubernetes Compilation

    # Configure the compiler
    # registry_prefix: Where to push images (e.g., "docker.io/myuser" or "localhost:5000")
    # namespace: The K8s namespace to deploy into
    k8s = KubernetesCompiler(
        registry_prefix="localhost:5000",
        namespace="seedemu"
    )

    # Compile to the 'output' directory
    output_dir = os.path.join(os.path.dirname(__file__), 'output_transit_as')
    emu.compile(k8s, output_dir, override=True)

    print(f"Compilation complete. Output generated in {output_dir}")

if __name__ == '__main__':
    run()

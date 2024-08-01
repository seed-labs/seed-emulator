#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship, Ibgp, Ospf
from seedemu.services import WebService
from seedemu.core import Emulator, Binding, Filter
from seedemu.raps import OpenVpnRemoteAccessProvider
from seedemu.compiler import Docker, Platform
import os, sys

def run(dumpfile = None):
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)
    
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    web     = WebService()
    ovpn    = OpenVpnRemoteAccessProvider()

    ###############################################################################

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    ###############################################################################
    # Create a transit AS (AS-150)

    as150 = base.createAutonomousSystem(150)

    as150.createNetwork('net0')
    as150.createNetwork('net1')
    as150.createNetwork('net2')

    # Create 4 routers: r1 and r4 are BGP routers (connected to internet exchange) 
    as150.createRouter('r1').joinNetwork('ix100').joinNetwork('net0')
    as150.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
    as150.createRouter('r3').joinNetwork('net1').joinNetwork('net2')
    as150.createRouter('r4').joinNetwork('net2').joinNetwork('ix101')


    ###############################################################################
    # Create AS-151

    as151 = base.createAutonomousSystem(151)

    # Create a network and enable the access from real world
    as151.createNetwork('net0').enableRemoteAccess(ovpn)
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

    # Create a web host
    as151.createHost('web').joinNetwork('net0')
    web.install('web1')
    emu.addBinding(Binding('web1', filter = Filter(asn = 151, nodeName = 'web')))


    ###############################################################################
    # Create AS-152

    as152 = base.createAutonomousSystem(152)

    # Create a network and enable the access from real world
    as152.createNetwork('net0').enableRemoteAccess(ovpn)
    as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')

    # Create a web host
    as152.createHost('web').joinNetwork('net0')
    web.install('web2')
    emu.addBinding(Binding('web2', filter = Filter(asn = 152, nodeName = 'web')))


    ###############################################################################
    # Create a real-world AS. 
    # AS11872 is the Syracuse University's autonomous system
    # The network prefixes announced by this AS will be collected from the real Internet
    # Packets coming into this AS will be routed out to the real world. 

    as11872 = base.createAutonomousSystem(11872)
    as11872.createRealWorldRouter('rw').joinNetwork('ix101', '10.101.0.118')


    ###############################################################################
    # BGP peering 

    ebgp.addPrivatePeering(100, 150, 151,   abRelationship = PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 150, 152,   abRelationship = PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 150, 11872, abRelationship = PeerRelationship.Unfiltered)


    ###############################################################################
    # Rendering

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(web)

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        ###############################################################################
        # Compilation 

        emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == "__main__":
    run()
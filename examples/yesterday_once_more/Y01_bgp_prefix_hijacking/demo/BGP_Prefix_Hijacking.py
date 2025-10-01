#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers
import os, sys

def run(dumpfile=None, hosts_per_as=2): 
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

    emu   = Emulator()
    ebgp  = Ebgp()
    base  = Base()
    ovpn = OpenVpnRemoteAccessProvider()
    
    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    ix106 = base.createInternetExchange(106)
    ix107 = base.createInternetExchange(107)
    ix108 = base.createInternetExchange(108)
    ix109 = base.createInternetExchange(109)
    
    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('Beijing-100')
    ix101.getPeeringLan().setDisplayName('Shanghai-101')
    ix102.getPeeringLan().setDisplayName('Hangzhou-102')
    ix103.getPeeringLan().setDisplayName('Wuhan-103')
    ix104.getPeeringLan().setDisplayName('Guanzhou-104')
    ix105.getPeeringLan().setDisplayName('Chongqing-105')
    ix106.getPeeringLan().setDisplayName('Lanzhou-106')
    ix107.getPeeringLan().setDisplayName('Kunming-107')
    ix108.getPeeringLan().setDisplayName('Nanchang-108')
    ix109.getPeeringLan().setDisplayName('Changchun-109')
    
    
    ###############################################################################
    # Create Transit Autonomous Systems 
    
    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2, [100, 101, 102, 107], 
           [(100, 101), (101, 102), (100, 107), (102, 107)] 
    )
    
    Makers.makeTransitAs(base, 3, [100, 103, 104, 107, 108], 
           [(100, 103), (103, 104), (104, 107), (107, 108)]
    )
    
    Makers.makeTransitAs(base, 4, [100, 102, 104, 106, 108], 
           [(100, 104), (102, 104), (102, 106), (100, 108)]
    )

    
    ## Tier 2 ASes
    Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
    Makers.makeTransitAs(base, 12, [101, 104, 109], [(101, 104), (104, 109)])
    Makers.makeTransitAs(base, 13, [103, 106], [(103, 106)])
    
    
    ###############################################################################
    # Create single-homed stub ASes. 
    Makers.makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 152, 100, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 155, 101, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 156, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 157, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 158, 102, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 159, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 162, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 165, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 166, 105, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 167, 106, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 168, 106, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 169, 106, hosts_per_as)


    Makers.makeStubAsWithHosts(emu, base, 170, 107, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 107, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 172, 107, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 173, 108, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 174, 108, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 175, 108, hosts_per_as)

    Makers.makeStubAsWithHosts(emu, base, 176, 109, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 177, 109, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 178, 109, hosts_per_as)

    # Create a real-world router, attach it to ix-101 and peer with AS-2
    as77777 = base.createAutonomousSystem(77777)
    as77777.createRealWorldRouter(name='real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1'])\
          .joinNetwork('ix102', address = '10.102.0.177')
    ebgp.addPrivatePeerings(102, [2],  [77777], PeerRelationship.Provider)


    # Create a new AS as the BGP attacker, attach it to ix-105 and peer with AS-11
    as199 = base.createAutonomousSystem(199)
    as199.createNetwork('net0')
    as199.createHost('host-0').joinNetwork('net0')
    as199.createRouter('attacker-bgp').joinNetwork('net0').joinNetwork('ix105')
    ebgp.addPrivatePeerings(105, [11],  [199], PeerRelationship.Provider)

    as153 = base.getAutonomousSystem(153)
    as153.getNetwork("net0").enableRemoteAccess(ovpn)
    
    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 
    
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(107, [2, 3])
    ebgp.addRsPeers(108, [3, 4])
    
    # To buy transit services from another autonomous system, 
    # we will use private peering  
    
    ebgp.addPrivatePeerings(100, [2],  [150, 151, 152], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [4],  [151, 152], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12, 155], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [153, 154], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(102, [2],  [11, 156, 157, 158], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(103, [3],  [13, 159], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [13],  [160, 161], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [162], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [163, 164], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(105, [11], [165, 166], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(106, [13], [167, 168, 169], PeerRelationship.Provider)
    
    ebgp.addPrivatePeerings(107, [2], [170, 171], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(107, [3], [172], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(108, [3], [173], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(108, [4], [174, 175], PeerRelationship.Provider)


    ebgp.addPrivatePeerings(109, [12], [176, 177, 178], PeerRelationship.Provider)
    
    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp) 
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    if dumpfile is not None: 
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
    else: 
        emu.render()

        # Attach the Internet Map container to the emulator
        docker = Docker(platform=platform, internetMapEnabled=False)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()

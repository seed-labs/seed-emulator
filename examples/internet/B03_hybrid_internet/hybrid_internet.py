#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os, sys

def run(dumpfile = None, hosts_per_as=2):
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


    ###############################################################################
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    web     = WebService()
    ovpn    = OpenVpnRemoteAccessProvider()


    ###############################################################################
    # Create Internet Exchanges 
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
    # Create single-homed stub ASes. "None" means create a host only 

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

    # Allow outside computers to VPN into AS-152's network
    as152 = base.getAutonomousSystem(152)
    as152.getNetwork('net0').enableRemoteAccess(ovpn)

    ###############################################################################
    # Create real-world AS.
    # AS11872 is the Syracuse University's autonomous system

    as11872 = base.createAutonomousSystem(11872)
    as11872.createRealWorldRouter('rw-11872-syr').joinNetwork('ix102', '10.102.0.118')

    ###############################################################################
    # Create hybrid AS.
    # AS99999 is the emulator's autonomous system that routes the traffics 
    #   to the real-world internet
    as99999 = base.createAutonomousSystem(99999)
    as99999.createRealWorldRouter('rw-real-world', 
        prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')



    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is 
    # PeerRelationship.Peer, which means each AS will only export its customers 
    # and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 

    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])

    # To buy transit services from another autonomous system, 
    # we will use private peering  

    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150, 99999], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154, 11872], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103, [3],  [160, 161, 162 ], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)


    ###############################################################################
    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(web)

    if dumpfile is not None:
        # Save it to a component file, so it can be used by other emulators
        emu.dump(dumpfile) 
    else:
        emu.render()
        emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == "__main__":
    run()

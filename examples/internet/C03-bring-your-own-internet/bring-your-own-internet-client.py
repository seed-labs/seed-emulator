#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

for i in range(0, 4):
    ###############################################################################
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    web     = WebService()
    dhcp    = DHCPService()
    ovpn    = OpenVpnRemoteAccessProvider()

    A=3*i
    B=3*i
    C=2*i
    D=10*(i-1)

    ###############################################################################

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102+A)
    ix103 = base.createInternetExchange(103+A)
    ix104 = base.createInternetExchange(104+A)

    ###############################################################################
    # Create Transit Autonomous Systems 

    ## Tier 1 ASes
    Makers.makeTransitAs(base, 2+B, [100, 101, 102+A], 
        [(100, 101), (101, 102+A)] 
    )

    Makers.makeTransitAs(base, 3+B, [100, 103+A, 104+A], 
        [(100, 103+A), (103+A, 104+A)]
    )

    Makers.makeTransitAs(base, 4+B, [100, 102+A, 104+A], 
        [(100, 104+A), (102+A, 104+A)]
    )

    ## Tier 2 ASes
    Makers.makeTransitAs(base, 51+C, [102+A, 103+A], [(102+A, 103+A)])
    Makers.makeTransitAs(base, 52+C, [101, 104+A], [(101, 104+A)])


    ###############################################################################
    # Create single-homed stub ASes. "None" means create a host only 

    Makers.makeStubAs(emu, base, 165+D, 100, [web, None])
    Makers.makeStubAs(emu, base, 166+D, 100, [web, dhcp, None])

    Makers.makeStubAs(emu, base, 167+D, 101, [None, None])
    Makers.makeStubAs(emu, base, 168+D, 101, [web, None, None])

    Makers.makeStubAs(emu, base, 169+D, 102+A, [None, web])

    Makers.makeStubAs(emu, base, 170+D, 103+A, [web, None])
    Makers.makeStubAs(emu, base, 171+D, 103+A, [web, dhcp, None])
    Makers.makeStubAs(emu, base, 172+D, 103+A, [web, None])

    Makers.makeStubAs(emu, base, 173+D, 104+A, [web, None])
    Makers.makeStubAs(emu, base, 174+D, 104+A, [None, None])

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 

    ebgp.addRsPeers(102+A, [2+B, 4+B])
    ebgp.addRsPeers(104+A, [3+B, 4+B])

    # To buy transit services from another autonomous system, 
    # we will use private peering  
    ebgp.addPrivatePeering(100, 2+B, 3+B, PeerRelationship.Peer)
    ebgp.addPrivatePeering(100, 3+B, 4+B, PeerRelationship.Peer)
    ebgp.addPrivatePeering(100, 2+B, 4+B, PeerRelationship.Peer)


    ebgp.addPrivatePeerings(100, [2+B],  [165+D, 166+D], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3+B],  [165+D], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2+B],  [52+C], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [52+C], [167+D, 168+D], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102+A, [2+B, 4+B],  [51+C, 169+D], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102+A, [51+C], [169+D], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103+A, [3+B],  [170+D, 171+D, 172+D ], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104+A, [3+B, 4+B], [52+C], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104+A, [4+B],  [173+D], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104+A, [52+C], [174+D], PeerRelationship.Provider)

    ###############################################################################
    base.setNameServers(['10.153.0.53'])

    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(web)
    emu.addLayer(dhcp)

    # Save it to a component file, so it can be used by other emulators
    emu.dump('base-component.bin')

    # Uncomment the following if you want to generate the final emulation files
    emu.render()
    #print(dns.getZone('.').getRecords())
    emu.compile(Docker(), './output_'+str(i), override=True)


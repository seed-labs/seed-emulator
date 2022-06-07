#!/usr/bin/env python3
# encoding: utf-8
import sys, os
from seedemu import *

def makeStubAs(emu: Emulator, base: Base, asn: int, exchange: int):

    # Create AS and internal network
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork("net0")

    # Create a BGP router
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork("net0")
    router.joinNetwork('ix{}'.format(exchange))

    for counter in range(5):
       host = stub_as.createHost('host_{}'.format(counter))
       host.joinNetwork("net0")


###############################################################################
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
###############################################################################
ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix102 = base.createInternetExchange(102)

ix103 = base.createInternetExchange(103)
ix104 = base.createInternetExchange(104)


Makers.makeTransitAs(base, 6, [100, 101], [(100, 101)])
Makers.makeTransitAs(base, 2, [101, 102], [(101, 102)])
Makers.makeTransitAs(base, 3, [102, 103], [(102, 103)])
Makers.makeTransitAs(base, 4, [103, 104], [(103, 104)])
Makers.makeTransitAs(base, 5, [104, 100], [(104, 100)])


ebgp.addRsPeers(100, [6, 5])
ebgp.addRsPeers(101, [6, 2])
ebgp.addRsPeers(102, [2, 3])
ebgp.addRsPeers(103, [3, 4])
ebgp.addRsPeers(104, [4, 5])

# Create single-homed stub ASes. "None" means create a host only 
makeStubAs(emu, base, 150, 100)
makeStubAs(emu, base, 151, 101)
makeStubAs(emu, base, 152, 102)
makeStubAs(emu, base, 153, 103)
makeStubAs(emu, base, 154, 104)


ebgp.addPrivatePeerings(101, [6],  [2], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [2],  [3], PeerRelationship.Provider)
ebgp.addPrivatePeerings(103, [3],  [4], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [4],  [5], PeerRelationship.Provider)
ebgp.addPrivatePeerings(100, [5],  [6], PeerRelationship.Provider)


ebgp.addPrivatePeerings(100, [6],  [150], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [2],  [151], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [3],  [152], PeerRelationship.Provider)
ebgp.addPrivatePeerings(103, [4],  [153], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [5],  [154], PeerRelationship.Provider)


# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)

emu.dump('base-component.bin')

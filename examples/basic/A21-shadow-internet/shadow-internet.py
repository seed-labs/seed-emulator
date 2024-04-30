#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

# Create the Emulator 
emu = Emulator()

# Create the base layer
base = Base()

# Create a  web service layer
web  = WebService()



###############################################################################
# Create Internet exchanges

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)
ix101 = base.createInternetExchange(102)
ix100.getPeeringLan().setDisplayName('New York-100')
ix101.getPeeringLan().setDisplayName('Chicago-101')
ix101.getPeeringLan().setDisplayName('Houston-102')


###############################################################################
# Create transit and stub ASes

Makers.makeTransitAs(base, 4, [100, 101, 102],
       [(100, 101), (101, 102), (100, 102)]
)

Makers.makeStubAs(emu, base, 160, 100, [web, None])
Makers.makeStubAs(emu, base, 161, 101, [None, web])
Makers.makeStubAs(emu, base, 162, 102, [None, None])
Makers.makeStubAs(emu, base, 163, 102, [None, None])


###############################################################################
# Allow outside computer to VPN into AS-152's network

ovpn    = OpenVpnRemoteAccessProvider()

as162 = base.getAutonomousSystem(162)
as162.getNetwork('net0').enableRemoteAccess(ovpn)


###############################################################################
# Create real-world AS.
# AS11872 is the Syracuse University's autonomous system

as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw').joinNetwork('ix100', '10.100.0.118')


###############################################################################
# BGP peering

# Create the Ebgp layer
ebgp = Ebgp()

ebgp.addPrivatePeerings(100, [4],  [160, 11872], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [4],  [161], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [4],  [162, 163], PeerRelationship.Provider)
ebgp.addPrivatePeering (102, 162,  163, PeerRelationship.Peer)



###############################################################################

emu.addLayer(base)
emu.addLayer(ebgp)
emu.addLayer(web)

emu.addLayer(Routing())
emu.addLayer(Ibgp())
emu.addLayer(Ospf())

###############################################################################
# Rendering: This is where the actual binding happens

emu.render()
#emu.dump('base-component.bin')

# Generate the Docker files
emu.compile(Docker(), './output')


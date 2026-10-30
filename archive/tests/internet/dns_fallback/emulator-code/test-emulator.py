#!/usr/bin/env python3
# encoding: utf-8

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.services import DomainNameService, DomainNameCachingService, ReverseDomainNameService

# Build a minimal Internet with authoritative DNS (no master), a local caching DNS, and a client host.
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
osfp    = Ospf()

# Internet Exchange
ix100 = base.createInternetExchange(100)
ix100.getPeeringLan().setDisplayName('IX-100')

# Authoritative side: AS150
as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('r150').joinNetwork('net0').joinNetwork('ix100')
as150.createHost('dns-a').joinNetwork('net0', address='10.150.0.10')
as150.createHost('dns-b').joinNetwork('net0', address='10.150.0.11')
as150.createHost('dns-com').joinNetwork('net0', address='10.150.0.12')
as150.createHost('dns-ex').joinNetwork('net0', address='10.150.0.13')
as150.createHost('dns-rev').joinNetwork('net0', address='10.150.0.14')

# Client side: AS151
as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('r151').joinNetwork('net0').joinNetwork('ix100')
# LDNS host and two end hosts
as151.createHost('local-dns').joinNetwork('net0', address='10.151.0.53')
as151.createHost('svc1').joinNetwork('net0', address='10.151.0.7')
as151.createHost('client1').joinNetwork('net0')

# EBGP peering between two ASes via IX100
ebgp.addPrivatePeering(100, 150, 151, abRelationship=PeerRelationship.Provider)

# Add layers
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(osfp)

# Authoritative DNS without explicit master
dns = DomainNameService()
# Root zone (no master)
dns.install('a-root').addZone('.')
dns.install('b-root').addZone('.')
# com. TLD and a business zone example32.com. (no setMaster on example zone)
dns.install('ns-com').addZone('com.')
dns.install('ns-example32-com').addZone('example32.com.')
# Reverse zone in-addr.arpa.
dns.install('ns-rev').addZone('in-addr.arpa.')

# Add an A record for example32.com to point to svc1 in AS151
dns.getZone('example32.com.').addRecord('@ A 10.151.0.7')

emu.addLayer(dns)

# Local Caching DNS (LDNS)
ldns = DomainNameCachingService(autoRoot=True)
ldns_server = ldns.install('global-dns')
# Forward a business zone but provide an invalid vnode name to trigger zone-server list fallback
ldns_server.addForwardZone('example32.com.', 'invalid-vnode-name')

emu.addLayer(ldns)

# Reverse DNS service to populate PTR records
rdns = ReverseDomainNameService()
emu.addLayer(rdns)

# Bind authoritative vnodes to specific hosts
emu.addBinding(Binding('a-root',              filter=Filter(asn=150, nodeName='dns-a'),   action=Action.FIRST))
emu.addBinding(Binding('b-root',              filter=Filter(asn=150, nodeName='dns-b'),   action=Action.FIRST))
emu.addBinding(Binding('ns-com',              filter=Filter(asn=150, nodeName='dns-com'), action=Action.FIRST))
emu.addBinding(Binding('ns-example32-com',    filter=Filter(asn=150, nodeName='dns-ex'),  action=Action.FIRST))
emu.addBinding(Binding('ns-rev',              filter=Filter(asn=150, nodeName='dns-rev'), action=Action.FIRST))
emu.addBinding(Binding('global-dns',          filter=Filter(asn=151, nodeName='local-dns'), action=Action.FIRST))

# Ensure resolv.conf on all nodes uses the local DNS server
base.setNameServers(['10.151.0.53'])

# Render and compile
emu.render()
emu.compile(Docker(), './output', override=True)

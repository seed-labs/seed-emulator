#!/usr/bin/env python3
# encoding: utf-8

from seedemu.compiler import Docker
from seedemu.core import Binding, Emulator, Filter, Action
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, Routing, PeerRelationship
from seedemu.services import DomainNameCachingService, DomainNameService, CAService, CAServer, WebService, WebServer, RootCAStore

emu = Emulator()
base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
caStore = RootCAStore(caDomain='ca.internal')
ca = CAService()
web = WebService()

###########################################################

ix100 = base.createInternetExchange(100)
ix101 = base.createInternetExchange(101)

ix100.getPeeringLan().setDisplayName('NYC-100')
ix101.getPeeringLan().setDisplayName('San Jose-101')

as2 = base.createAutonomousSystem(2)

as2.createNetwork('net0')

# Create two routers and link them in a linear structure:
# ix100 <--> r1 <--> r2 <--> ix101
# r1 and r2 are BGP routers because they are connected to internet exchanges
as2.createRouter('r1').joinNetwork('net0').joinNetwork('ix100')
as2.createRouter('r2').joinNetwork('net0').joinNetwork('ix101')

caServer: CAServer = ca.install('ca-vnode')
caServer.setCAStore(caStore)
caServer.installCACert()

as150 = base.createAutonomousSystem(150)
as150.createNetwork('net0')
as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
for i in range(6):
    host = as150.createHost('host_{}'.format(i)).joinNetwork('net0')
# Do not install the CA cert on the CA host
host_ca = as150.createHost('ca').joinNetwork('net0', address='10.150.0.7')

as151 = base.createAutonomousSystem(151)
as151.createNetwork('net0')
as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
for i in range(2):
    host = as151.createHost('host_{}'.format(i)).joinNetwork('net0')
host_web = as151.createHost('web').joinNetwork('net0', address='10.151.0.7')

webServer: WebServer = web.install('web-vnode')
webServer.setServerNames(['user.internal'])
webServer.setCAServer(caServer).enableHTTPS()
emu.addBinding(Binding('ca-vnode', filter=Filter(nodeName='ca'), action=Action.FIRST))
emu.addBinding(Binding('web-vnode', filter=Filter(nodeName='web'), action=Action.FIRST))


ebgp.addPrivatePeering(100, 2, 150, abRelationship = PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 2, 151, abRelationship = PeerRelationship.Provider)

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(ca)
emu.addLayer(web)

###########################################################
# Create a DNS layer
dns = DomainNameService()

# Create two nameservers for the root zone
dns.install('a-root-server').addZone('.').setMaster()   # Master server
dns.install('b-root-server').addZone('.')               # Slave server

# Create nameservers for TLD and ccTLD zones
# https://itp.cdn.icann.org/en/files/root-system/identification-tld-private-use-24-01-2024-en.pdf
dns.install('a-internal-server').addZone('internal.').setMaster()  
dns.install('b-internal-server').addZone('internal.')

dns.install('ns-ca-internal').addZone('ca.internal.')
dns.install('ns-user-internal').addZone('user.internal.')

# Add records to zones
dns.getZone('ca.internal.').addRecord('@ A 10.150.0.7')
dns.getZone('user.internal.').addRecord('@ A 10.151.0.7')

emu.addLayer(dns)

emu.addBinding(Binding('a-root-server', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('a-internal-server', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('b-internal-server', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('ns-ca-internal', filter=Filter(asn=150), action=Action.FIRST))
emu.addBinding(Binding('ns-user-internal', filter=Filter(asn=150), action=Action.FIRST))

###########################################################
# Create two local DNS servers (virtual nodes).
ldns = DomainNameCachingService()
ldns.install('global-dns')

# Customize the display name (for visualization purpose)
emu.getVirtualNode('global-dns').setDisplayName('Global DNS')

as151 = base.getAutonomousSystem(151)
as151.createHost('local-dns').joinNetwork('net0', address = '10.151.0.53')

emu.addBinding(Binding('global-dns', filter = Filter(asn=151, nodeName="local-dns")))

# Add 10.153.0.53 as the local DNS server for all the other nodes
base.setNameServers(['10.151.0.53'])

# Add the ldns layer
emu.addLayer(ldns)

###########################################################

emu.render()
emu.compile(Docker(), './output', override=True)

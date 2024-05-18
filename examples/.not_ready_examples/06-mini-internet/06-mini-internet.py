from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from seedemu.raps import OpenVpnRemoteAccessProvider
from typing import List, Tuple, Dict

###############################################################################

emu = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
web = WebService()
dns = DomainNameService()
ldns = DomainNameCachingService()
dnssec = Dnssec()
cymru = CymruIpOriginService()
rdns = ReverseDomainNameService()
lg = BgpLookingGlassService()
ovpn = OpenVpnRemoteAccessProvider()

###############################################################################
# Helper function: create real-world autonomous system

def make_real_as(asn: int, exchange: int, exchange_ip: str):
    real_as = base.createAutonomousSystem(asn)
    real_router = real_as.createRealWorldRouter('rw')
    real_router.joinNetwork('ix{}'.format(exchange), exchange_ip)

###############################################################################
# Helper function: create service autonomous system

def make_service_as(emu: Emulator, asn: int, services: List[Service], exchange: int):
    service_as = base.createAutonomousSystem(asn)
    service_as.createNetwork('net0')
    router = service_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    for service in services:
        # Create a physical node
        name = 's_{}'.format(service.getName().lower())
        service_as.createHost(name).joinNetwork('net0')
       
        # Install the service on a virtual node 
        vnodename = 'as{}_{}'.format(asn, name)
        service.install(vnodename)

        # Bind the virtual node to the physical node
        emu.addBinding(Binding(vnodename, filter = Filter(asn = asn, nodeName = name)))

###############################################################################
# Helper function: create autonomous system for a DNS server

def make_dns_as(emu: Emulator, asn: int, zones: List[str], exchange: int):
    dns_as = base.createAutonomousSystem(asn)
    dns_as.createNetwork('net0')

    router = dns_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    # For each zone, create a server in asn to host this zone
    for zone in zones:
        # Create a physical node
        name = 's_{}dns'.format(zone.replace('.','_'))
        dns_as.createHost(name).joinNetwork('net0')

        # Install DNS service on a virtual node (on the DNS layer)
        vnodename = 'as{}_{}'.format(asn, name)
        dns.install(vnodename).addZone(zone)

        # Bind the virtual node to the physical node
        emu.addBinding(Binding(vnodename, filter = Filter(asn = asn, nodeName = name)))

###############################################################################
# Helper function: create a real-world accessible autonomous system

def make_user_as(emu: Emulator, asn: int, exchange: str):
    # Create AS and internal network
    user_as = base.createAutonomousSystem(asn)
    net = user_as.createNetwork('net0')

    # Create a BGP router and attach it to 2 networks
    router = user_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    # Create a looking-glass host node
    user_as.createHost('looking_glass').joinNetwork('net0')

    vnodename = 'lg{}'.format(asn)

    # Create a looking-glass virtual node, attach it to a BGP router.
    # The looking-glass service has two parts: proxy and front end. 
    # Proxy runs on routers and talk with the BIRD server to get routing information. 
    # The attach() API will install the proxy software on the router.
    # The front end is the actual "looking glass" service.
    # A looking-glass server can be attached to multiple routers.
    lg.install(vnodename).attach('router0')
    
    # Bind looking-glass virtual node to a physical node
    emu.addBinding(Binding(vnodename, filter = Filter(asn = asn, nodeName = 'looking_glass')))

    # Enable the real-world access, i.e. a new VPN server node will be created.
    net.enableRemoteAccess(ovpn)


###############################################################################
# Helper function: create a transit autonomous system

def make_transit_as(asn: int, exchanges: List[int], intra_ix_links: List[Tuple[int, int]]):
    transit_as = base.createAutonomousSystem(asn)

    routers: Dict[int, Router] = {}

    # Create a BGP router for each internet exchange (for peering purpose)
    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetwork('ix{}'.format(ix))

    # For each pair, create an internal network
    for (a, b) in intra_ix_links:
        name = 'net_{}_{}'.format(a, b)

        net = transit_as.createNetwork(name)

        routers[a].joinNetwork(name)
        routers[b].joinNetwork(name)

###############################################################################

base.createInternetExchange(100)
base.createInternetExchange(101)
base.createInternetExchange(102)
base.createInternetExchange(103)
base.createInternetExchange(104)
base.createInternetExchange(105)

###############################################################################

## Tier 1

make_transit_as(2, [100, 101, 102], [
    (100, 101),
    (101, 102),
    (102, 100)
])

make_transit_as(3, [100, 103, 105], [
    (100, 103),
    (103, 105),
    (105, 100)
])

make_transit_as(4, [100, 104], [
    (100, 104)
])

## Tier 2

make_transit_as(11, [102, 105], [
    (102, 105)
])

make_transit_as(12, [101, 104], [
    (101, 104)
])

###############################################################################

make_real_as(11872, 105, '10.105.0.250') # Syracuse University

###############################################################################

make_service_as(emu, 150, [web, ldns], 101)
make_service_as(emu, 151, [web], 100)
make_service_as(emu, 152, [web], 102)
make_service_as(emu, 153, [ldns], 102)

###############################################################################

# Host the root zone in AS-160, which has a PoP in IX-103
make_dns_as(emu, 160, ['.'], 103)

# Host these 3 zones in AS-161, which has a PoP in IX-103
make_dns_as(emu, 161, ['net.', 'com.', 'arpa.'], 103)

###############################################################################

# Create three zones, and add a record to each  
dns.getZone('as150.net.').addRecord('@ A 10.150.0.71')
dns.getZone('as151.net.').addRecord('@ A 10.151.0.71')
dns.getZone('as152.net.').addRecord('@ A 10.152.0.71')

# Host these 3 zones in AS-162, which has a PoP in IX-103
make_dns_as(emu, 162, ['as150.net.', 'as151.net.', 'as152.net.'], 103)

###############################################################################

# Host the in-addr.arpa. zone in AS-154, which has a PoP in IX-104
make_dns_as(emu, 154, ['in-addr.arpa.'], 104)

# Host the cymru.com. zone in AS-155, which has a PoP in IX-105
make_dns_as(emu, 155, ['cymru.com.'], 105)

###############################################################################

make_user_as(emu, 170, 102)
make_user_as(emu, 171, 105)

###############################################################################

dnssec.enableOn('.')
dnssec.enableOn('net.')
dnssec.enableOn('as150.net.')
dnssec.enableOn('as151.net.')
dnssec.enableOn('as152.net.')

###############################################################################
# 
google = base.createAutonomousSystem(15169)
google.createNetwork('google_dns_net', '8.8.8.0/24')

google_router = google.createRouter('router0')
google_router.joinNetwork('google_dns_net')
google_router.joinNetwork('ix100', '10.100.0.250')

# Create a local DNS server on 8.8.8.8.
# This local DNS server will use the DNS infrastructure inside the emulator
google.createHost('google_dns').joinNetwork('google_dns_net', '8.8.8.8')
ldns.install('google_dns')
emu.addBinding(Binding('google_dns', filter = Filter(asn = 15169)))


###############################################################################

ebgp.addRsPeer(100, 2)
ebgp.addRsPeer(101, 2)
ebgp.addRsPeer(102, 2)

ebgp.addRsPeer(100, 3)
ebgp.addRsPeer(103, 3)
ebgp.addRsPeer(105, 3)

ebgp.addRsPeer(100, 4)
ebgp.addRsPeer(104, 4)

###############################################################################

ebgp.addPrivatePeering(102, 2, 11, PeerRelationship.Provider)
ebgp.addPrivatePeering(105, 3, 11, PeerRelationship.Provider)

ebgp.addPrivatePeering(101, 2, 12, PeerRelationship.Provider)
ebgp.addPrivatePeering(104, 4, 12, PeerRelationship.Provider)

ebgp.addPrivatePeering(101, 2, 150, PeerRelationship.Provider)
ebgp.addPrivatePeering(101, 12, 150, PeerRelationship.Provider)

ebgp.addPrivatePeering(100, 3, 151, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 4, 151, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 2, 152, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 2, 153, PeerRelationship.Provider)

ebgp.addPrivatePeering(104, 4, 154, PeerRelationship.Provider)
ebgp.addPrivatePeering(104, 12, 154, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 3, 155, PeerRelationship.Provider)

ebgp.addPrivatePeering(103, 3, 160, PeerRelationship.Provider)

ebgp.addPrivatePeering(103, 3, 161, PeerRelationship.Provider)
ebgp.addPrivatePeering(103, 3, 162, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 11, 170, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 11, 171, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 3, 11872, PeerRelationship.Provider)
ebgp.addPrivatePeering(105, 11, 11872, PeerRelationship.Provider)

ebgp.addPrivatePeering(100, 2, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 3, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 4, 15169, PeerRelationship.Provider)

###############################################################################
# Set 8.8.8.8 as the local DNS server for all the hosts in the emulator
emu.addHook(ResolvConfHook(['8.8.8.8']))

###############################################################################

emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)
emu.addLayer(dns)
emu.addLayer(ldns)
emu.addLayer(dnssec)
emu.addLayer(cymru)
emu.addLayer(rdns)
emu.addLayer(lg)

emu.render()

###############################################################################

emu.compile(Docker(), './output')
# emu.compile(Graphviz(), './output/_graphs') # FIXME

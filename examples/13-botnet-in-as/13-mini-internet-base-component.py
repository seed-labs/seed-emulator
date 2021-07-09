from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, Reality, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from typing import List, Tuple, Dict

###############################################################################

sim = Emulator()

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
real = Reality()
web = WebService()
dns = DomainNameService()
ldns = DomainNameCachingService()
dnssec = Dnssec()
cymru = CymruIpOriginService()
rdns = ReverseDomainNameService()

###############################################################################

def make_real_as(asn: int, exchange: int, exchange_ip: str):
    real_as = base.createAutonomousSystem(asn)
    real_router = real.createRealWorldRouter(real_as)

    real_router.joinNetwork('ix{}'.format(exchange), exchange_ip)

###############################################################################

def make_service_as(asn: int, services: List[Service], exchange: int):
    service_as = base.createAutonomousSystem(asn)

    router = service_as.createRouter('router0')

    net = service_as.createNetwork('net0')

    

    router.joinNetwork('net0')

    router.joinNetwork('ix{}'.format(exchange))

    for service in services:
        name = 's_{}'.format(service.getName().lower())

        server = service_as.createHost(name)
        #server1 = service_as.createHost(name)

        server.joinNetwork('net0')

        service.install(name)
        sim.addBinding(Binding(name, filter = Filter(asn = asn, nodeName=name)))

###############################################################################

def make_dns_as(asn: int, zones: List[str], exchange: int):
    dns_as = base.createAutonomousSystem(asn)

    router = dns_as.createRouter('router0')

    net = dns_as.createNetwork('net0')

    

    router.joinNetwork('net0')

    router.joinNetwork('ix{}'.format(exchange))

    for zone in zones:
        name = 's_{}dns'.format(zone.replace('.','_'))

        server = dns_as.createHost(name)

        server.joinNetwork('net0')

        dns.install(name).addZone(zone)
        sim.addBinding(Binding(name, filter = Filter(asn = asn, nodeName=name)))

###############################################################################

def make_user_as(asn: int, exchange: str):
    user_as = base.createAutonomousSystem(asn)

    router = user_as.createRouter('router0')

    net = user_as.createNetwork('net0')

    

    real.enableRealWorldAccess(user_as, 'net0')

    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

###############################################################################

def make_transit_as(asn: int, exchanges: List[int], intra_ix_links: List[Tuple[int, int]]):
    transit_as = base.createAutonomousSystem(asn)

    routers: Dict[int, Router] = {}

    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetwork('ix{}'.format(ix))

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

make_service_as(150, [web, ldns], 101)
make_service_as(151, [web], 100)
make_service_as(152, [web], 102)
make_service_as(153, [ldns], 102)
make_service_as(154, [ldns], 104)
make_service_as(155, [web], 105)

###############################################################################

make_dns_as(160, ['.'], 103)
make_dns_as(161, ['net.', 'com.', 'arpa.'], 103)

###############################################################################

dns.getZone('as150.net.').addRecord('@ A 10.150.0.71')
dns.getZone('as151.net.').addRecord('@ A 10.151.0.71')
dns.getZone('as152.net.').addRecord('@ A 10.152.0.71')

make_dns_as(162, ['as150.net.', 'as151.net.', 'as152.net.'], 103)

###############################################################################

make_user_as(170, 102)
make_user_as(171, 105)

###############################################################################

dnssec.enableOn('.')
dnssec.enableOn('net.')
dnssec.enableOn('as150.net.')
dnssec.enableOn('as151.net.')
dnssec.enableOn('as152.net.')

###############################################################################

google = base.createAutonomousSystem(15169)

google_dns_net = google.createNetwork('google_dns_net', '8.8.8.0/24')

google_dns = google.createHost('google_dns')

google_dns.joinNetwork('google_dns_net', '8.8.8.8')

ldns.install('google_dns')
sim.addBinding(Binding("google_dns", filter = Filter(asn = 15169, nodeName="google_dns")))



google_router = google.createRouter('router0')

google_router.joinNetwork('google_dns_net')
google_router.joinNetwork('ix100', '10.100.0.250')

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

ebgp.addPrivatePeering(105, 3, 11872, PeerRelationship.Unfiltered)
ebgp.addPrivatePeering(105, 11, 11872, PeerRelationship.Unfiltered)

ebgp.addPrivatePeering(100, 2, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 3, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 4, 15169, PeerRelationship.Provider)

###############################################################################

sim.addHook(ResolvConfHook(['8.8.8.8']))

###############################################################################

sim.addLayer(base)
sim.addLayer(routing)
sim.addLayer(ebgp)
sim.addLayer(ibgp)
sim.addLayer(ospf)
sim.addLayer(real)
sim.addLayer(web)
sim.addLayer(dns)
sim.addLayer(ldns)
sim.addLayer(dnssec)
#sim.addLayer(cymru)
#sim.addLayer(rdns)

sim.dump('mini-internet.bin')
#sim.render()

###############################################################################

#sim.compile(Docker(), './mini-internet')
# sim.compile(Graphviz(), './mini-internet/_graphs')

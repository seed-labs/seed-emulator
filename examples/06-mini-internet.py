from seedsim.layers import Base, Routing, Ebgp, Ibgp, Ospf, Reality, PeerRelationship
from seedsim.layers import WebService, DomainNameService, DomainNameCachingService
from seedsim.layers import CymruIpOriginService, ReverseDomainNameService

from seedsim.compiler import Docker, Graphviz
from seedsim.compiler import Compiler

from seedsim.renderer import Renderer

from seedsim.layers import Router, Service

from typing import List, Tuple, Dict

base = Base()
routing = Routing()
ebgp = Ebgp()
ibgp = Ibgp()
ospf = Ospf()
real = Reality()
web = WebService()
dns = DomainNameService()
ldns = DomainNameCachingService()
cymru = CymruIpOriginService()
rdns = ReverseDomainNameService()

rendrer = Renderer()
docker_compiler = Docker()
graphviz = Graphviz()

###############################################################################

def make_real_as(asn: int, exchange: int, exchange_ip: str):
    real_as = base.createAutonomousSystem(asn)
    real_router = real.createRealWorldRouter(real_as)

    real_router.joinNetworkByName('ix{}'.format(exchange), exchange_ip)

###############################################################################

def make_service_as(asn: int, services: List[Service], exchange: int):
    service_as = base.createAutonomousSystem(asn)

    router = service_as.createRouter('router0')

    net = service_as.createNetwork('net0')

    routing.addDirect(net)

    router.joinNetwork(net)

    router.joinNetworkByName('ix{}'.format(exchange))

    for service in services:
        server = service_as.createHost('s_{}'.format(service.getName().lower()))

        server.joinNetwork(net)

        service.installOn(server)

###############################################################################

def make_dns_as(asn: int, zones: List[str], exchange: int):
    dns_as = base.createAutonomousSystem(asn)

    router = dns_as.createRouter('router0')

    net = dns_as.createNetwork('net0')

    routing.addDirect(net)

    router.joinNetwork(net)

    router.joinNetworkByName('ix{}'.format(exchange))

    for zone in zones:
        server = dns_as.createHost('s_{}dns'.format(zone.replace('.','_')))

        server.joinNetwork(net)

        dns.hostZoneOn(zone, server)

###############################################################################

def make_user_as(asn: int, exchange: str):
    user_as = base.createAutonomousSystem(asn)

    router = user_as.createRouter('router0')

    net = user_as.createNetwork('net0')

    routing.addDirect(net)

    real.enableRealWorldAccess(net)

    router.joinNetworkByName('ix{}'.format(exchange))

###############################################################################

def make_transit_as(asn: int, exchanges: List[int], intra_ix_links: List[Tuple[int, int]]):
    transit_as = base.createAutonomousSystem(asn)

    routers: Dict[int, Router] = {}

    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetworkByName('ix{}'.format(ix))

    for (a, b) in intra_ix_links:
        net = transit_as.createNetwork('net_{}_{}'.format(a, b))

        routing.addDirect(net)

        routers[a].joinNetwork(net)
        routers[b].joinNetwork(net)

###############################################################################

def get_asn():
    i = 150
    while True:
        yield i
        i += 1

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

###############################################################################

make_real_as(15169, 100, '10.100.0.250') # Google
make_real_as(11872, 105, '10.105.0.250') # Syracuse University

###############################################################################

make_service_as(150, [web, ldns], 101)
make_service_as(151, [web], 100)
make_service_as(152, [web], 102)
make_service_as(153, [ldns], 102)
make_service_as(154, [rdns], 104)
make_service_as(155, [cymru], 105)

make_dns_as(160, ['.'], 103)
make_dns_as(161, ['com.', 'arpa.'], 103)

make_user_as(170, 102)
make_user_as(171, 105)

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

ebgp.addPrivatePeering(101, 2, 150, PeerRelationship.Provider)

ebgp.addPrivatePeering(100, 3, 151, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 4, 151, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 2, 152, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 2, 153, PeerRelationship.Provider)

ebgp.addPrivatePeering(104, 4, 154, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 3, 155, PeerRelationship.Provider)

ebgp.addPrivatePeering(103, 3, 160, PeerRelationship.Provider)

ebgp.addPrivatePeering(103, 3, 161, PeerRelationship.Provider)

ebgp.addPrivatePeering(102, 11, 170, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 11, 171, PeerRelationship.Provider)

ebgp.addPrivatePeering(105, 3, 11872, PeerRelationship.Provider)
ebgp.addPrivatePeering(105, 11, 11872, PeerRelationship.Provider)

ebgp.addPrivatePeering(100, 2, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 3, 15169, PeerRelationship.Provider)
ebgp.addPrivatePeering(100, 4, 15169, PeerRelationship.Provider)

###############################################################################

rendrer.addLayer(base)
rendrer.addLayer(routing)
rendrer.addLayer(ebgp)
rendrer.addLayer(ibgp)
rendrer.addLayer(ospf)
rendrer.addLayer(real)
rendrer.addLayer(web)
rendrer.addLayer(dns)
rendrer.addLayer(ldns)
rendrer.addLayer(cymru)
rendrer.addLayer(rdns)

rendrer.render()

###############################################################################

docker_compiler.compile('./mini-internet')
graphviz.compile('./mini-internet/_graphs')
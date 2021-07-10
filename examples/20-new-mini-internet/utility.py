from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from typing import List, Tuple, Dict


###############################################################################
# Helper function: create a stub autonomous system (with one internal network)

def make_stub_AS(emu: Emulator, base: Base, routing: Routing, asn: int, 
                 exchange: int, services: List[Service]):
    # Create AS and internal network
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork('net0')

    # Create a BGP router 
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    # For each service, create a host for it. 
    # service is the instance of a service class, such as WebService,
    # If service is None, only create a host without installing any service.
    counter = 0;
    for service in services:
        if service is None:
           name = 'host_{}'.format(counter)
           stub_as.createHost(name).joinNetwork('net0')
        else: 
           # Create a physical node
           name = '{}_{}'.format(service.getName().lower(), counter)
           stub_as.createHost(name).joinNetwork('net0')
          
           # Install the service on a virtual node 
           vnodename = 'as{}_{}_{}'.format(asn, name, counter)
           service.install(vnodename)
   
           # Bind the virtual node to the physical node
           emu.addBinding(Binding(vnodename, filter = Filter(asn = asn, nodeName = name)))

        counter += 1
   

###############################################################################
# Helper function: create a transit autonomous system.

def make_transit_AS(base: Base, routing: Routing, asn: int, exchanges: List[int], 
                    intra_ix_links: List[Tuple[int, int]]):
    transit_as = base.createAutonomousSystem(asn)

    routers: Dict[int, Router] = {}

    # Create a BGP router for each internet exchange (for peering purpose)
    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetwork('ix{}'.format(ix))

    # For each pair, create an internal network to connect the BGP routers
    # from two internet exchanges. There is no need to create a full-mesh
    # network among the BGP routers. As long as they can reach each other
    # over a single or multiple hops, it is OK.
    for (a, b) in intra_ix_links:
        name = 'net_{}_{}'.format(a, b)

        transit_as.createNetwork(name)
        routers[a].joinNetwork(name)
        routers[b].joinNetwork(name)

###############################################################################
# Helper function: create a multi-homed stub autonomous system

#def make_multihome_stub_AS(emu: Emulator, base: Base, routing: Routing, asn: int, 
#                 exchange: List[int], services: List[Service]):




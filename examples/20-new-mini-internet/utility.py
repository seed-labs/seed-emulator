from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship, Dnssec
from seedemu.services import WebService, DomainNameService, DomainNameCachingService
from seedemu.services import CymruIpOriginService, ReverseDomainNameService, BgpLookingGlassService
from seedemu.compiler import Docker, Graphviz
from seedemu.hooks import ResolvConfHook
from seedemu.core import Emulator, Service, Binding, Filter
from seedemu.layers import Router
from typing import List, Tuple, Dict


###############################################################################
# Helper function: create a transit autonomous system.

def make_transit_AS(base: Base, asn: int, exchanges: List[int], 
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
# Helper function: create a single-homed stub autonomous system 
# We will only create one internal network

def make_stub_AS(emu: Emulator, base: Base, asn: int, 
                 exchange: int, services: List[Service]):
    # Create AS and internal network
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork('net0')

    # Create a BGP router 
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    # Create a host node for each specified service
    create_hosts_on_network(emu, stub_as, 'net0', services, 0)




###############################################################################
# Helper function: create a multi-homed stub autonomous system
# For the sake of simplicity, we will only create one internal network, 
# and connect all the BGP routers to this single internal network.
# We can create another utility function for a more sophisticated setup.

def make_multihomed_stub_AS_in_multi_ix(emu: Emulator, base: Base, asn: int, 
                           exchanges: List[int], services: List[Service]):
    # Create AS and an internal network
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork('net0')

    # Create a BGP router for each internet exchange.
    # Internally, connect them to the same internal network.
    for ix in exchanges:
        router = stub_as.createRouter('r{}'.format(ix))
        router.joinNetwork('ix{}'.format(ix))
        router.joinNetwork('net0')

    # Create a host node for each specified service
    create_hosts_on_network(emu, stub_as, 'net0', services, 0)


###############################################################################
# Helper function: create host/service nodes on a network in an autonomous system
# counter_start: counter will be used to give each node a unique name.
# This function can be called multiple times, but counter_start needs to be 
# set properly to avoid duplicated names. 

def create_hosts_on_network(emu: Emulator, the_as, network: str, 
                            services: List[Service], counter_start: int):
    # For each service, create a host for it. 
    # service is the instance of a service class, such as WebService,
    # If service is None, only create a host without installing any service.
    counter = counter_start;
    for service in services:
        if service is None:
           name = 'host_{}'.format(counter)
           the_as.createHost(name).joinNetwork(network)
        else:
           # Create a physical node
           name = '{}_{}'.format(service.getName().lower(), counter)
           the_as.createHost(name).joinNetwork(network)

           # Install the service on a virtual node 
           asn = the_as.getAsn()
           vnodename = 'as{}_{}_{}'.format(asn, name, counter)
           service.install(vnodename)

           # Bind the virtual node to the physical node
           emu.addBinding(Binding(vnodename, filter = Filter(asn = asn, nodeName = name)))

        counter += 1


###############################################################################
# Helper function: create private peering between an ISP and a list of customers

def private_peering_with_isp(ebgp: Ebgp, exchange: int, 
                             isp: int, customers: [int]):
    for customer in customers:
        ebgp.addPrivatePeering(exchange, isp, customer, 
                               abRelationship = PeerRelationship.Provider)


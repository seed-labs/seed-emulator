from seedemu.layers import Base
from seedemu.core import Binding, Filter, Emulator, Service, Router, AutonomousSystem
from typing import List, Tuple, Dict

def makeTransitAs(base: Base, asn: int, exchanges: List[int],
    intra_ix_links: List[Tuple[int, int]]) -> AutonomousSystem:
    """!
    @brief create a transit AS.

    @param base reference to the base layer.
    @param asn ASN of the newly created AS.
    @param exchanges list of IXP IDs to join.
    @param intra_ix_links list of tuple of IXP IDs, to create intra-IX links at.

    @returns transit AS object.
    """

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

    return transit_as

def createHostsOnNetwork(emu: Emulator, the_as: AutonomousSystem, network: str, 
        services: List[Service], counter_start: int = 0):
    """!
    @brief For each service, create a host for it.

    @param emu reference to the Emulator object.
    @param the_as reference to the AutonomousSystem object.
    @param network name of network to join on hosts.
    @param services list of instances of Service to install on hosts. One will
    be installed on each.
    @param counter_start (optional) counter to start when assigning names to
    hosts. Defualt to 0.
    """

    # For each service, create a host for it. 
    # service is the instance of a service class, such as WebService,
    # If service is None, only create a host without installing any service.
    counter = counter_start

    if len(services) == 0:
        name = 'host_{}'.format(counter)
        the_as.createHost(name).joinNetwork(network)

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

def makeStubAs(emu: Emulator, base: Base, asn: int, exchange: int,
    services: List[Service]):
    """!
    @brief create a new stub AS.

    @param emu reference to the Emulator object.
    @param base reference to the base layer.
    @param asn ASN for the newly created AS.
    @param exchange IXP ID for new newly created AS to join.
    @param list of instances of Service to install on hosts. One host will be
    created for each.
    """

    # Create AS and internal network
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork('net0')

    # Create a BGP router 
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork('net0')
    router.joinNetwork('ix{}'.format(exchange))

    # Create a host node for each specified service
    createHostsOnNetwork(emu, stub_as, 'net0', services)
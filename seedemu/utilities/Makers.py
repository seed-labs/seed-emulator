from seedemu.layers import Base, Ebgp, Routing, Ibgp, Ospf
from seedemu.layers.Ebgp import PeerRelationship
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
    hosts. Default to 0.
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

def makeStubAsWithHosts(emu: Emulator, base: Base, asn: int, exchange: int, hosts_total: int):

    # Create AS and internal network
    network = "net0"
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork(network)

    # Create a BGP router
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork(network)
    router.joinNetwork('ix{}'.format(exchange))

    for counter in range(hosts_total):
       name = 'host_{}'.format(counter)
       host = stub_as.createHost(name)
       host.joinNetwork(network)

def makeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as: int) -> Emulator:
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

    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')


    ###############################################################################
    # Create Transit Autonomous Systems 

    ## Tier 1 ASes
    makeTransitAs(base, 2, [100, 101, 102], 
        [(100, 101), (101, 102)] 
    )

    makeTransitAs(base, 3, [100, 103, 104], 
        [(100, 103), (103, 104)]
    )

    makeTransitAs(base, 4, [100, 102, 104], 
        [(100, 104), (102, 104)]
    )

    ## Tier 2 ASes
    makeTransitAs(base, 12, [101, 104], [(101, 104)])


    ###############################################################################
    # Create single-homed stub ASes. "None" means create a host only 

    makeStubAsWithHosts(emu, base, 150, 100, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 151, 100, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 152, 101, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 153, 101, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 154, 102, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 160, 103, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 161, 103, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 162, 103, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 163, 104, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 164, 104, hosts_per_stub_as)
    

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 

    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])

    # To buy transit services from another autonomous system, 
    # we will use private peering  

    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4],  [154], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    return emu

def makeEmulatorBaseWith5StubASAndHosts(hosts_per_stub_as: int) -> Emulator:
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

    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')


    ###############################################################################
    # Create Transit Autonomous Systems 

    ## Tier 1 ASes
    makeTransitAs(base, 2, [100, 101, 102], 
        [(100, 101), (101, 102)] 
    )

    makeTransitAs(base, 3, [100, 103, 104], 
        [(100, 103), (103, 104)]
    )

    makeTransitAs(base, 4, [100, 102, 104], 
        [(100, 104), (102, 104)]
    )

    ## Tier 2 ASes
    makeTransitAs(base, 12, [101, 104], [(101, 104)])


    ###############################################################################
    # Create single-homed stub ASes. "None" means create a host only 

    makeStubAsWithHosts(emu, base, 150, 100, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 151, 100, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 152, 101, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 153, 101, hosts_per_stub_as)
    makeStubAsWithHosts(emu, base, 154, 102, hosts_per_stub_as)
    

    ###############################################################################
    # Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
    # which means each AS will only export its customers and their own prefixes. 
    # We will use this peering relationship to peer all the ASes in an IX.
    # None of them will provide transit service for others. 

    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])

    # To buy transit services from another autonomous system, 
    # we will use private peering  

    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

    ebgp.addPrivatePeerings(102, [2, 4],  [154], PeerRelationship.Provider)


    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)

    return emu
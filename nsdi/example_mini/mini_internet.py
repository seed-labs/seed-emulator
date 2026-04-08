#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers
import os, sys

def makeTransitAs(base: Base, asn: int, exchanges: List[int], 
        intra_ix_links: List[Tuple[int, int]]):

    transit_as = base.createAutonomousSystem(asn)

    routers: Dict[int, Router] = {}

    # Create a BGP router for each internet exchange.
    for ix in exchanges:
        routers[ix] = transit_as.createRouter('r{}'.format(ix))
        routers[ix].joinNetwork('ix{}'.format(ix))

    # For each pair, create an internal network to connect 
    # the BGP routers from two internet exchanges. 
    for (a, b) in intra_ix_links:
        name = 'net_{}_{}'.format(a, b)
        transit_as.createNetwork(name)
        routers[a].joinNetwork(name)
        routers[b].joinNetwork(name)


def makeStubAsWithHosts(emu: Emulator, base: Base, asn: int, exchange: int, hosts_total: int):

    # Create AS and internal network
    network = "net0"
    stub_as = base.createAutonomousSystem(asn)
    stub_as.createNetwork(network)

    # Create a BGP router,
    # Attach the router to both the internal and external networks
    router = stub_as.createRouter('router0')
    router.joinNetwork(network)
    router.joinNetwork('ix{}'.format(exchange))

    for counter in range(hosts_total):
       name = 'host_{}'.format(counter)
       host = stub_as.createHost(name)
       host.joinNetwork(network)


def run(dumpfile=None, hosts_per_as=2): 
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    emu   = Emulator()
    ebgp  = Ebgp()
    base  = Base()
    
    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    
    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')
    ix105.getPeeringLan().setDisplayName('Huston-105')
    
    
    ###############################################################################
    # Create Transit Autonomous Systems 
    
    ## Tier 1 ASes
    makeTransitAs(base, 2, [100, 101, 102, 105], 
           [(100, 101), (101, 102), (100, 105)] 
    )
    
    makeTransitAs(base, 3, [100, 103, 104, 105], 
           [(100, 103), (100, 105), (103, 105), (103, 104)]
    )
    
    makeTransitAs(base, 4, [100, 102, 104], 
           [(100, 104), (102, 104)]
    )
    
    ## Tier 2 ASes
    makeTransitAs(base, 11, [102, 105], [(102, 105)])
    makeTransitAs(base, 12, [101, 104], [(101, 104)])
    
    # Enable MPLS 
    mpls = Mpls()     # MPLS layer
    mpls.enableOn(3)  # Enable MPLS in AS-3 


    ###############################################################################
    # Create single-homed stub ASes. 
    makeStubAsWithHosts(emu, base, 150, 100, hosts_per_as)
    makeStubAsWithHosts(emu, base, 151, 100, hosts_per_as)
    makeStubAsWithHosts(emu, base, 152, 101, hosts_per_as)
    makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    makeStubAsWithHosts(emu, base, 154, 102, hosts_per_as)
    makeStubAsWithHosts(emu, base, 160, 103, hosts_per_as)
    makeStubAsWithHosts(emu, base, 161, 103, hosts_per_as)
    makeStubAsWithHosts(emu, base, 162, 103, hosts_per_as)
    makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)
    makeStubAsWithHosts(emu, base, 170, 105, hosts_per_as)
    makeStubAsWithHosts(emu, base, 171, 105, hosts_per_as)

    # Peering via RS (route server): public peering 
    ebgp.addRsPeers(100, [2, 3, 4])
    ebgp.addRsPeers(102, [2, 4])
    ebgp.addRsPeers(104, [3, 4])
    ebgp.addRsPeers(105, [2, 3])
    
    # Stub ASes buy services from transit ASes: private peering 
    ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [3],  [150], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [3],  [160, 161, 162], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)
    
    ######################################
    # Node customization
    ######################################

    # An example to show how to customize IP
    as154 = base.getAutonomousSystem(154)
    new_host = as154.createHost('host_new')
    new_host.joinNetwork('net0', address = '10.154.0.129')
    new_host ....   


    # Node customization: software installation, configuration 
    new_node.addSoftware("python3")
    new_node.addBuildCommand("curl http://example.com")
    new_node.importFile(hostpath=os.getcwd() + "/myprog.py",
                containerpath="/myprog.py")
    new_node.insertStartCommand(0, "ping 1.2.3.4")


    # Node customization: set sysctl parameters
    from seedemu.core import OptionRegistry, OptionMode
    o = OptionRegistry().sysctl_netipv4_conf_rp_filter({'all': False, 
          'default': False, 'net0': False}, mode = OptionMode.RUN_TIME)
    new_host.setOption(o)

    o = OptionRegistry().sysctl_netipv4_udp_rmem_min(5000, mode = OptionMode.RUN_TIME)
    new_host.setOption(o)
    

    ######################################
    # Network customization
    ######################################

    # Enable remote access on AS-151 network 
    as151.createNetwork('net0').enableRemoteAccess(ovpn)

    # Create a real-world AS. 
    # Packets coming into this AS will be routed out to the real world. 
    as60000 = base.createAutonomousSystem(60000)
    router = as60000.createRealWorldRouter(name='rw', 
                     prefixes=['0.0.0.0/1', '128.0.0.0/1'])
    router.joinNetwork('ix101', '10.101.0.118')
    ebgp.addPrivatePeerings(101, [2], [60000], PeerRelationship.Provider)


    ######################################
    # IP Anycast 
    ######################################

    # Follow the instructions from example B24_ip_anycast 

    
    ###############################################################################
    # Add layers to the emulator

    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp) 
    emu.addLayer(Ibgp())
    emu.addLayer(Ospf())

    if dumpfile is not None: 
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
    else: 
        emu.render()

        # Attach the Internet Map container to the emulator
        docker = Docker(platform=platform)
        emu.compile(docker, './output', override=True)

if __name__ == "__main__":
    run()

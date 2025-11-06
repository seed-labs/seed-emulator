#!/usr/bin/env python3
# encoding: utf-8

"""在基础 10 Stub-AS 网络上部署 MoneroService 的示例脚本。

该示例仿照 `examples/blockchain/D01_ethereum_pos/ethereum_pos.py` 的结构，
利用 `Makers.makeEmulatorBaseWith10StubASAndHosts()` 构建底层拓扑，并按照
预期角色创建以下 Monero 节点：

* AS150-154: host_0 作为种子节点，host_1 作为 full client（仅 AS150 的 client 节点挖矿）。
* AS160-161: 每个 AS 一个 full client 节点。
* AS162-163: 每个 AS 一个 light wallet 节点。
* AS164: 一个 pruned 节点。

"""

from __future__ import annotations

import os
import sys

from seedemu import *


def _bind(emu, vnode: str, asn: int, host_index: int):
    emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName=f"host_{host_index}")))


###############################################################################
# Set the platform information
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


def mymakeStubAsWithHosts(emu: Emulator, base: Base, asn: int, exchange: int, hosts_total: int):

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
       host.addSoftware('monero')
       host.joinNetwork(network)

def mymakeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as: int) -> Emulator:
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

    mymakeStubAsWithHosts(emu, base, 150, 100, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 151, 100, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 152, 101, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 153, 101, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 154, 102, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 160, 103, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 161, 103, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 162, 103, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 163, 104, hosts_per_stub_as)
    mymakeStubAsWithHosts(emu, base, 164, 104, hosts_per_stub_as)
    

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

hosts_per_stub_as = 5
emu = mymakeEmulatorBaseWith10StubASAndHosts(hosts_per_stub_as=hosts_per_stub_as)



emu.render()

docker = Docker(internetMapEnabled=True, platform=platform)
emu.compile(docker, './output', override = True)



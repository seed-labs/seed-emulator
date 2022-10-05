#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os

from seedemu.services.EthereumService import EthereumServerTypes

def makeStubAs(emu: Emulator, base: Base, asn: int, exchange: int, hosts_total: int):

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

#n = len(sys.argv)
#if n < 2:
#    print("Please provide the number of hosts per networks")
#    exit(0)
#hosts_total = int(sys.argv[1])

hosts_total = int(1)

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
Makers.makeTransitAs(base, 2, [100, 101, 102], 
       [(100, 101), (101, 102)] 
)

Makers.makeTransitAs(base, 3, [100, 103, 104], 
       [(100, 103), (103, 104)]
)

Makers.makeTransitAs(base, 4, [100, 102, 104], 
       [(100, 104), (102, 104)]
)

## Tier 2 ASes
Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])


###############################################################################
# Create single-homed stub ASes. "None" means create a host only 

makeStubAs(emu, base, 150, 100, hosts_total)
makeStubAs(emu, base, 151, 100, hosts_total)

makeStubAs(emu, base, 152, 101, hosts_total)
makeStubAs(emu, base, 153, 101, hosts_total)

makeStubAs(emu, base, 154, 102, hosts_total)

makeStubAs(emu, base, 160, 103, hosts_total)
makeStubAs(emu, base, 161, 103, hosts_total)
makeStubAs(emu, base, 162, 103, hosts_total)

makeStubAs(emu, base, 163, 104, hosts_total)
makeStubAs(emu, base, 164, 104, hosts_total)


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

eth = EthereumService()
docker = Docker()
asns = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]

TERMINAL_TOTAL_DIFFICULTY=50
LIGHTHOUSE_BIN_PATH="/home/won/.cargo/bin/lighthouse"
i = 1
for asn in asns:
    for id in range(hosts_total):
        
        e:EthereumServer = eth.install("eth{}".format(i)).setConsensusMechanism(ConsensusMechanism.POA)    
        e.enablePoS(LIGHTHOUSE_BIN_PATH, TERMINAL_TOTAL_DIFFICULTY)
        e.unlockAccounts()
        e.startMiner()
        e.setBeaconSetupNodeIp('10.150.0.99:8090')
                
        if asn == asns[0]:
            if id == 0:
                e.setBootNode(True)
                e.enableGethHttp()

        if asn in [151,153,154,160]:
            e.enablePOSValidator(True)    
                
        emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-POA-{}'.format(i))
        emu.addBinding(Binding('eth{}'.format(i), filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        
        i = i+1

# ###################################################
# # Beacon Setup Node 
# asn150 = base.getAutonomousSystem(150)
# asn150.createHost('beacon_setup_host').joinNetwork('net0', address="10.150.0.99")
# beacon_setup_node:EthereumServer = eth.install('eth99999', EthereumServerTypes.BEACON_SETUP_NODE).setConsensusMechanism(ConsensusMechanism.POA)
# beacon_setup_node.enableGethHttp()
# beacon_setup_node.enablePoS(terminal_total_difficulty)
# beacon_setup_node.unlockAccounts()
# emu.getVirtualNode('eth99999').setDisplayName('Ethereum-POA-99999')
# emu.addBinding(Binding('eth99999', filter=Filter(asn=150, nodeName='beacon_setup_host')))

# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(eth)

emu.render()

emu.compile(docker, './output', override = True)
os.system('cp ./z_start.sh ./output/')

BEACON_SETUP_NODE_COMMAND_SH = """\
#!/bin/bash
./beacon-setup-node.py {} '{}' {}
"""
f = open("beacon-setup-node.sh", "w")
f.write(BEACON_SETUP_NODE_COMMAND_SH.format(TERMINAL_TOTAL_DIFFICULTY, ",".join(eth.getValidatorIds()),eth.getBootNodes(ConsensusMechanism.POA)[0].split(":")[0]))
f.close()

os.system("chmod +x beacon-setup-node.sh")
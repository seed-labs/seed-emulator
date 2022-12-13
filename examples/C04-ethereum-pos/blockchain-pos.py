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

hosts_total = int(3)

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

TERMINAL_TOTAL_DIFFICULTY=20

i = 1
for asn in asns:
    for id in range(hosts_total):
        
        e:EthereumServer = eth.install("eth{}".format(i)).setConsensusMechanism(ConsensusMechanism.POA)    
        e.enablePoS(TERMINAL_TOTAL_DIFFICULTY)
        e.appendClassName('Ethereum-POS-{}'.format(i))

        e.setBeaconPeerCounts(10)
        e.unlockAccounts()
        e.enableGethHttp()
        
        if asn == asns[0]:
            if id == 0:
                e.setBootNode(True)
                e.createAccount(balance=32*pow(10,18), password = "admin")
                e.setBaseAccountBalance(balance=32*pow(10,18)*(4*hosts_total+5))
        if asn in [152, 162]:
            if id == 0:
                e.enablePOSValidatorAtRunning()
            if id == 1:
                e.enablePOSValidatorAtRunning(is_mananual=True)

        if asn in [151,153,154,160]:
            e.enablePOSValidatorAtGenesis() 
            e.startMiner()
        
        emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-POS-{}'.format(i))
        emu.addBinding(Binding('eth{}'.format(i), filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        
        i = i+1
        
###################################################
# Beacon Setup Node 
asn150 = base.getAutonomousSystem(150)
asn150.createHost('beacon_setup_host').joinNetwork('net0', address="10.150.0.99")
beacon_setup_node:EthereumServer = eth.install('eth99999').setConsensusMechanism(ConsensusMechanism.POA)
beacon_setup_node.setBeaconSetupNode()
beacon_setup_node.enablePoS(TERMINAL_TOTAL_DIFFICULTY)

emu.getVirtualNode('eth99999'.format(i)).setDisplayName('Ethereum-Beacon-Setup')
emu.addBinding(Binding('eth99999', filter=Filter(asn=150, nodeName='beacon_setup_host')))


# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(eth)

emu.render()

docker.addImage(DockerImage('rafaelawon/seedemu-lighthouse-base', [], local=False), priority=-1)
docker.addImage(DockerImage('rafaelawon/seedemu-lcli-base', [], local=False), priority=-2)

beacon_nodes = base.getNodesByName('host')
for beacon in beacon_nodes:
   docker.setImageOverride(beacon, 'rafaelawon/seedemu-lighthouse-base')

beacon_setup = base.getNodesByName('beacon_setup_host')
docker.setImageOverride(beacon_setup[0], 'rafaelawon/seedemu-lcli-base')

emu.compile(docker, './output', override = True)
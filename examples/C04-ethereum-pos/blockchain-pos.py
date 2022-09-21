#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os

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

hosts_total = int(5)

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

# Customize names (for visualization purpose)
ix100.getPeeringLan().setDisplayName('NYC-100')
ix101.getPeeringLan().setDisplayName('San Jose-101')

###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
Makers.makeTransitAs(base, 2, [100, 101], 
       [(100, 101)] 
)

###############################################################################
# Create single-homed stub ASes. "None" means create a host only 

makeStubAs(emu, base, 150, 100, hosts_total)
makeStubAs(emu, base, 151, 101, hosts_total)

###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
# which means each AS will only export its customers and their own prefixes. 
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others. 

ebgp.addRsPeers(100, [2])
ebgp.addRsPeers(101, [2])

# To buy transit services from another autonomous system, 
# we will use private peering  

ebgp.addPrivatePeerings(100, [2],  [150], PeerRelationship.Provider)

ebgp.addPrivatePeerings(101, [2],  [151], PeerRelationship.Provider)

###############################################################################
# Create the Ethereum layer

eth = EthereumService()
docker = Docker()
asns = [150, 151]
i = 1
for asn in asns:
    for id in range(hosts_total):
        e:EthereumServer = eth.install("eth{}".format(i)).setConsensusMechanism(ConsensusMechanism.POA)
        e.enablePoS(terminal_total_difficulty=100)
        e.setCustomGeth("./bin/geth")
        e.unlockAccounts()
        e.startMiner()
        if asn == 150:
            if id == 0:
                e.setBootNode(True)
                smart_contract = SmartContract("./contract/deploy.bin", "./contract/deploy.abi") 
                e.deploySmartContract(smart_contract)
            if id == 2:
                e.enableGethHttp()
                emu.getVirtualNode('eth{}'.format(i)).addPortForwarding(8545, 8545)
                emu.getVirtualNode('eth{}'.format(i)).addPortForwarding(8551, 8551)                   
        emu.getVirtualNode('eth{}'.format(i)).setDisplayName('Ethereum-POA-{}'.format(i))
        emu.addBinding(Binding('eth{}'.format(i), filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        i = i+1


# ##############################################
# # Create the PoS Beacon chain layer
# for i in range(1,4):
#     asn = base.getAutonomousSystem(asns[i])
#     pos:Node = asn.createHost("pos-{}".format(i))
#     pos.joinNetwork("net0")
#     pos.importFile("/home/won/seed-emulator/examples/not-ready-examples/27-ethereum-pos/lighthouse_bin/lighthouse", "/usr/bin/lighthouse")
#     pos.importFile("/home/won/seed-emulator/examples/not-ready-examples/27-ethereum-pos/lighthouse_bin/lcli", "/usr/bin/lcli")
    
#     pos.setFile('/tmp/jwt.hex', '0xae7177335e3d4222160e08cecac0ace2cecce3dc3910baada14e26b11d2009fc')

#     pos.setFile("/start_beacon.sh",'''
# #!/bin/bash

# lighthouse boot_node \\
# --testnet-dir ~/.lighthouse/local-testnet/testnet \\
# --port 30303 \\
# --listen-address 0.0.0.0 \\
# --disable-packet-filter \\
# --network-dir ~/.lighthouse/local-testnet/bootnode >> boot.log &

# lighthouse --debug-level info bn \\
# --datadir ~/.lighthouse/local-testnet/node_{} \\
# --testnet-dir ~/.lighthouse/local-testnet/testnet \\ 
# --enable-private-discovery \\
# --staking \\
# --enr-address 0.0.0.0 \\
# --enr-udp-port 9000 \\
# --enr-tcp-port 9000 \\ 
# --port 9000 \\
# --http-port 8000 \\
# --disable-packet-filter \\
# --target-peers 2 \\
# --execution-endpoint http://10.{}.0.71:8551 \\
# --execution-jwt /tmp/jwt.hex >> beacon.log &

# lighthouse --debug-level info vc \\
# --datadir ~/.lighthouse/local-testnet/node_{} \\
# --testnet-dir ~/.lighthouse/local-testnet/testnet \\
# --init-slashing-protection \\
# --beacon-nodes http://localhost:8000 \\
# --suggested-fee-recipient 0x11d0B73242ec1D60A7f67DF9440e511cC84c6b18 >> validator.log & 

# '''.format(i, asns[i], i))
#     pos.appendStartCommand("chmod +x /usr/bin/lcli")
#     pos.appendStartCommand("chmod +x /usr/bin/lighthouse")
#     pos.appendStartCommand("chmod +x /start_beacon.sh")




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
os.system('mkdir ./output/local-testnet')

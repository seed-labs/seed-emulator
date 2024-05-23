#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import os
import platform

###############################################################################
#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

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



hosts_total = 3


###############################################################################
emu     = Emulator()
base    = Base()
routing = Routing()
ebgp    = Ebgp()
ibgp    = Ibgp()
ospf    = Ospf()
web     = WebService()
ovpn    = OpenVpnRemoteAccessProvider()


###############################################################################

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
ix104.getPeeringLan().setDisplayName('Toronto-104')
ix105.getPeeringLan().setDisplayName('Huston-105')


###############################################################################
# Create Transit Autonomous Systems 

## Tier 1 ASes
Makers.makeTransitAs(base, 2, [100, 101, 102, 105], 
       [(100, 101), (101, 102), (100, 105)] 
)

Makers.makeTransitAs(base, 3, [100, 103, 104, 105], 
       [(100, 103), (100, 105), (103, 105), (103, 104)]
)

Makers.makeTransitAs(base, 4, [100, 102, 104], 
       [(100, 104), (102, 104)]
)
# This transit is for lab exercise. Its setup is incomplete
Makers.makeTransitAs(base, 5, [101, 103, 105], 
       [(101, 103), (103, 105)]
)

## Tier 2 ASes
Makers.makeTransitAs(base, 11, [102, 105], [(102, 105)])
Makers.makeTransitAs(base, 12, [101, 104], [(101, 104)])


###############################################################################
# Create single-homed stub ASes. "None" means create a host only 

makeStubAs(emu, base, 150, 100, hosts_total)
makeStubAs(emu, base, 151, 100, hosts_total)

makeStubAs(emu, base, 152, 101, hosts_total)
makeStubAs(emu, base, 153, 101, hosts_total)

makeStubAs(emu, base, 154, 102, hosts_total)
makeStubAs(emu, base, 155, 102, hosts_total)
makeStubAs(emu, base, 156, 102, hosts_total)

makeStubAs(emu, base, 160, 103, hosts_total)
makeStubAs(emu, base, 161, 103, hosts_total)
makeStubAs(emu, base, 162, 103, hosts_total)

makeStubAs(emu, base, 163, 104, hosts_total)
makeStubAs(emu, base, 164, 104, hosts_total)

makeStubAs(emu, base, 170, 105, hosts_total)
makeStubAs(emu, base, 171, 105, hosts_total)

# Create real-world AS.
# AS11872 is the Syracuse University's autonomous system

as11872 = base.createAutonomousSystem(11872)
as11872.createRealWorldRouter('rw-11872-syr').joinNetwork('ix102', '10.102.0.118')


###############################################################################
# Create hybrid AS.
# AS99999 is the emulator's autonomous system that routes the traffics to the real-world internet
as99999 = base.createAutonomousSystem(99999)
as99999.createRealWorldRouter('rw-real-world', prefixes=['0.0.0.0/1', '128.0.0.0/1']).joinNetwork('ix100', '10.100.0.99')
###############################################################################


###############################################################################
# Peering via RS (route server). The default peering mode for RS is PeerRelationship.Peer, 
# which means each AS will only export its customers and their own prefixes. 
# We will use this peering relationship to peer all the ASes in an IX.
# None of them will provide transit service for others. 

ebgp.addRsPeers(100, [2, 3, 4])
ebgp.addRsPeers(102, [2, 4])
ebgp.addRsPeers(104, [3, 4])
ebgp.addRsPeers(105, [2, 3])

# To buy transit services from another autonomous system, 
# we will use private peering  

ebgp.addPrivatePeerings(100, [2],  [150, 151], PeerRelationship.Provider)
ebgp.addPrivatePeerings(100, [3],  [150, 99999], PeerRelationship.Provider)

ebgp.addPrivatePeerings(101, [2],  [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(101, [12], [152, 153], PeerRelationship.Provider)

ebgp.addPrivatePeerings(102, [2, 4],  [11, 154], PeerRelationship.Provider)
ebgp.addPrivatePeerings(102, [11], [154, 11872], PeerRelationship.Provider)

ebgp.addPrivatePeerings(103, [3],  [160, 161, 162 ], PeerRelationship.Provider)

ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [4],  [163], PeerRelationship.Provider)
ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Provider)

ebgp.addPrivatePeerings(105, [3],  [11, 170], PeerRelationship.Provider)
ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Provider)


###############################################################################

# Add layers to the emulator
emu.addLayer(base)
emu.addLayer(routing)
emu.addLayer(ebgp)
emu.addLayer(ibgp)
emu.addLayer(ospf)
emu.addLayer(web)

###############################################################################
# Create the Ethereum layer

eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# Create 10 accounts, each with 100 Ethers. We will use these accounts to
# generate background traffic (sending random transactions from them).
words = "great amazing fun seed lab protect network system security prevent attack future"
blockchain.setLocalAccountParameters(mnemonic=words, total=10, balance=100)

# These 3 accounts are generated from the following phrase:
# "gentle always fun glass foster produce north tail security list example gain"
# They are for users. We will use them in MetaMask, as well as in our sample code.
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=5000)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9',
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24',
                           balance=10)
blockchain.addLocalAccount(address='0xA08Ae0519125194cB516d72402a00A76d0126Af8', balance=20)


asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
hosts_total = 2    # The number of servers per AS
signers  = []
i = 0
for asn in asns:
    for id in range(hosts_total):
        vnode = 'eth{}'.format(i)
        e = blockchain.createNode(vnode)
        displayName = 'Ethereum-POA-%.2d'
        e.enableGethHttp()  # Enable HTTP on all nodes
        e.enableGethWs()    # Enable WS on all nodes for chainlink service to listen
        e.unlockAccounts()
        if i%2  == 0:
            e.startMiner()
            signers.append(vnode)
            displayName = displayName + '-Signer'
            emu.getVirtualNode(vnode).appendClassName("Signer")
        if i%3 == 0:
            e.setBootNode(True)
            displayName = displayName + '-BootNode'
            emu.getVirtualNode(vnode).appendClassName("BootNode")

        emu.getVirtualNode(vnode).setDisplayName(displayName%(i))
        emu.addBinding(Binding(vnode, filter=Filter(asn=asn, nodeName='host_{}'.format(id))))
        i = i+1


# Create the Faucet server
faucet:FaucetServer = blockchain.createFaucetServer(vnode='faucet', 
                                                     port=80, 
                                                     linked_eth_node='eth5',
                                                     balance=10000,
                                                     max_fund_amount=20)

emu.addBinding(Binding('faucet', filter=Filter(asn=150, nodeName='host_2')))
emu.getVirtualNode('faucet').setDisplayName('FaucetServer')

# Create the Chainlink Init server
chainlink = ChainlinkService()

chainlink.setFaucetServer('faucet', 80)
cnode = 'chainlink_init_server'
c_init = chainlink.installInitializer(cnode)
c_init.setLinkedEthNode('eth2')
service_name = 'Chainlink-Init'
emu.getVirtualNode(cnode).setDisplayName(service_name)
emu.addBinding(Binding(cnode, filter = Filter(asn=151, nodeName='host_2')))

c_asns  = [152, 153, 154, 160, 161, 162, 163, 164]
i = 0
# Create Chainlink normal servers
for asn in c_asns:
    cnode = 'chainlink_server_{}'.format(i)
    c_normal = chainlink.install(cnode)
    c_normal.setLinkedEthNode('eth{}'.format(i))
    service_name = 'Chainlink-{}'.format(i)
    emu.getVirtualNode(cnode).setDisplayName(service_name)
    emu.addBinding(Binding(cnode, filter = Filter(asn=asn, nodeName='host_2')))
    i = i + 1
    
# Add the Ethereum layer
emu.addLayer(eth)

# Add the Chainlink layer
emu.addLayer(chainlink)

# Render and compile
OUTPUTDIR = './output'
emu.render()

# Access an environment variable
platform = os.environ.get('platform')

platform_mapping = {
    "amd": Platform.AMD64,
    "arm": Platform.ARM64
}
docker = Docker(internetMapEnabled=True, internetMapPort=8081, etherViewEnabled=True, platform=platform_mapping[platform])

emu.compile(docker, OUTPUTDIR, override = True)

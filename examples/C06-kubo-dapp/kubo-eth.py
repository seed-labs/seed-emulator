#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random

###############################################################################
OUTPUTDIR = './output'
emu = Emulator()

# Load the pre-built components and merge them
emu.load('./base-component.bin')


###############################################################################
# Create the Ethereum layer

eth = EthereumService()
blockchain = eth.createBlockchain(chainName="POA", consensus=ConsensusMechanism.POA)

# These 3 accounts are generated from the following phrase:
# "gentle always fun glass foster produce north tail security list example gain"
# They are for users. We will use them in MetaMask, as well as in our sample code.
blockchain.addLocalAccount(address='0xF5406927254d2dA7F7c28A61191e3Ff1f2400fe9',
                           balance=30)
blockchain.addLocalAccount(address='0x2e2e3a61daC1A2056d9304F79C168cD16aAa88e9', 
                           balance=9999999)
blockchain.addLocalAccount(address='0xCBF1e330F0abD5c1ac979CF2B2B874cfD4902E24', 
                           balance=10)

# The smart contract will be deployed from this account:
blockchain.addLocalAccount(address='0xad15bEbf1992212A57dC3513acc77796110E2bD4', 
                           balance=9999999)

# Create the Ethereum servers. 
asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
hosts_total = 1    # The number of servers per AS
signers  = []
i = 0
for asn in asns:
    for id in range(hosts_total):
        vnode = 'eth{}'.format(i)
        e = blockchain.createNode(vnode)

        displayName = 'Ethereum-POA-%.2d'
        e.enableGethHttp()  # Enable HTTP on all nodes
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

# Add the Ethereum layer
# emu.addLayer(eth)


###############################################################################
# Initialize the KuboService (you may specify additional parameters here):
ipfs = KuboService(gatewayPort=8081)

# Iterate through hosts from base component and install Kubo on them:
asns  = [150, 151, 152, 153, 154, 160, 161, 162, 163, 164]
numHosts = 1   # Number of hosts in the stub AS to install Kubo on
i = 0
webAppCandidates = []
for asNum in asns:
    curAS = emu.getLayer('Base').getAutonomousSystem(asNum)
    # This AS exists, so install Kubo on each host:
    for h in range(numHosts):
        vnode = f'kubo{i}'
        cur = ipfs.install(vnode)
        if i % 5 == 0:
            cur.setBootNode()
            webAppCandidates.append((asNum, f'host_{h}'))
        
        # Modify display name and bind virtual node to a physical node in the Emulator:
        print(f'Bound {vnode} to hnode_{asNum}_host_{h}')
        emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName='host_{}'.format(h), allowBound=True)))
        i += 1
# Add the KuboService layer (ipfs) to the Emulator so that it is rendered and compiled:
# emu.addLayer(ipfs)

###############################################################################
# Expose Ethereum on a node:
ethVnode = random.choice(signers)
ethNode = emu.getVirtualNode(ethVnode)
ethNode.addPortForwarding(8545, 8545)

webKubo = ipfs.install('extraKubo')
asn, node = random.choice(webAppCandidates)
webASN = emu.getLayer('Base').getAutonomousSystem(asn)
webHost = webASN.createHost('webhost').joinNetwork('net0')

# Make changes to active Kubo configuration:
webKubo.setConfig('API.HTTPHeaders.Access-Control-Allow-Origin', ["*"])

# Add software to node:
webHost.addSoftware('curl python3 python3-pip')
webHost.addBuildCommand('curl -fsSL https://deb.nodesource.com/setup_21.x | bash - && apt update -y && apt install -y nodejs')
webHost.addBuildCommand('npm install -g serve')
webHost.addBuildCommand('pip install web3 py-solc-x')   # Used to deploy the smart contract
webHost.addBuildCommand("""python3 -c 'from solcx import install_solc;install_solc(version="0.8.15")'""")

# Allocate node resources:
webHost.addSharedFolder('/volumes', '../volumes')
webHost.addPortForwarding(3000, 3000)
webHost.addPortForwarding(5001, 5001)
webHost.addPortForwarding(8081, 8081)
webHost.setDisplayName('WebHost')
emu.addBinding(Binding('extraKubo', filter = Filter(asn=asn, nodeName='webhost')))

# Render and compile 
emu.addLayer(ipfs)
emu.addLayer(eth)
emu.render()

# Deploy the smart contract:
webHost.appendStartCommand(f'python3 volumes/deployContract.py {getIP(emu.resolvVnode(ethVnode))}')

# Build and run the web app:
webHost.appendStartCommand('serve -sC /volumes/kubo-dapp/build', fork=True)

docker = Docker(internetMapEnabled=True, etherViewEnabled=True)
emu.compile(docker, OUTPUTDIR, override = True)

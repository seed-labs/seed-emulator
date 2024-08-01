#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random
import os, sys
import base_component

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

###############################################################################
OUTPUTDIR = './output'   # Directory to output compiled emulation
emu = Emulator()
base_component.run(dumpfile='./base_component.bin')
# Load the pre-built components and merge them
emu.load('./base_component.bin')


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


###############################################################################
# Initialize the KuboService (you may specify additional parameters here):
if platform == Platform.AMD64:
    arch = Architecture.X64
elif platform == Platform.ARM64:
    arch = Architecture.ARM64
else:
    print("Only AMD64 and ARM64 are supported in current version of SEED.")
    sys.exit(1)

ipfs = KuboService(gatewayPort=8081, arch=arch)

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

# Allocate node resources:
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

# Build (if not built) and run the web app:
webHost.appendStartCommand('cd /volumes/kubo-dapp/ && [ ! -d build ] && npm run build')
webHost.appendStartCommand('serve -sC /volumes/kubo-dapp/build', fork=True)

docker = Docker(internetMapEnabled=True, etherViewEnabled=True, platform=platform)

# Use the "kubo-webhost-image" custom image from local
docker.addImage(DockerImage('kubo-webhost-image', [], local = True), priority=-1)
docker.setImageOverride(webHost, 'kubo-webhost-image')

emu.compile(docker, OUTPUTDIR, override = True)

# Copy the base container image to the output folder
# the base container image should be located under the ouput folder to add it as custom image.
script_dir = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(script_dir, 'kubo-webhost-image')
output_dir = os.path.join(script_dir, 'output')
command = 'cp -r "{image_dir}" "{output_dir}"'.format(image_dir=image_dir, output_dir=output_dir)
os.system(command)
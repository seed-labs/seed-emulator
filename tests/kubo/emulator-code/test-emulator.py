#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random, json, os

###############################################################################
emu = Makers.makeEmulatorBaseWith5StubASAndHosts(2)

###############################################################################


#############################
# Ensure that this can be tested on multiple platforms:
if os.environ.get('platform', 'amd') == 'arm':
    ipfs:KuboService = KuboService(arch=Architecture.ARM)
else:
    ipfs:KuboService = KuboService()

numHosts:int = 2
i:int = 0
kuboAll = []  # vnodes

# Install Kubo on some nodes:
for asNum in range(150, 155):
    try:
        curAS = emu.getLayer('Base').getAutonomousSystem(asNum)
    except:
        print(f'AS {asNum} does\'t appear to exist.')
    else:
        for h in range(numHosts):
            vnode = f'kubo-{i}'
            displayName = f'Kubo-{i}_'
            cur = ipfs.install(vnode)
            if i % 5 == 0:
                cur.setBootNode(True)
                displayName += 'Boot'
            else:
                displayName += 'Peer'
            
            emu.getVirtualNode(vnode).setDisplayName(displayName)
            emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName=f'host_{h}')))
            kuboAll.append(vnode)  # Used to implement further customization for testing
            i += 1
emu.addLayer(ipfs)

kuboPeers = [v for v in kuboAll if not emu.getServerByVirtualNodeName(v).isBootNode()]
            
# Specify profile for a container for testing:
vnode_profile = random.choice(kuboPeers)
emu.getServerByVirtualNodeName(vnode_profile).setProfile('lowpower')


# Specify config for a container for testing.
# Config changes:
#    - Datastore.StorageMax = "20GB"
#    - Gateway.HTTPHeaders.x-kubo-test = "true"
with open('sample-config.json', 'r') as f:
    conf = json.loads(f.read())
vnode_config = random.choice(kuboPeers)
emu.getServerByVirtualNodeName(vnode_config).importConfig(conf)

# Change the Kubo version for a container for testing:
vnode_version = random.choice(kuboPeers)
emu.getServerByVirtualNodeName(vnode_version).setVersion('v0.26.0')
        

# Render and compile 
OUTPUTDIR = './output'
emu.render()

# Add some labels that are used for testing purposes only (must be added to physical nodes post-render):
for vnode in kuboAll: emu.resolvVnode(vnode).setLabel('kubo.test.group', '[\\"basic\\"]')
emu.resolvVnode(vnode_profile).setLabel('kubo.test.group', '[\\"profile\\"]')
emu.resolvVnode(vnode_config).setLabel('kubo.test.group', '[\\"config\\"]')
emu.resolvVnode(vnode_version).setLabel('kubo.test.group', '[\\"basic\\", \\"version\\"]')

emu.compile(Docker(), OUTPUTDIR, override = True)

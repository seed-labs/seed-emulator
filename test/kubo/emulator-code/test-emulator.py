#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random, json

###############################################################################
emu = emu = Makers.makeEmulatorBaseWith5StubASAndHosts(2)

###############################################################################


#############################
ipfs:KuboService = KuboService()

numHosts:int = 2
i:int = 0
kuboServers = []  # vnodes

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
            kuboServers.append(vnode)
            i += 1
emu.addLayer(ipfs)
            
# Specify profile for a container for testing:
vnode_profile = random.choice(kuboServers)
print(vnode_profile)
emu.getServerByVirtualNodeName(vnode_profile).setProfile('lowpower')


# Specify config for a container for testing.
# Config changes:
#    - Datastore.StorageMax = "20GB"
#    - Gateway.HTTPHeaders.x-kubo-test = "true"
with open('sample-config.json', 'r') as f:
    conf = json.loads(f.read())
vnode_config = random.choice(kuboServers)
emu.getServerByVirtualNodeName(vnode_config).importConfig(conf)
        

# Render and compile 
OUTPUTDIR = './output'
emu.render()

# Add some labels that are used for testing purposes only (must be added to physical nodes post-render):
for vnode in kuboServers: emu.resolvVnode(vnode).setLabel('kubo.test.group', '[\\"basic\\"]')
emu.resolvVnode(vnode_profile).setLabel('kubo.test.group', '[\\"profile\\"]')
emu.resolvVnode(vnode_config).setLabel('kubo.test.group', '[\\"config\\"]')


emu.compile(Docker(), OUTPUTDIR, override = True)

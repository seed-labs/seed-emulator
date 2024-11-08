#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import random, json, os

###############################################################################
emu = Makers.makeEmulatorBaseWith5StubASAndHosts(2)

###############################################################################


#############################
# Ensure that this can be tested on multiple platforms:
if os.environ.get('platform') == 'arm':
    ipfs:KuboService = KuboService(arch=Architecture.ARM64)
    docker = Docker(platform=Platform.ARM64)
else:
    ipfs:KuboService = KuboService()
    docker = Docker()
    
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

# Prepare for testing:
kuboPeers = [v for v in kuboAll if not emu.getServerByVirtualNodeName(v).isBootNode()]
testCases = ['profile', 'version', 'set_config', 'import_config', 'replace_config']
testNodes = { group : vnode for (vnode, group) in zip(random.sample(kuboPeers, len(testCases)), testCases) }
            
# Specify profile for a container for testing:
emu.getServerByVirtualNodeName(testNodes['profile']).setProfile('lowpower')

# Specify init config for a container for testing.
# Config changes:
#    - Datastore.StorageMax = "20GB"
#    - Gateway.HTTPHeaders.x-kubo-test = "true"
with open('sample-config.json', 'r') as f:
    conf = json.loads(f.read())
emu.getServerByVirtualNodeName(testNodes['replace_config']).replaceConfig(conf)

# Specify start config for a container, by import:
testConf = {
    'API': {
        'HTTPHeaders': {
            'Access-Control-Allow-Origin': ['*']
        }
    }
}
emu.getServerByVirtualNodeName(testNodes['import_config']).importConfig(testConf)

# Specify start config for a container, by key:
emu.getServerByVirtualNodeName(testNodes['set_config']).setConfig('API.HTTPHeaders.Access-Control-Allow-Origin', ['*'])
emu.getServerByVirtualNodeName(testNodes['set_config']).setConfig('Gateway.ExposeRoutingAPI', True)
emu.getServerByVirtualNodeName(testNodes['set_config']).setConfig('Gateway.RootRedirect', 'ThisIsOnlyATest')

# Change the Kubo version for a container for testing:
emu.getServerByVirtualNodeName(testNodes['version']).setVersion('v0.28.0')
        

# Render and compile 
OUTPUTDIR = './output'
emu.render()

# Add some labels that are used for testing purposes only (must be added to physical nodes post-render):
for vnode in kuboAll: emu.resolvVnode(vnode).setLabel('kubo.test.group', '[\\"basic\\"]')
for group, vnode in testNodes.items(): emu.resolvVnode(vnode).setLabel('kubo.test.group', f'[\\"{group}\\"]')

emu.compile(docker, OUTPUTDIR, override = True)


#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

###############################################################################
emu = Emulator()

# Load the pre-built components and merge them
emu.load('./base-component.bin')

###############################################################################


#############################
ipfs:KuboService = KuboService()
# ipfs.install('kubonode0')
# emu.addBinding(Binding('kubonode0', filter = Filter(asn = 151)))
# emu.getBindingFor('kubonode0').setDisplayName('Kubo Peer 0')

numHosts:int = 1
i:int = 0
bootnodes = []

for asNum in range(150, 172):
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
                # cur.setConfig('API.HTTPHeaders', {"x-test-header": ["Test"]})
                displayName += 'Boot'
                bootnodes.append(vnode)
            else:
                displayName += 'Peer'
            
            emu.getVirtualNode(vnode).setDisplayName(displayName)
            emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName=f'host_{h}')))
            i += 1
        
emu.addLayer(ipfs)

docker = Docker(internetMapEnabled=True, internetMapPort=8081)

# Render and compile 
OUTPUTDIR = './output'
emu.render()
emu.compile(docker, OUTPUTDIR, override = True)

print(f'Created {i} nodes in total.')
print(f'{len(bootnodes)} boot nodes created: {", ".join(bootnodes)}')
print(ipfs.getBootstrapList())

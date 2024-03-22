#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

###############################################################################
emu = emu = Makers.makeEmulatorBaseWith5StubASAndHosts(2)

###############################################################################


#############################
ipfs:KuboService = KuboService()

numHosts:int = 2
i:int = 0

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
            i += 1
        
emu.addLayer(ipfs)

# Render and compile 
OUTPUTDIR = './output'
emu.render()
emu.compile(Docker(), OUTPUTDIR, override = True)

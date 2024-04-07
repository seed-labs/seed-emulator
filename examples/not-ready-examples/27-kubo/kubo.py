#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *

OUTPUTDIR = './output'   # Directory to output compiled emulation

###############################################################################
emu = Emulator()

# Load the pre-built components and merge them
emu.load('./base-component.bin')

###############################################################################


#############################
# Initialize the KuboService (you may specify additional parameters here):
ipfs = KuboService()

# Iterate through hosts from base component and install Kubo on them:
numHosts = 3   # Number of hosts in the stub AS to install Kubo on
i = 0
for asNum in range(150, 172):
    try:
        curAS = emu.getLayer('Base').getAutonomousSystem(asNum)
    except:
        print(f'AS {asNum} does\'t appear to exist.')
    else:
        # This AS exists, so install Kubo on each host:
        for h in range(numHosts):
            vnode = f'kubo-{i}'
            displayName = f'Kubo-{i}_'
            cur = ipfs.install(vnode)
            if i % 5 == 0:
                cur.setBootNode()
                displayName += 'Boot'
            else:
                displayName += 'Peer'
            
            # Modify display name and bind virtual node to a physical node in the Emulator:
            emu.getVirtualNode(vnode).setDisplayName(displayName)
            emu.addBinding(Binding(vnode, filter=Filter(asn=asNum, nodeName=f'host_{h}')))
            i += 1

# Add the KuboService layer (ipfs) to the Emulator so that it is rendered and compiled:
emu.addLayer(ipfs)

# Render and compile 
docker = Docker(internetMapEnabled=True)  # Initialize the desired compiler
emu.render()
emu.compile(docker, OUTPUTDIR, override = True)

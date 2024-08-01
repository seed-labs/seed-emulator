#!/usr/bin/env python3
# encoding: utf-8

from seedemu import *
import base_component
import os, sys

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

OUTPUTDIR = './output'   # Directory to output compiled emulation

###############################################################################
emu = Emulator()
base_component.run(dumpfile='./base_component.bin')
# Load the pre-built components and merge them
emu.load('./base_component.bin')

###############################################################################


#############################
# Initialize the KuboService (you may specify additional parameters here):
if platform == Platform.AMD64:
    arch = Architecture.X64
elif platform == Platform.ARM64:
    arch = Architecture.ARM64
else:
    print("Only AMD64 and ARM64 are supported in current version of SEED.")
    sys.exit(1)

ipfs = KuboService(arch=arch)

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
docker = Docker(internetMapEnabled=True, platform=platform)  # Initialize the desired compiler
emu.render()
emu.compile(docker, OUTPUTDIR, override = True)

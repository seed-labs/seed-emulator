#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.compiler import Docker
from env import getSaveState

emuA = Emulator()
emuB = Emulator()

# Load the pre-built components and merge them
emuA.load('../B00-mini-internet/base-component.bin')
emuB.load('./component-blockchain.bin')
emu = emuA.merge(emuB, DEFAULT_MERGERS)

# Binding virtual nodes to physical nodes
emu.addBinding(Binding('eth1', filter = Filter(asn = 151)))
emu.addBinding(Binding('eth2', filter = Filter(asn = 152)))
emu.addBinding(Binding('eth3', filter = Filter(asn = 163)))
emu.addBinding(Binding('eth4', filter = Filter(asn = 164)))
emu.addBinding(Binding('eth5', filter = Filter(asn = 150)))
emu.addBinding(Binding('eth6', filter = Filter(asn = 170)))

# Callback that will modify the output directory
output = './output'

def updateEthStates(compiler):
    if getSaveState("blockchain.py"):
        compiler.createDirectoryAtBase(output, "eth-states/")
        for i in range(1, 7):
            compiler.createDirectoryAtBase(output, "eth-states/" + str(i))
    else : # Currently This will never run (check comment below)
        compiler.deleteDirectoryAtBase(output, "eth-states/")

# Render and compile
emu.render()

compiler = Docker()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(compiler, output).updateOutputDirectory(compiler, [updateEthStates])


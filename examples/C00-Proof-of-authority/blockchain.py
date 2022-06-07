#!/usr/bin/env python3
# encoding: utf-8

from seedemu.core import Emulator, Binding, Filter
from seedemu.mergers import DEFAULT_MERGERS
from seedemu.compiler import Docker
from os import mkdir, chdir, getcwd, path


emuA = Emulator()
emuB = Emulator()

# Load the pre-built components and merge them
emuA.load('../B00-mini-internet/base-component.bin')
emuB.load('./component-blockchain.bin')
emu = emuA.merge(emuB, DEFAULT_MERGERS)

# Binding virtual nodes to physical nodes
start=1
end=16
for i in range(start, end):
    emu.addBinding(Binding('eth{}'.format(i)))

output = './emulator'

def createDirectoryAtBase(base:str, directory:str, override:bool = False):
    cur = getcwd()
    if path.exists(base):
        chdir(base)
        if override:
            rmtree(directory)
        mkdir(directory)
    chdir(cur)


saveState = True
def updateEthStates():
    if saveState:
        createDirectoryAtBase(output, "eth-states/")
        for i in range(start, end):
            createDirectoryAtBase(output, "eth-states/" + str(i))

# Render and compile
emu.render()

# If output directory exists and override is set to false, we call exit(1)
# updateOutputdirectory will not be called
emu.compile(Docker(ethClientEnabled=False, clientEnabled=False), output)
updateEthStates()

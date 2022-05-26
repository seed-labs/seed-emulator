#!/usr/bin/env python3
# encoding: utf-8

from DockerController import *
from seedemu import *

ctrl = DockerController()

containers = ctrl.getContainersByClassName("WebService")

print(ctrl.execContainers(containers, 'ls'))

ctrl.readFile(containers[0], fileName='/seedemu_worker')

container = ctrl.getContainerById("as151h-dynamic-node-10.151.0.99")
print(container.attrs)
#print(ctrl.getNetworkInfo(container))

# create Dockerfile for a dynamic-node
emu = Emulator()

emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

#ctrl.addNode(emu, scope='151', name='dynamic-node', type='hnode')
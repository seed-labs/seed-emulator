#!/usr/bin/env python3
# encoding: utf-8

from DockerController import *
from seedemu import *

# Instantiate DockerController class
controller = DockerController()

# Get containers by classname 
# returns container list with classname
# classname is assigned using Label:org.seedsecuritylabs.seedemu.meta.class
webContainers = controller.getContainersByClassName("WebService")

container = controller.getContainerById("as151r-router0-10.151.0.254")

# Execute command on containers
# returns a result
ls_result = controller.execContainers(webContainers, 'id')
print("ls_result: \n",ls_result)

# Read file from container
# It just print a file yet.
controller.readFile(webContainers[0], fileName='/seedemu_worker')


# Get networkInfo
# get result of 'ip addr' inside the container 
networkInfo = controller.getNetworkInfo(container)
print("networkInfo: \n", networkInfo)

####################################################################
# Add new node
# create a new node to a existing base-componenet.
emu = Emulator()

emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

# Run a new container based on the added node info. 
controller.addNode(emu, scope='151', name='dynamic-node', type='hnode')
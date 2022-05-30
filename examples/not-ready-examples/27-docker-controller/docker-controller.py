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

# Get container by container name
container = controller.getContainerById("as151r-router0-10.151.0.254")

# Execute command on containers
# returns a result
ls_result = controller.executeCommandInContainers(webContainers, 'id')
print("id_result: \n",ls_result)

# Read file from container
# It just print a file yet.
controller.copyFileToContainer(webContainers[0], fileName='/seedemu_worker')


# Get networkInfo
# get result of 'ip addr' inside the container 
networkInfo = controller.getNetworkInfo(container)
print("networkInfo: \n", networkInfo)

''' Need to be revised. 
####################################################################
# Add new node
# create a new node to a existing base-componenet.
emu = Emulator()

emu.load('./base-component.bin')

base:Base = emu.getLayer('Base')
web:WebService = emu.getLayer('WebService')
web.install('web-dynamic')
as151 = base.getAutonomousSystem(151)
as151.createHost('dynamic-node').joinNetwork('net0', address='10.151.0.99')

as161 = base.getAutonomousSystem(161)
as161.createHost('dynamic-web').joinNetwork('net0')
emu.addBinding(Binding('web-dynamic', filter = Filter(nodeName = 'dynamic-web', asn = 161)))

# Run a new containers 
# - compare new emu with base-component.bin and get newly added nodes.
# - create Dockerfiles for newly added nodes
# - create Images
# - create Containers
# - assign ip address
# - run

#controller.addNodes(emu, './base-component.bin')'''
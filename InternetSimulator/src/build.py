#!/usr/bin/env python3

import csv
import os
from seedsim.simulator import *

# Copy the base folders
os.system("mkdir -p ./output/base_host")
os.system("mkdir -p ./output/base_router")
os.system("cp -rf ./base_images/host/*   ./output/base_host/")
os.system("cp -rf ./base_images/router/* ./output/base_router/")


sim = Simulator("SEED simulator")

sim.getASFromCSV('ases.csv')
print("List of networks -----------------------")
sim.listNetworks()
print("List of ASes -----------------------")
sim.listASes()
print("List of IXPs -----------------------")
sim.listIXPs()

sim.getPeeringsFromCSV('peerings.csv')
print("List of Routers -----------------------")
sim.listRouters()

# Ask the simulator to generate hosts for each network
sim.generateHosts(1)
print("List of Hosts -----------------------")
sim.listHosts()

sim.createHostDockerFiles()
sim.createRouterDockerFiles()
sim.createDockerComposeFile()

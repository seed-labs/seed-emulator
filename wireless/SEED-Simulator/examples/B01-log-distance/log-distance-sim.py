#!/bin/env python3 
from seedsim import *

ITERATION       = 30
NODE_TOTAL      = 30

# To use the Simulation class, you need to define how many nodes you want to use in the SEED emulator. 
# In the example A00-emulator-code, 30 nodes are used. 
# Therefore, in this tutorial, you would input 30 when configuring the Simulation class.
sim = Simulation(NODE_TOTAL)

# You can use the `getNodeList()` method to retrieve a list of node objects initialized in the Simulation class. 
# With the Node objects obtained from this list, you can configure the movement of each node.
nodes = sim.getNodeList()

for i, node in enumerate(nodes):
    mobility = ConstantVelocityMobilityModel(position=Vector(i*10, 0, 0))
    nodes[i].setMobility(mobility)

# Use LogDistancePropagationLossModel
lossModel = LogDistancePropagationLossModel()
sim.appendPropagationLossModel(lossModel=lossModel)

# "ITERATION" is an indicator in the simulation representing how many times nodes will move based on the mobility model. 
# In this tutorial, we are using the constantVelocityMobility model with a velocity set to (0,0,0), 
# indicating that nodes will not move.
for i in range(ITERATION):
    sim.move_nodes()

# Compile tc commands per nodes and iterations from the csv file created from Simulation::move_nodes method. 
# The files will be located in /tmp/seedsim/ folder.
sim.compile_tc_commands(iteration=ITERATION)

#!/bin/env python3 
from seedsim import *
import random

ITERATION       = 30
NODE_TOTAL      = 30
FREQUENCY       = 28.0e9

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

for i, node in enumerate(nodes):
    # Circular
    if i==22 or i==29:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=100, maxRadius=300)
    else:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=200)

    nodes[i].setMobility(mobility)



frequency = FREQUENCY

lossModel = LogDistancePropagationLossModel()
constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)

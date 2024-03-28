#!/bin/env python3 
from seedsim import *

ITERATION       = 30
NODE_TOTAL      = 30
FREQUENCY       = 28.0e9

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

for i, node in enumerate(nodes):
    # Grid
    if i==22 or i==29:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=False)
    else:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=True)

    nodes[i].setMobility(mobility)

frequency = FREQUENCY

lossModel = LogDistancePropagationLossModel()
constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)

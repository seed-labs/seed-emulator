#!/bin/env python3 
from seedsim import *

ITERATION       = 30
NODE_TOTAL      = 30

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

for i, node in enumerate(nodes):
    # Linear
    mobility = LinearMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, length=1000, maxLength=2000)
    nodes[i].setMobility(mobility)

lossModel = LogDistancePropagationLossModel()
constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)

       
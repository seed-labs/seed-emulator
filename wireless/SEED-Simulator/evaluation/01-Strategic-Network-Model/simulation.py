#!/bin/env python3 
from seedsim import *

ITERATION       = 300
NODE_TOTAL      = 16
FREQUENCY       = 28.0e9

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

for i, node in enumerate(nodes):
    mobility = ConstantVelocityMobilityModel(position=Vector(((i//4)*250+(i//4)*250+250)/2, ((i%4)*250 + (i%4)*250+250)/2, 0), velocity=Vector(1.94*((i+1)%2),1.94*(i%2),0))
    mobility.setBoundary(Box((i//4)*250,(i//4)*250+250, (i%4)*250, (i%4)*250+250, 0, 100), isBouncy=True)

    nodes[i].setMobility(mobility)
    nodes[i].setGroup(i//4)
    if i//4 == i%4 :
        nodes[i].setGroup(10)
        
frequency = FREQUENCY

lossModel = FriisPropagationLossModel()
constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)

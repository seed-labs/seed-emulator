#!/bin/env python3 
from seedsim import *
import random
import time

ITERATION       = 30
NODE_TOTAL      = 30

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList() 

for i, node in enumerate(nodes):
    mobility = ConstantVelocityMobilityModel(position=Vector(i*10, 20.0, 1.5), velocity=Vector(round(random.random()*10,2), round(random.random()*10,2), 0))
    mobility.setBoundary(Box(0,10000, 0, 10000, 0, 100), isBouncy=True)
    nodes[i].setMobility(mobility)
    

frequency = 28.0e9

conditionModel = ThreeGppV2vUrbanChannelConditionModel()
threeGppV2vUrban = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)

sim.appendPropagationLossModel(lossModel=threeGppV2vUrban)
   
for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)

    
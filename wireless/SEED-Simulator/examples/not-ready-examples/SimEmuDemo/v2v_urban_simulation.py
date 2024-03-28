#!/bin/env python3 
from seedsim import *
import random

ITERATION       = 30
NODE_TOTAL      = 30

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList() 

for i, node in enumerate(nodes):
    # mobility = ConstantVelocityMobilityModel()
    # mobility.setPosition(Vector(i*10, 20.0, 1.5))
    # mobility.setVelocity(Vector(round(random.random()*10,2), round(random.random()*10,2), 0))
    # mobility.setMobilityBuildingInfo()
    # mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)
    
    # Circular
    # Think about more scenario
    # Write Documents(screenshot or video) , conclusion
    # More investigate and observations 
    # Discuss (goal : get a sense that how our system works)
    # Add some buildings (obstacle)
    # Change the height of the antenna or height of the node
    # change one at a time
    # Expect the result and Observe the result.
    # ex) hypothesis : height of the antenna affect 

    if i==3:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=200, maxRadius=300)
    else:
        mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=200)
    
    # Linear
    # mobility = LinearMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, length=1000, maxLength=1000)
    # Star
    # add speed
    # mobility = StarMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=50, maxRadius=100)

    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)

    # mobility.setMobilityBuildingInfo()
    # mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)
    
    nodes[i].setMobility(mobility)

frequency = 28.0e9
# conditionModel = ThreeGppV2vUrbanChannelConditionModel()
# lossModel = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
# constantDelay = ConstantSpeedPropagationDelayModel()

# conditionModel = ThreeGppUmaChannelConditionModel()
# lossModel = ThreeGppUmaPropagationLossModel(frequency, conditionModel)
# # threeGppV2vUrban.shadowingEnabled = True
# constantDelay = ConstantSpeedPropagationDelayModel() 

lossModel = LogDistancePropagationLossModel()
constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()
       
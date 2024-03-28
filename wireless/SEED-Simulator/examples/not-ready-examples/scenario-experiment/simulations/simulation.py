#!/bin/env python3 
from seedsim import *
import random

ITERATION       = 30
NODE_TOTAL      = 30
BUILDINGS       = True
FREQUENCY       = 28.0e9

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

if BUILDINGS:
    buildingSizeX = 10
    buildingSizeY = 10
    streetWidth = 20
    buildingHeight = 10
    numBuildingsX = 2
    numBuildingsY = 2

    for buildingIdX in range(numBuildingsX):
        for buildingIdY in range(numBuildingsY):
            building = Building()
            building.setBoundaries(
                Box(buildingIdX * (buildingSizeX + streetWidth),
                    buildingIdX * (buildingSizeX + streetWidth) + buildingSizeX,
                    buildingIdY * (buildingSizeY + streetWidth), 
                    buildingIdY * (buildingSizeY + streetWidth) + buildingSizeY,
                    0.0,
                    buildingHeight)
            )
            building.setNumberOfRoomsX(1)
            building.setNumberOfRoomsY(1)
            building.setNumberOfFloors(1)

for i, node in enumerate(nodes):
    # Circular
    # if i==22:
    #     mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=100, maxRadius=300)
    # else:
    #     mobility = CircularMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=200)
    
    # Linear
    # mobility = LinearMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, length=1000, maxLength=2000)
    # Star
    # add speed
    # mobility = StarMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, centerX=100, centerY=100, radius=50, maxRadius=100)

    # Grid
    if i==22:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=False)
    else:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=True)
        
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)

    # mobility.setMobilityBuildingInfo()
    # mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)
    
    nodes[i].setMobility(mobility)



frequency = FREQUENCY
conditionModel = ThreeGppV2vUrbanChannelConditionModel()
lossModel = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
constantDelay = ConstantSpeedPropagationDelayModel()

# conditionModel = ThreeGppUmaChannelConditionModel()
# lossModel = ThreeGppUmaPropagationLossModel(frequency, conditionModel)
# lossModel.shadowingEnabled = True
# constantDelay = ConstantSpeedPropagationDelayModel() 

# lossModel = LogDistancePropagationLossModel()
# constantDelay = ConstantSpeedPropagationDelayModel()

sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()
       
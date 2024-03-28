#!/bin/env python3 
from seedsim import *

ITERATION       = 30
NODE_TOTAL      = 30
BUILDINGS       = True
FREQUENCY       = 28.0e9

sim = Simulation(NODE_TOTAL)

nodes = sim.getNodeList()

if BUILDINGS:
    buildingSizeX = 20
    buildingSizeY = 20
    streetWidth = 10
    buildingHeight = 10
    numBuildingsX = 2
    numBuildingsY = 2

    for buildingIdX in range(numBuildingsX):
        for buildingIdY in range(numBuildingsY):
            building = Building()
            building.setBoundaries(
                Box(buildingIdX * (buildingSizeX + streetWidth) + 1,
                    buildingIdX * (buildingSizeX + streetWidth) + buildingSizeX - 1,
                    buildingIdY * (buildingSizeY + streetWidth) + 1, 
                    buildingIdY * (buildingSizeY + streetWidth) + buildingSizeY - 1,
                    0.0,
                    buildingHeight)
            )
            building.setNumberOfRoomsX(1)
            building.setNumberOfRoomsY(1)
            building.setNumberOfFloors(1)

for i, node in enumerate(nodes):
    # Grid
    if i==22 or i==29:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=False)
    else:
        mobility = GridMobilityModel(nodeId=i, nodeTotal=NODE_TOTAL, colTotal=10, dist=10, paused=True)
        
    mobility.setMobilityBuildingInfo()
    mobility.setBoundary(Box(0,2000, 0, 2000, 0, 100), isBouncy=True)
    
    nodes[i].setMobility(mobility)

frequency = FREQUENCY

conditionModel = ThreeGppV2vUrbanChannelConditionModel()
lossModel = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
constantDelay = ConstantSpeedPropagationDelayModel()


sim.appendPropagationLossModel(lossModel=lossModel)
sim.setPropagationDelayModel(delayModel=constantDelay) 

for i in range(ITERATION):
    sim.move_nodes()

sim.compile_tc_commands(iteration=ITERATION)
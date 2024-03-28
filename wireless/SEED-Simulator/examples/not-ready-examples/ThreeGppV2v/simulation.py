#!/bin/env python3 
from seedsim import *
import argparse
import time
import random
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='command')

init = subparsers.add_parser('init', help='initialize nodes positisons')
move = subparsers.add_parser('move', help='move nodes positions')
highway = subparsers.add_parser('highway', help='ThreeGppV2vHighway')
urban = subparsers.add_parser('urban', help='ThreeGppV2vUrban')
uma = subparsers.add_parser('uma', help='ThreeGppUma')
highway.add_argument("--counts","-c", dest="counts", action="store",
                    default=1,
                    help='move nodes for the given counts (default counts: 1)')

urban.add_argument("--counts","-c", dest="counts", action="store",
                    default=1,
                    help='move nodes for the given counts (default counts: 1)')
urban.add_argument("--shadowingEnabled","-s", dest="shadowingEnabled", action="store_true",
                    help='enable shadowing')
urban.add_argument("--init","-i", dest="init", action="store_true",
                    help='initialize node positions')

uma.add_argument("--counts","-c", dest="counts", action="store",
                    default=1,
                    help='move nodes for the given counts (default counts: 1)')
uma.add_argument("--shadowingEnabled","-s", dest="shadowingEnabled", action="store_true",
                    help='enable shadowing')
uma.add_argument("--init","-i", dest="init", action="store_true",
                    help='initialize node positions')

args = parser.parse_args()


if args.command == "init":
    sim = Simulation(override=True)
    logDist = LogDistancePropagationLossModel()
    nakagami = NakagamiPropagationLossModel()
    constantDelay = ConstantSpeedPropagationDelayModel()
    sim.appendPropagationLossModel(lossModel=logDist)\
        .appendPropagationLossModel(lossModel=nakagami)
    sim.setPropagationDelayModel(delayModel=constantDelay)

    sim.move_nodes_by_manual([(0, 50, 50),
                                (1, 0, 50),
                                ])

    sim.update_loss_and_delay_on_containers()


elif args.command == "highway":   
    sim = Simulation()

    frequency = 28.0e9
    conditionModel = ThreeGppV2vHighwayChannelConditionModel()
    threeGppUrbanHighway = ThreeGppV2vHighwayPropagationLossModel(frequency, conditionModel)
    constantDelay = ConstantSpeedPropagationDelayModel()
    
    # building = Building()
    # building.setBoundaries(
    #     Box(41,49,
    #         10,20,
    #         0.0,10)
    # )
    # building.setNumberOfRoomsX(1)
    # building.setNumberOfRoomsY(1)
    # building.setNumberOfFloors(1)

    nodes = sim.getNodeList() 

    for i, node in enumerate(nodes):
        mobility = ConstantVelocityMobilityModel()
        mobility.setPosition(Vector(i*10, 20.0, 1.5))
        # Set Random Movement
        # Repeat What we did in the summer with the new model.
        mobility.setVelocity(Vector(0, i+1, 0))
        mobility.setMobilityBuildingInfo()
        mobility.setBoundary(Box(0,1000, 0, 1000, 0, 100))
        nodes[i].setMobility(mobility)

    sim.appendPropagationLossModel(lossModel=threeGppUrbanHighway)
    sim.setPropagationDelayModel(delayModel=constantDelay) 
    
    for i in range(int(args.counts)):
        sim.move_nodes()
        sim.update_loss_and_delay_on_containers()
        time.sleep(5)


elif args.command == "urban":   
    sim = Simulation()

    frequency = 28.0e9
    conditionModel = ThreeGppV2vUrbanChannelConditionModel()
    threeGppV2vUrban = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
    constantDelay = ConstantSpeedPropagationDelayModel()
    
    if (args.shadowingEnabled):
        threeGppV2vUrban.shadowingEnabled = True
    # building = Building()
    # building.setBoundaries(
    #     Box(40,50,
    #         30,50,
    #         0.0,10)
    # )
    # building.setNumberOfRoomsX(1)
    # building.setNumberOfRoomsY(1)
    # building.setNumberOfFloors(1)

    buildingSizeX = 25 - 3.5*2 - 3
    buildingSizeY = 43 - 3.5*2 - 3
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

    nodes = sim.getNodeList() 
    
    for i, node in enumerate(nodes):
        if nodes[i].getMobility() == None:
            mobility = ConstantVelocityMobilityModel()
            mobility.setPosition(Vector(i*10, 20.0, 1.5))
            # mobility.setVelocity(Vector(0, i+0.5, 0))
            mobility.setVelocity(Vector(round(random.random()*10,2), round(random.random()*10,2), 0))
            mobility.setMobilityBuildingInfo()
            mobility.setBoundary(Box(0,200, 0, 200, 0, 100))

            nodes[i].setMobility(mobility)
        else:
            mobility = nodes[i].getMobility()
            if args.init:
                mobility.setPosition(Vector(i*10, 20.0, 1.5))
            velocity:Vector = mobility.getVelocity()
            mobility.setMobilityBuildingInfo()
            mobility.setBoundary(Box(0,200, 0, 200, 0, 100), isBouncy=True)


    sim.appendPropagationLossModel(lossModel=threeGppV2vUrban)
    sim.setPropagationDelayModel(delayModel=constantDelay)
    for i in range(int(args.counts)):
        sim.move_nodes()
        sim.update_loss_and_delay_on_containers()
        time.sleep(3)

elif args.command == "uma":   
    sim = Simulation()

    frequency = 28.0e9
    conditionModel = ThreeGppUmaChannelConditionModel()
    uma = ThreeGppUmaPropagationLossModel(frequency, conditionModel)
    if (args.shadowingEnabled):
        uma.shadowingEnabled = True
    constantDelay = ConstantSpeedPropagationDelayModel()

    nodes = sim.getNodeList() 

    for i, node in enumerate(nodes):
        if nodes[i].getMobility() == None:
            mobility = ConstantVelocityMobilityModel()
            mobility.setPosition(Vector(i*10, 20.0, 1.5))
            # mobility.setVelocity(Vector(0, i+0.5, 0))
            mobility.setVelocity(Vector(round(random.random()*10,2), round(random.random()*10,2), 0))
            mobility.setMobilityBuildingInfo()
            mobility.setBoundary(Box(0,1000, 0, 1000, 0, 100))

            nodes[i].setMobility(mobility)
        else:
            mobility = nodes[i].getMobility()
            if args.init:
                mobility.setPosition(Vector(i*10, 20.0, 1.5))
            mobility.setMobilityBuildingInfo()

    sim.appendPropagationLossModel(lossModel=uma)
    sim.setPropagationDelayModel(delayModel=constantDelay) 
    
    for i in range(int(args.counts)):
        sim.move_nodes()
        sim.update_loss_and_delay_on_containers()
        time.sleep(3)


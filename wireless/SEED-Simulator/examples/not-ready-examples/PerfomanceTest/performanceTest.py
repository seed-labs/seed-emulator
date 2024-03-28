#!/bin/env python3 
from seedsim import *
import random
import time

ITERATION       = 10
NODE_TOTAL      = 30

with open('./elapsedTimes.csv', 'a', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ')
    columns = "Scenario Iterations NumNodes ElaspedTime"
    writer.writerow(columns.split())

test_num_nodes = [10, 30, 50, 100, 300, 500]
test_iterations = [1, 5, 10]
test_scenario = ["v2v-highway"]

for scenario in test_scenario:
    for iteration in test_iterations:
        for num_nodes in test_num_nodes:
            sim = Simulation(num_nodes)

            nodes = sim.getNodeList() 

            for i, node in enumerate(nodes):
                mobility = ConstantVelocityMobilityModel()
                mobility.setPosition(Vector(i*10, 20.0, 1.5))
                mobility.setVelocity(Vector(round(random.random()*10,2), round(random.random()*10,2), 0))
                mobility.setMobilityBuildingInfo()
                mobility.setBoundary(Box(0,10000, 0, 10000, 0, 100), isBouncy=True)

                nodes[i].setMobility(mobility)

            frequency = 28.0e9
            if scenario == "v2v-urban":
                conditionModel = ThreeGppV2vUrbanChannelConditionModel()
                threeGppV2vUrban = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
                # constantDelay = ConstantSpeedPropagationDelayModel()

                sim.appendPropagationLossModel(lossModel=threeGppV2vUrban)
                # sim.setPropagationDelayModel(delayModel=constantDelay) 
            else:
                conditionModel = ThreeGppV2vHighwayChannelConditionModel()
                threeGppV2vHighway = ThreeGppV2vHighwayPropagationLossModel(frequency, conditionModel)
                # constantDelay = ConstantSpeedPropagationDelayModel()

                sim.appendPropagationLossModel(lossModel=threeGppV2vHighway)
                # sim.setPropagationDelayModel(delayModel=constantDelay) 

            current_time = time.time()
            for i in range(iteration):
                sim.move_nodes()

            elapsed_time = time.time() - current_time

            with open('./elapsedTimes.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                columns = [scenario, iteration, num_nodes, elapsed_time]
                writer.writerow(columns)

    
#!/bin/env python3 
from seedsim import *
import time

ITERATION       = 1
NODE_TOTAL      = 2
FREQUENCY       = 28.0e9

distance_list = range(10, 101) 

csv_file = 'distance_result.csv'
with open(csv_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ')
    columns = "Distance LossRate"
    writer.writerow(columns.split())

for distance in distance_list:
     
    sim = Simulation(NODE_TOTAL)

    nodeA = sim.getNodeList()[0]
    nodeB = sim.getNodeList()[1]

    mobilityA = ConstantVelocityMobilityModel(position=Vector(0, 0, 0))
    nodeA.setMobility(mobilityA)
    mobilityB = ConstantVelocityMobilityModel(position=Vector(distance, 0, 0))
    nodeB.setMobility(mobilityB)

    conditionModel = ThreeGppV2vUrbanChannelConditionModel()
    conditionModel.setUpdatePeriod(updatePeriod=0.1)
    lossModel = ThreeGppV2vUrbanPropagationLossModel(FREQUENCY, conditionModel)
    
    while True:
        time.sleep(0.1)
        loss = lossModel.calcLossRate(nodeA, nodeB, txPower=16.0206)

        if (lossModel.getChannelConditionModel().getChannelCondition(nodeA, nodeB).getLosCondition().value) == LosConditionValue.NLOSv.value:
            with open(csv_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                rows = [distance, loss]
                writer.writerow(rows)
            break


#!/bin/env python3 
from seedsim import *
import time

ITERATION       = 1
NODE_TOTAL      = 2
DISTANCE        = 30

frequency_list = range(int(24.0e9), int(52.0e9) + 1, int(1e9))

csv_file = 'frequency_result.csv'
with open(csv_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ')
    columns = "Distance Frequency LossRate"
    writer.writerow(columns.split())

for frequency in frequency_list:
    print(frequency)
    
    sim = Simulation(NODE_TOTAL)

    nodeA = sim.getNodeList()[0]
    nodeB = sim.getNodeList()[1]

    mobilityA = ConstantVelocityMobilityModel(position=Vector(0, 0, 0))
    nodeA.setMobility(mobilityA)
    mobilityB = ConstantVelocityMobilityModel(position=Vector(DISTANCE, 0, 0))
    nodeB.setMobility(mobilityB)

    conditionModel = ThreeGppV2vUrbanChannelConditionModel()
    conditionModel.setUpdatePeriod(updatePeriod=0.1)
    lossModel = ThreeGppV2vUrbanPropagationLossModel(frequency, conditionModel)
    
    while True:
        time.sleep(0.1)
        loss = lossModel.calcLossRate(nodeA, nodeB, txPower=16.0206)

        if (lossModel.getChannelConditionModel().getChannelCondition(nodeA, nodeB).getLosCondition().value) == LosConditionValue.NLOSv.value:
            with open(csv_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                rows = [DISTANCE, frequency, loss]
                writer.writerow(rows)
            break


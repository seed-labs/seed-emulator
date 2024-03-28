#!/bin/env python3 
from seedsim import *
import time

ITERATION       = 1
NODE_TOTAL      = 2
DISTANCE        = 30
FREQUENCY       = 28.0e9

txpower_list = range(15, 31) # tx power list in dbm

csv_file = 'txpower_result.csv'
with open(csv_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile, delimiter=' ')
    columns = "Distance TxPower LossRate"
    writer.writerow(columns.split())

for txpower in txpower_list:
     
    sim = Simulation(NODE_TOTAL)

    nodeA = sim.getNodeList()[0]
    nodeB = sim.getNodeList()[1]

    mobilityA = ConstantVelocityMobilityModel(position=Vector(0, 0, 0))
    nodeA.setMobility(mobilityA)
    mobilityB = ConstantVelocityMobilityModel(position=Vector(DISTANCE, 0, 0))
    nodeB.setMobility(mobilityB)

    conditionModel = ThreeGppV2vUrbanChannelConditionModel()
    conditionModel.setUpdatePeriod(updatePeriod=0.1)
    lossModel = ThreeGppV2vUrbanPropagationLossModel(FREQUENCY, conditionModel)
    
    while True:
        time.sleep(0.1)
        loss = lossModel.calcLossRate(nodeA, nodeB, txPower=txpower)

        if (lossModel.getChannelConditionModel().getChannelCondition(nodeA, nodeB).getLosCondition().value) == LosConditionValue.NLOSv.value:
            with open(csv_file, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile, delimiter=' ')
                rows = [DISTANCE, txpower, loss]
                writer.writerow(rows)
            break


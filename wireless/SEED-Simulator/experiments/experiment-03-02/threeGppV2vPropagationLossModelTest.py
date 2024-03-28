#!/usr/bin/env python3
# encoding: utf-8

from seedsim import *
import unittest as ut
import time
import pandas as pd



class ThreeGppPropagationLossTestCase(ut.TestCase):
    frequency:float

    @classmethod
    def setUpClass(cls) -> None:
        cls.frequency = 28.0e9

        cls.node_a:NodeInfo = NodeInfo(node_id=1, container_id="temp", ipaddress="10.150.0.1")
        cls.node_b:NodeInfo = NodeInfo(node_id=2, container_id="temp", ipaddress="10.150.0.2")
        return
    
    @classmethod
    def setBuilding(cls):
        buildingSizeX = 250 - 3.5*2 - 3
        buildingSizeY = 433 - 3.5*2 - 3
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

    def test_constant_velocity_mobility_model(self):
        vScatt = 140 / 3.6
        vTx = vScatt
        vRx = vScatt / 2
        mobilityA = ConstantVelocityMobilityModel()
        mobilityA.setPosition(Vector(300.0, 20.0, 1.5))\
                .setVelocity(Vector(0.0, vTx, 0.0))
        mobilityA.setMobilityBuildingInfo()
        mobilityB = ConstantVelocityMobilityModel()
        mobilityB.setPosition(Vector(300.0, 0.0, 1.5))\
                .setVelocity(Vector(0.0, vRx, 0.0))
        mobilityB.setMobilityBuildingInfo()
        
        self.node_a.setMobility(mobilityA)
        self.node_b.setMobility(mobilityB)

        output = pd.read_csv('/home/won/seedblock/wireless/propagationModel/test/v2v-highway-output.txt', delimiter=' ')   

        for i in range(60):
            _, x_1, y_1, z_1, x_2, y_2, z_2, los, _, pathLoss = output.loc[i]

            positionA = self.node_a.getMobility().getPosition()
            positionB = self.node_b.getMobility().getPosition()
            self.assertTrue(round(positionA.x,2)==round(x_1, 2))
            self.assertTrue(round(positionA.y,2)==round(y_1, 2))
            self.assertTrue(round(positionA.z,2)==round(z_1, 2))

            self.assertTrue(round(positionB.x,2)==round(x_2, 2))
            self.assertTrue(round(positionB.y,2)==round(y_2, 2))
            self.assertTrue(round(positionB.z,2)==round(z_2, 2))

            time.sleep(1)

    def test_highway(self):
        file = "v2v-highway-output.txt"
        file_path = os.path.join(os.path.dirname(__file__), file)
        
        output = pd.read_csv(file_path, delimiter=' ')        
        
        uniformRandom.line = 0
        
        mobilityA = ManualMobilityModel(file=file_path, role=MobilityNodeRole.tx)
        mobilityB = ManualMobilityModel(file=file_path, role=MobilityNodeRole.rx)
        mobilityA.setMobilityBuildingInfo()
        mobilityB.setMobilityBuildingInfo()
        conditionModel = ThreeGppV2vHighwayChannelConditionModel()
        propagationModel = ThreeGppV2vHighwayPropagationLossModel(self.frequency, conditionModel)
        conditionModel.setUpdatePeriod(1)
        propagationModel.shadowingEnabled = False     
        self.node_a.setMobility(mobilityA)
        self.node_b.setMobility(mobilityB)

        los_diff = 0
        loss_diff = 0
        for i in range(60):
            _, x_1, y_1, z_1, x_2, y_2, z_2, los, _, pathLoss = output.loc[i]
            los = los.strip()

            result_los = conditionModel.getChannelCondition(self.node_a, self.node_b, test=True).getLosCondition().value
            if los != result_los:
                los_diff += 1
            
            rxPower = self.get_rx_power(lossModel=propagationModel)
            if los == "LOS" and round(rxPower*(-1),3) != round(pathLoss,3):
                print(round(rxPower*(-1),3))
                print(round(pathLoss,3))
                loss_diff += 1
            time.sleep(1)

        self.assertTrue(los_diff==0, "los diff should be 0 but its value is "+ str(los_diff))
        self.assertTrue(loss_diff==0, "loss diff should be 0 but its value is "+ str(loss_diff))

    def test_urban(self):
        self.setBuilding()
        uniformRandom.line = 0
        
        file = "v2v-urban-output.txt"
        file_path = os.path.join(os.path.dirname(__file__), file)
        
        output = pd.read_csv(file_path, delimiter=' ')        

        mobilityA = ManualMobilityModel(file=file_path, role=MobilityNodeRole.tx)
        mobilityB = ManualMobilityModel(file=file_path, role=MobilityNodeRole.rx)
        mobilityA.setMobilityBuildingInfo()
        mobilityB.setMobilityBuildingInfo()
        conditionModel = ThreeGppV2vUrbanChannelConditionModel()
        propagationModel = ThreeGppV2vUrbanPropagationLossModel(self.frequency, conditionModel)
        conditionModel.setUpdatePeriod(1)
        propagationModel.shadowingEnabled = False
            

        self.node_a.setMobility(mobilityA)
        self.node_b.setMobility(mobilityB)
        
        los_diff = 0
        loss_diff = 0
        
        for i in range(60):
            _, x_1, y_1, z_1, x_2, y_2, z_2, los, _, pathLoss = output.loc[i]
            los = los.strip()

            result_los = conditionModel.getChannelCondition(self.node_a, self.node_b, test=True).getLosCondition().value
            if los != result_los:
                los_diff += 1
            
            rxPower = self.get_rx_power(lossModel=propagationModel)
            lossRate = self.get_loss_rate(lossModel=propagationModel)
            
            if los == "LOS" and round(rxPower*(-1),3) != round(pathLoss,3):
                loss_diff += 1
            time.sleep(1)

        self.assertTrue(los_diff==0, "los diff should be 0 but its value is "+str(los_diff))
        self.assertTrue(loss_diff==0, "loss diff should be 0 but its value is "+str(loss_diff))
        # when it is nlosv or nlos, it uses random value so hard check it is true or not.
    
    def get_rx_power(self, lossModel:PropagationLossModel):
        return lossModel.doCalcRxPower(txPower=0, node_a=self.node_a, node_b=self.node_b)

    def get_loss_rate(self, lossModel:PropagationLossModel):
        return lossModel.calcLossRate(node_a=self.node_a, node_b=self.node_b, txPower=30, threshold=-82)
    
        
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        # test_suite.addTest(cls('test_constant_velocity_mobility_model'))
        test_suite.addTest(cls('test_highway'))
        test_suite.addTest(cls('test_urban'))
        return test_suite
    
if __name__ == "__main__":
    ts = ThreeGppPropagationLossTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(ts)
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)



#!/usr/bin/env python3
# encoding: utf-8

from seedsim import *
import unittest as ut


class ThreeGppPropagationLossTestCase(ut.TestCase):
    frequency:float
    scenarios:list

    @classmethod
    def setUpClass(cls) -> None:
        cls.frequency = 2125.0e6
        cls.scenarios = ["RMa", "UMa", "UMi-StreetCanyon", "Inh-OfficeOpen", "InH-OfficeMixed"]
        cls.node_a = NodeInfo(node_id=1, container_id="temp", ipaddress="10.150.0.1", x=0, y=0, z=10)
        cls.node_b = NodeInfo(node_id=2, container_id="temp", ipaddress="10.150.0.2", x=10, y=0, z=1.6)
        mobilityA = ConstantPositionMobilityModel(position=Vector(0,0,10))
        mobilityB = ConstantPositionMobilityModel(position=Vector(10, 0, 1.6))
        cls.node_a.setMobility(mobilityA)
        cls.node_b.setMobility(mobilityB)
        return
    
    def test_RMa(self):
        condModel = ThreeGppRmaChannelConditionModel()
        lossModel = ThreeGppRmaPropagationLossModel(frequency=self.frequency, channelConditionModel=condModel)
        lossModel.shadowingEnabled = True
        rxPower = self.get_loss_rate(lossModel)
        print(rxPower)
        self.assertTrue(round(rxPower,4)== -61.1584)

    def test_UMa(self):
        condModel = ThreeGppUmaChannelConditionModel()
        lossModel = ThreeGppUmaPropagationLossModel(frequency=self.frequency, channelConditionModel=condModel)
        lossModel.shadowingEnabled = False
        rxPower = self.get_rx_power(lossModel)
        print(round(rxPower, 4))

        self.assertTrue(round(rxPower,4)== -59.0978)

    def test_UMi_StreetCanyon(self):
        condModel = ThreeGppUmiStreetCanyonChannelConditionModel()
        lossModel = ThreeGppUmiStreetCanyonPropagationLossModel(frequency=self.frequency, channelConditionModel=condModel)
        lossModel.shadowingEnabled = False
        rxPower = self.get_rx_power(lossModel)
        print(round(rxPower, 4))

        self.assertTrue(round(rxPower,4)== -62.3819)

    def test_InH_OfficeOpen(self):
        condModel = ThreeGppIndoorOpenOfficeChannelConditionModel()
        lossModel = ThreeGppIndoorOfficePropagationLossModel(frequency=self.frequency, channelConditionModel=condModel)
        lossModel.shadowingEnabled = False
        rxPower = self.get_rx_power(lossModel)
        print(round(rxPower, 4))
        if lossModel.channelConditionModel.getChannelCondition(self.node_a, self.node_b).losCondition == LosConditionValue.NLOS:
            self.assertTrue(round(rxPower,4)== -68.1917)
        elif lossModel.channelConditionModel.getChannelCondition(self.node_a, self.node_b).losCondition == LosConditionValue.LOS:
            self.assertTrue(round(rxPower,4) == -58.2529)
    
    def test_InH_OfficeMixed(self):
        condModel = ThreeGppIndoorMixedOfficeChannelConditionModel()
        lossModel = ThreeGppIndoorOfficePropagationLossModel(frequency=self.frequency, channelConditionModel=condModel)
        lossModel.shadowingEnabled = False
        rxPower = self.get_rx_power(lossModel)
        print(round(rxPower, 4))

        if lossModel.channelConditionModel.getChannelCondition(self.node_a, self.node_b).losCondition == LosConditionValue.NLOS:
            self.assertTrue(round(rxPower,4)== -68.1917)
        elif lossModel.channelConditionModel.getChannelCondition(self.node_a, self.node_b).losCondition == LosConditionValue.LOS:
            self.assertTrue(round(rxPower,4) == -58.2529)

    
    def get_rx_power(self, lossModel:PropagationLossModel):
        
        return lossModel.doCalcRxPower(txPower=0, node_a=self.node_a, node_b=self.node_b)
        # node_a.move()
        # node_b.move()
        # lossModel.doCalcRxPower(txPower=0, node_a=node_a, node_b=node_b)
    
    def get_loss_rate(self, lossModel:PropagationLossModel):
        return lossModel.calcLossRate(node_a=self.node_a, node_b=self.node_a, txPower=30, threshold=-82)
    
    @classmethod
    def get_test_suite(cls):
        test_suite = ut.TestSuite()
        test_suite.addTest(cls('test_RMa'))
        # test_suite.addTest(cls('test_UMa'))
        # test_suite.addTest(cls('test_UMi_StreetCanyon'))
        # test_suite.addTest(cls('test_InH_OfficeOpen'))
        # test_suite.addTest(cls('test_InH_OfficeMixed'))

        return test_suite
    
if __name__ == "__main__":
    ts = ThreeGppPropagationLossTestCase.get_test_suite()
    res = ut.TextTestRunner(verbosity=2).run(ts)
    num, errs, fails = res.testsRun, len(res.errors), len(res.failures)



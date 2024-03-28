from __future__ import annotations
from typing import List
import numpy as np
from scipy.stats import gamma
from ..NodeInfo import *

M_PI = 3.14159265358979323846
class PropagationLossModel:
    mLoss:List[PropagationLossModel]
    # txPower in dBm
    txPower:float
    threshold:float

    def __init__(self):
        self.mLoss=[]
        self.txPower = 16.0206
        self.threshold = -82
        return
    
    def setTxPower(self, txPower):
        self.txPower = txPower
        return self

    def getPropagationLossModelByIndex(self, index=0):
        return self.mLoss[index]
    
    def appendLossModel(self,lossModel:PropagationLossModel):
        self.mLoss.append(lossModel)
    
    def calcRxPower(self, node_a, node_b, txPower=None):
        if not txPower: txPower = self.txPower

        rxPower = txPower
        for loss in self.mLoss:
            rxPower = loss.doCalcRxPower(rxPower, node_a, node_b)
        return rxPower
    
    def calcLossRate(self, node_a:NodeInfo, node_b:NodeInfo, txPower=None, threshold=None):
        if not txPower: txPower = self.txPower
        if not threshold: threshold = self.threshold
        rxPower = txPower
        for i, loss in enumerate(self.mLoss):
            if i == len(self.mLoss)-1:
                return loss.calcLossRate(txPower=rxPower, node_a=node_a, node_b=node_b, threshold=threshold)
            rxPower = loss.doCalcRxPower(rxPower, node_a, node_b)
    
    def doCalcRxPower(self, txPower, node_a:NodeInfo, node_b:NodeInfo):
        pass

    def getDistance2D(self, a_position:Vector, b_position:Vector):
        a = np.array((a_position.x, a_position.y))
        b = np.array((b_position.x, b_position.y))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist
    
    def getDistance3D(self, a_position:Vector, b_position:Vector):
        a = np.array((a_position.x, a_position.y))
        b = np.array((b_position.x, b_position.y))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist
    
    def _getDisplacementLen2D(self, vector_1, vector_2):

        a = np.array((vector_1.x, vector_1.y))
        b = np.array((vector_2.x, vector_2.y))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist

    def _getVectorDifference(self, a_position, b_position):
        x = a_position.x - b_position.x
        y = a_position.y - b_position.y

        return Vector(x,y,0)
    
    def getChannelType(self):
        return "GeneralChannel"

class LogDistancePropagationLossModel(PropagationLossModel):
    referenceDistance:float

    def __init__(self):
        self.referenceDistance = 1.0
        self.exponent = 3.0
        self.referenceLoss = 46.6777


    def doCalcRxPower(self, txPower, node_a:NodeInfo, node_b:NodeInfo):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)

        if (distance <= self.referenceDistance):
            return txPower - self.referenceDistance
        
        pathLossDb = 10 * self.exponent * np.log10(distance/self.referenceDistance)
        rxc = -self.referenceLoss - pathLossDb

        return txPower+rxc
    
    def calcLossRate(self, txPower, node_a:NodeInfo, node_b:NodeInfo, threshold):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)
        
        if (distance <= self.referenceDistance):
            return txPower - self.referenceDistance
        
        pathLossDb = 10 * self.exponent * np.log10(distance/self.referenceDistance)
        rxc = -self.referenceLoss - pathLossDb
        if txPower + rxc > threshold:
            return 0.0
        else:
            return 1.0 * 100

    
class NakagamiPropagationLossModel(PropagationLossModel):
    
    def __init__(self):
        # self.alpha = 1.5
        # self.beta = 4.58447e-12
        self.distance1 = 80.0
        self.distance2 = 200.0
        self.m0 = 1.5
        self.m1 = 0.75
        self.m2 = 0.75


    def doCalcRxPower(self, txPower, node_a:NodeInfo, node_b:NodeInfo):
        m:float = 0.0
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)

        if distance<self.distance1:
            m=self.m0
        elif distance<self.distance2:
            m=self.m1
        else:
            m=self.m2
        
        powerW = 10**((txPower-30)/10)

        # alpha = m
        # beta = powerW/m
        resultPowerW = np.random.gamma(m, powerW/m)
        
        resultPowerDbm = 10*np.log10(resultPowerW) + 30
        
        return resultPowerDbm
    
    def calcLossRate(self, txPower, node_a:NodeInfo, node_b:NodeInfo, threshold):
        m:float = 0.0
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)

        if distance<self.distance1:
            m=self.m0
        elif distance<self.distance2:
            m=self.m1
        else:
            m=self.m2
        
        powerW = 10**((txPower-30)/10)
        thresholdW = 10**((threshold-30)/10)
        
        loss = gamma.cdf(x=thresholdW, a=m, scale=powerW/m)

        return loss * 100
    
class FriisPropagationLossModel(PropagationLossModel):
    
    def __init__(self):
        self.frequency = 5.150e9    # "The carrier frequency (in Hz) at which propagation occurs (default is 5.15 GHz).",
        self.system_loss = 1.0
        self.min_loss = 0.0         # "The minimum value (dB) of the total loss, used at short ranges."
        self.c = 299792458.0        # speed of light in vacuum
        self.m_lambda = self.c / self.frequency


    def doCalcRxPower(self, txPower, node_a:NodeInfo, node_b:NodeInfo):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)

        if (distance < 3 * self.m_lambda):
            print("distance not within the far field region => inaccurate propagation loss value")
        if (distance <= 0):
            return txPower - self.min_loss
        
        numerator = self.m_lambda * self.m_lambda
        denominator = 16 * M_PI * M_PI * distance * distance * self.system_loss
        loss = -10 * np.log10(numerator / denominator)
        # NS_LOG_DEBUG("distance=" << distance << "m, loss=" << lossDb << "dB, minLoss=" << m_minLoss);
        return txPower - max(loss, self.min_loss)
    
    
    def calcLossRate(self, txPower, node_a:NodeInfo, node_b:NodeInfo, threshold):
        a_position = node_a.getMobility().getPosition()
        b_position = node_b.getMobility().getPosition()
        distance = self.getDistance2D(a_position, b_position)

        if (distance < 3 * self.m_lambda):
            print("distance not within the far field region => inaccurate propagation loss value")
        if (distance <= 0):
            return txPower - self.min_loss
        
        numerator = self.m_lambda * self.m_lambda
        denominator = 16 * M_PI * M_PI * distance * distance * self.system_loss
        loss = -10 * np.log10(numerator / denominator)

        if txPower - max(loss, self.min_loss) > threshold:
            return 0.0
        else:
            return 1.0 * 100
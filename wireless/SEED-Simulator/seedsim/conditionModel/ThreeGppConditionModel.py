"""
Copyright (c) 2020 SIGNET Lab, Department of Information Engineering,
University of Padova

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License version 2 as
published by the Free Software Foundation;

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
"""

import time
import numpy as np

from ..NodeInfo import NodeInfo
from .ChannelConditionModel import *
from .BuildingsChannelConditionModel import *
from ..testRandom import uniformRandom

class ThreeGppConditionModel(ChannelConditionModel):
    updatePeriod = 0
    o2iThreshold = 0.0
    o2iLowLossThreshold = 1.0
    linkO2iConditionToAntennaHeight = False
    channelConditionMap = {}

    def __init__(self) -> None:
        pass

    def getChannelCondition(self, node_a:NodeInfo, node_b:NodeInfo, test:bool=False):
        cond = ChannelCondition()
        key = self.getKey(node_a, node_b)

        notFound = False
        update = False
        now = time.time()
        if key in self.channelConditionMap.keys():
            item:Item = self.channelConditionMap[key]
            cond = item.channelCondition
            
            if (self.updatePeriod != 0 and \
                now - item.generatedTime > self.updatePeriod):
                update = True

            if (node_a.is_moved or node_b.is_moved):
                update = True
                print("update")
        else:
            notFound = True
        
        if (notFound or update):
            cond = self.computeChannelCondition(node_a, node_b, test)
            mapItem = Item(cond, now)
            self.channelConditionMap[key] = mapItem

        return cond
    
    def getKey(self, node_a:NodeInfo, node_b:NodeInfo):
        x1 = min(node_a.id, node_b.id)
        x2 = max(node_a.id, node_b.id)

        key = (((x1 + x2) * (x1 + x2 + 1)) / 2) + x2
        
        return key
    
    def computeChannelCondition(self, node_a:NodeInfo, node_b:NodeInfo, test:bool=False):
        cond = ChannelCondition()

        pLos = self.computePlos(node_a, node_b)
        pNlos = self.computePnlos(node_a, node_b)
        if test:
            pRef = uniformRandom.getRandom()
        else:
            pRef = np.random.uniform(0,1)
        # print(node_a.getMobility().getPosition().x, node_a.getMobility().getPosition().y, node_b.getMobility().getPosition().x, node_b.getMobility().getPosition().y, "pRef ", pRef, " pLos ", pLos, " pNlos ", pNlos)
        
        if (pRef <= pLos):
            cond.setLosCondition(LosConditionValue.LOS)
        elif (pRef <= pLos + pNlos):
            cond.setLosCondition(LosConditionValue.NLOS)
        else:
            cond.setLosCondition(LosConditionValue.NLOSv)
        
        return cond


    def computeO2i(self, node_a:NodeInfo, node_b:NodeInfo):
        o2iProbability = np.random.uniform(0,1)
        positionA = node_a.getMobility().getPosition()
        positionB = node_b.getMobility().getPosition()
        if(self.linkO2iConditionToAntennaHeight):
            if(min(positionA.z, positionB.z) == 1.5):
                return O2iConditionValue.O2O
            else:
                return O2iConditionValue.O2I
            
        else:
            if o2iProbability < self.o2iThreshold:
                return O2iConditionValue.O2I
            else:
                return O2iConditionValue.O2O
            
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        pass

    def computePnlos(self, node_a:NodeInfo, node_b:NodeInfo):
        return 1- self.computePlos(node_a, node_b)
    
    def _getDistance2D(self, a_position, b_position):
        a = np.array((a_position.x, a_position.y))
        b = np.array((b_position.x, b_position.y))

        dist = np.sqrt(np.sum(np.square(a-b)))
        return dist
    
    def setUpdatePeriod(self, updatePeriod):
        self.updatePeriod = updatePeriod
        return self
    
class ThreeGppRmaChannelConditionModel(ThreeGppConditionModel):
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())

        pLos = 0.0
        if (distance2D <= 10.0):
            pLos = 1.0
        else:
            pLos = np.exp (-(distance2D - 10.0)/1000.0)

        return pLos

class ThreeGppUmaChannelConditionModel(ThreeGppConditionModel):
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        utHeight = min(node_a.getMobility().getPosition().z, node_b.getMobility().getPosition().z)

        if (utHeight > 23.0):
            print("The height of the UT should be smaller than 23 m")

        bsHeight = max(node_a.getMobility().getPosition().z, node_b.getMobility().getPosition().z)

        if (bsHeight != 25.0):
            print("The LOS probability was derived assuming BS antenna heights of 25m")

        pLos = 0.0
        if (distance2D <= 18.0):
            pLos = 1.0
        else:
            c = 0.0
            if utHeight <= 13:
                c = 0
            else:
                c = pow((utHeight - 13.0)/10.0, 1.5)
            
            pLos = (18.0 / distance2D + np.exp(-distance2D / 63.0) * (1.0 - 18.0 / distance2D)) *\
               (1.0 + c * 5.0 / 4.0 * pow(distance2D / 100.0, 3.0) * np.exp(-distance2D / 150.0))

        return pLos
    
class ThreeGppUmiStreetCanyonChannelConditionModel(ThreeGppConditionModel):
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        
        bsHeight = max(node_a.getMobility().getPosition()[2], node_b.getMobility().getPosition()[2])

        if (bsHeight != 10.0):
            print("The LOS probability was derived assuming BS antenna heights of 10m")

        pLos = 0.0
        if (distance2D <= 18.0):
            pLos = 1.0
        else:
            pLos = 18.0 / distance2D + np.exp(-distance2D / 36.0) * (1.0 - 18.0 / distance2D)

        return pLos


class ThreeGppIndoorMixedOfficeChannelConditionModel(ThreeGppConditionModel):
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        
        bsHeight = max(node_a.getMobility().getPosition()[2], node_b.getMobility().getPosition()[2])

        if (bsHeight != 3.0):
            print("The LOS probability was derived assuming BS antenna heights of 3 m (see TR "
                    "38.901, Table 7.4.2-1)")

        pLos = 0.0
        if (distance2D <= 1.2):
            pLos = 1.0
        elif (distance2D > 1.2 and distance2D < 6.5):
            pLos = np.exp(-(distance2D - 1.2) / 4.7)
        else:
            pLos = np.exp(-(distance2D - 6.5) / 32.6) * 0.32

        return pLos
    
class ThreeGppIndoorOpenOfficeChannelConditionModel(ThreeGppConditionModel):
    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
        
        bsHeight = max(node_a.getMobility().getPosition()[2], node_b.getMobility().getPosition()[2])

        if (bsHeight != 3.0):
            print("The LOS probability was derived assuming BS antenna heights of 3 m (see TR "
                    "38.901, Table 7.4.2-1)")

        pLos = 0.0
        if (distance2D <= 5.0):
            pLos = 1.0
        elif (distance2D > 5.0 and distance2D <= 49.0):
            pLos = np.exp(-(distance2D - 5.0) / 70.8)
        else:
            pLos = np.exp(-(distance2D - 49.0) / 211.7) * 0.54

        return pLos

class ThreeGppV2vUrbanChannelConditionModel(ThreeGppConditionModel):
    buildingsChannelConditionModel:BuildingsChannelConditionModel

    def __init__(self) -> None:
        super().__init__()
        self.buildingsChannelConditionModel = BuildingsChannelConditionModel() 

    def computePlos(self, node_a:NodeInfo, node_b:NodeInfo):
        cond = self.buildingsChannelConditionModel.getChannelCondition(node_a, node_b)
        pLos = 0.0
        if cond.getLosCondition()==LosConditionValue.LOS:
            distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
            pLos = min(1.0, 1.05 * np.exp(-0.0114 * distance2D))
        return pLos
    
    def computePnlos(self, node_a, node_b):
        cond = self.buildingsChannelConditionModel.getChannelCondition(node_a, node_b)

        pNlos = 0.0
        if cond.getLosCondition()==LosConditionValue.NLOS:
            pNlos = 1.0

        return pNlos
    
class ThreeGppV2vHighwayChannelConditionModel(ThreeGppConditionModel):
    buildingsChannelConditionModel:BuildingsChannelConditionModel

    def __init__(self) -> None:
        super().__init__()
        self.buildingsChannelConditionModel = BuildingsChannelConditionModel()

    def computePlos(self, node_a: NodeInfo, node_b: NodeInfo):
        cond = self.buildingsChannelConditionModel.getChannelCondition(node_a, node_b)

        pLos = 0.0
        if(cond.getLosCondition()==LosConditionValue.LOS):
            distance2D = self._getDistance2D(node_a.getMobility().getPosition(), node_b.getMobility().getPosition())
            if (distance2D <= 475.0):
                pLos = min(1.0, 2.1013e-6 * distance2D * distance2D - 0.002 * distance2D + 1.0193)
            else:
                pLos = max(0.0, 0.54 - 0.001 * (distance2D - 475.0))
        return pLos
    
    def computePnlos(self, node_a: NodeInfo, node_b: NodeInfo):
        cond = self.buildingsChannelConditionModel.getChannelCondition(node_a, node_b)
        pNlos = 0
        if (cond.getLosCondition()==LosConditionValue.NLOS):
            pNlos = 1.0
        return pNlos
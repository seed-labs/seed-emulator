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

from .ChannelConditionModel import *
from .BuildingsChannelConditionModel import *

class BuildingsChannelConditionModel(ChannelConditionModel):
    updatePeriod = 0
    o2iThreshold = 0.0
    o2iLowLossThreshold = 1.0
    linkO2iConditionToAntennaHeight = False
    channelConditionMap = {}

    def __init__(self) -> None:
        pass

    def getChannelCondition(self, node_a:NodeInfo, node_b:NodeInfo):
        mobilityA = node_a.getMobility()
        mobilityB = node_b.getMobility()
        
        mobilityBuildingInfoA = mobilityA.getMobilityBuildingInfo()
        mobilityBuildingInfoB = mobilityB.getMobilityBuildingInfo()

        cond = ChannelCondition()

        isAIndoor = mobilityBuildingInfoA.isIndoor()
        isBIndoor = mobilityBuildingInfoB.isIndoor()

        # if a and b are outdoor
        if (not isAIndoor) and (not isBIndoor):
            cond.setO2iCondition(O2iConditionValue.O2O)
            # TO DO: 
            blocked = self.isLineOfSightBlocked(mobilityA.getPosition(), mobilityB.getPosition())

            if (blocked):
                # print("blocked")
                cond.setLosCondition(LosConditionValue.NLOS)
            else:
                cond.setLosCondition(LosConditionValue.LOS)
        elif (isAIndoor and isBIndoor):
            cond.setO2iCondition(O2iConditionValue.I2I)

            if(mobilityBuildingInfoA.getBuildingId() == mobilityBuildingInfoB.getBuildingId()):
                cond.setLosCondition(LosConditionValue.LOS)
            else:
                cond.setLosCondition(LosConditionValue.NLOS)
            
        else:
            cond.setO2iCondition(O2iConditionValue.O2I)
            cond.setLosCondition(LosConditionValue.NLOS)
        
        return cond
    
    def isLineOfSightBlocked(self, positionA:Vector, positionB:Vector):
        for building in BuildingList.getBuildings():
            building:Building
            if building.isIntersect(positionA, positionB):
                return True
        
        return False
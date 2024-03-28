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

from enum import Enum
from ..NodeInfo import *
from collections import namedtuple

Item = namedtuple("Item", ['channelCondition', 'generatedTime'])

class LosConditionValue(Enum):
    # Line of Sight
    LOS = 'LOS'
    # None Line of Sight
    NLOS = 'NLOS'
    # None Line of Sight due to a vehicle
    NLOSv = 'NLOSv'

class O2iConditionValue(Enum):
    O2O = 'O2O'
    O2I = 'O2I'
    I2I = 'I2I'

class ChannelCondition:
    losCondition:LosConditionValue
    o2iCondition:O2iConditionValue
    
    def __init__(self) -> None:
        pass

    def getLosCondition(self):
        return self.losCondition
    
    def setLosCondition(self, losCondition:LosConditionValue):
        self.losCondition = losCondition
        return self
    
    def getO2iCondition(self):
        return self.o2iCondition
    
    def setO2iCondition(self, o2iCondition:O2iConditionValue):
        self.o2iCondition = o2iCondition
        return self
    
class ChannelConditionModel:
    
    def getChannelCondition(self, node_a:NodeInfo, node_b:NodeInfo):
        pass


from .MobilityModel import *
from .Box import *
import time
import os
from pathlib import Path
import pandas as pd
from enum import Enum

class MobilityNodeRole(Enum):
    tx = 'Transmitter'
    rx = 'Receiver'

class ManualMobilityHelper():
    isPaused:bool
    position:Vector
    index:int = 0
    role:MobilityNodeRole
    lastUpdate:float
    
    
    def __init__(self, position=None, path=None, role:MobilityNodeRole=MobilityNodeRole.tx):
        self.position = position if position else Vector(0,0,0)
        self.path = path
        self.output = pd.read_csv(path, delimiter=' ')
        self.role = role
        self.lastUpdate=0
    
    def getPosition(self):
        return self.position
    
    def setPosition(self, position):
        self.position = position
    
    def updatePosition(self):
        now = time.time()
        if self.lastUpdate != 0:
            if now - self.lastUpdate < 1:
                return
        self.lastUpdate = now
        _, x_1, y_1, z_1, x_2, y_2, z_2, _, _, _  = self.output.loc[self.index]
        if self.role == MobilityNodeRole.tx:
            self.position = Vector(x_1, y_1, z_1)
        else:
            self.position = Vector(x_2, y_2, z_2)

        self.index += 1


    
class ManualMobilityModel(MobilityModel):
    helper:ManualMobilityHelper

    def __init__(self, file, role:MobilityNodeRole=MobilityNodeRole.tx, position=None, velocity=None, ):
        super().__init__(position, velocity)
        self.helper = ManualMobilityHelper(path=file, role=role)
        self.helper.setPosition(position=position)
    
    def doGetPosition(self):
        self.helper.updatePosition()
        return self.helper.getPosition()
    
    def doSetPosition(self, position):
        self.helper.setPosition(position)
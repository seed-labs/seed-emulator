#!/bin/env python3 

import math
from .MobilityModel import *
import time

class LinearMobilityHelper():
    isPaused:bool
    position:Vector
    length:float
    maxLength:float
    lastUpdate:float
    nodeId:int
    nodeTotal:int
    
    def __init__(self, nodeId, nodeTotal, length=None, maxLength=None, paused=True):
        self.nodeId=nodeId
        self.nodeTotal = nodeTotal
        self.length=length
        self.maxLength=maxLength
        self.isPaused = paused
        self.position = self.calculateLinearPosition()

    def getPosition(self):
        return self.position
    
    def setPosition(self, position):
        self.position = position
    
    def setMaxLength(self, maxLength):
        self.maxLength = maxLength
        self.lastUpdate = time.time()
    
    def updatePosition(self, isRealtime:bool=False, deltaS:int = 1):
        now = time.time()
        
        if self.isPaused:
            return
        
        if isRealtime:
            if now - self.lastUpdate < 1:
                return
            deltaS = round(now - self.lastUpdate)
        else:
            # SeedSimLogger.debug(clsname=__name__, msg="deltaS = 1")
            deltaS = deltaS

        if not self.isPaused:
            self.lastUpdate = now
            self.length += 5 * deltaS

            if self.length > self.maxLength:
                return
            else:
                self.position = self.calculateLinearPosition()

    def pause(self):
        self.isPaused = True
        return self
    
    def unpause(self):
        self.isPaused = False
        return self
    
    def calculateLinearPosition(self):
        x = self.nodeId * (self.length / (self.nodeTotal - 1))
        return Vector(round(x,2), 50, 0)

class LinearMobilityModel(MobilityModel):
    helper:LinearMobilityHelper

    def __init__(self, nodeId, nodeTotal, length, maxLength):
        self.helper = LinearMobilityHelper(nodeId=nodeId, nodeTotal=nodeTotal, length=length)
        if maxLength is not None:
            self.setMaxLength(maxLength)
        super().__init__(self.helper.getPosition())

    def doGetVelocity(self):
        return Vector(0.0, 0.0, 0.0)
    
    def doUpdatePosition(self):
        return self.helper.updatePosition(deltaS=self.deltaS)

    def doGetPosition(self):
        # self.helper.updatePosition(self.boundary, self.isBouncy)
        return self.helper.getPosition()
    
    def doSetPosition(self, position):
        self.helper.setPosition(position)
    
    def setMaxLength(self, maxLength):
        self.helper.setMaxLength(maxLength)
        self.helper.unpause()
        return self
        #notifyCourseChange()


# # Example usage:
# center_x = 10
# center_y = 10
# radius = 5
# num_points = 10

# circle_coordinates = calculate_circle_coordinates(center_x, center_y, radius, num_points)

# # Print the result
# for x, y in circle_coordinates:
#     print(f"({x}, {y})")
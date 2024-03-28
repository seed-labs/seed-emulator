#!/bin/env python3 

import math
from .MobilityModel import *
import time

class GridMobilityHelper():
    isPaused:bool
    position:Vector
    colTotal:int
    lastUpdate:float
    nodeId:int
    nodeTotal:int
    dist:float
    positionId:int
    
    def __init__(self, nodeId, nodeTotal, colTotal, dist, paused):
        self.nodeId = nodeId
        self.positionId = nodeId
        self.nodeTotal = nodeTotal
        self.colTotal = colTotal
        self.dist = dist
        self.isPaused = paused
        self.position = self.calculateGridPosition()

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
            self.position = self.calculateGridPosition()
            self.positionId += 1


    def pause(self):
        self.isPaused = True
        return self
    
    def unpause(self):
        self.isPaused = False
        return self
    
    def calculateGridPosition(self):
        x = (self.positionId % self.colTotal)*self.dist
        y = (self.positionId // self.colTotal)*self.dist
        return Vector(round(x,2), round(y,2), 0)

class GridMobilityModel(MobilityModel):
    helper:GridMobilityHelper

    def __init__(self, nodeId, nodeTotal, colTotal=5, dist=50, paused=True):
        self.helper = GridMobilityHelper(nodeId=nodeId, nodeTotal=nodeTotal, colTotal=colTotal, dist=dist, paused=paused)
        if not paused:
            self.helper.unpause()
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

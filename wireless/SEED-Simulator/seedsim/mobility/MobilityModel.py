from __future__ import annotations
from .Vector import *
from .Building import *

class MobilityBuildingInfo:
    indoor:bool
    nFloor:int
    roomX:int
    roomY:int
    building:Building
    mobilityModel:MobilityModel

    def __init__(self, mobilityModel) -> None:
        self.indoor = False
        self.nFloor = 1
        self.roomX = 1
        self.roomY = 1
        self.mobilityModel = mobilityModel
        self.building = None
        self.prevPosition = Vector(0,0,0)
    
    def isIndoor(self):
        currentPosition = self.mobilityModel.getPosition()
        posEqual = (currentPosition == self.prevPosition)
        if not posEqual:
            self.updatePosition()
        return self.indoor

    def getBuilding(self):
        return self.building
    
    def getBuildingId(self):
        return self.building.id

    def setIndoor(self, building:Building, floor, roomx, roomy):
        self.indoor = True
        self.building = building
        self.nFloor = floor
        self.roomX = roomx
        self.roomY = roomy
    
    def setOutdoor(self):
        self.indoor = False

    def updatePosition(self):
        isInBuilding = False
        position = self.mobilityModel.getPosition()
        for building in BuildingList.getBuildings():
            building:Building
            if building.isInside(position):
                isInBuilding = True
                floor = building.getFloorByPosition(position)
                roomX = building.getRoomXByPosition(position)
                roomY = building.getRoomYByPosition(position)
                self.setIndoor(building, floor, roomX, roomY)
                break
        
        if not isInBuilding:
            self.setOutdoor()
        
        self.prevPosition = position




class MobilityModel:
    position:Vector
    velocity:Vector
    mobilityBuildingInfo:MobilityBuildingInfo
    boundary:Box
    isBouncy:bool
    deltaS:int
    isMoved:bool

    def __init__(self, position:Vector=None, velocity:Vector=None):
        self.position = position if position else Vector(0,0,0)
        self.velocity = velocity if velocity else Vector(0,0,0)
        self.mobilityBuildingInfo = MobilityBuildingInfo(self)
        self.boundary = None
        self.isBouncy = False
        self.deltaS = 1
        self.isMoved = False

    def getPosition(self)-> Vector: 
        prev_position = self.position
        self.position = self.doGetPosition()
        if prev_position.isMoved(self.position):
            
            self.isMoved=False
        else:
            self.isMoved=True
        return self.position
    
    def updatePosition(self)->Vector:
        return self.doUpdatePosition()
    
    def setBoundary(self, boundary:Box, isBouncy:bool=False):
        self.boundary = boundary
        self.isBouncy = isBouncy
        return self
    
    def setDeltaS(self, deltaS:int):
        '''
        @brief By default, 1 iteration = 1 second  
        It is customizable by changing deltaS
        1 iteration = deltaS sec.
        '''
        self.deltaS = deltaS
        return self
    
    def getDeltaS(self):
        return self.deltaS
    
    def setPosition(self, position):
        self.doSetPosition(position)
        return self

    def getVelocity(self):
        return self.doGetVelocity()
    
    def setVelocity(self, velocity):
        self.velocity = velocity
        return self

    def doGetVelocity(self):
        raise NotImplementedError
    
    def doGetPosition(self):
        raise NotImplementedError
    
    def doUpdatePosition(self):
        raise NotImplementedError
    
    def doSetPosition(self, position):
        raise NotImplementedError
    
    def setMobilityBuildingInfo(self):
        self.mobilityBuildingInfo = MobilityBuildingInfo(self)

    def getMobilityBuildingInfo(self):
        return self.mobilityBuildingInfo
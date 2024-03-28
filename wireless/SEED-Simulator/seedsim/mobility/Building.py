from __future__ import annotations
from .Box import *
from .Vector import *
from math import floor
    
class Building():
    # The number of rooms in the X axis
    rooms_x:int
    # The number of rooms in the Y axis
    rooms_y:int
    floors:int
    id:int
    boundaries:Box
    # todo:
    # the type of building
    # ExternealWalls type
    def __init__(self):
        self.id = BuildingList.add(self)
    
    def getId(self):
        return self.id
    
    def setBoundaries(self, boundaries:Box):
        self.boundaries = boundaries

    def setNumberOfFloors(self, floors):
        self.floors = floors

    def setNumberOfRoomsX(self, rooms_x):
        self.rooms_x = rooms_x

    def setNumberOfRoomsY(self, rooms_y):
        self.rooms_y = rooms_y

    def getBoundaries(self):
        return self.boundaries
    
    def getNumberOfFloors(self):
        return self.floors
    
    def getNumberOfRoomsX(self):
        return self.rooms_x
    
    def getNumberOfRoomsY(self):
        return self.rooms_y
    
    def isInside(self, position:Vector):
        return self.boundaries.isInside(position)
    
    # GetRoomX
    def getRoomXByPosition(self, position:Vector):
        if (position.x == self.boundaries.x_max):
            return self.rooms_x
        else:
            x_len = self.boundaries.x_max - self.boundaries.x_min
            x = position.x - self.boundaries.x_min
            return floor(self.rooms_x*x/x_len) + 1
           
    # GetRoomY
    def getRoomYByPosition(self, position:Vector):
        if position.y == self.boundaries.y_max:
            return self.rooms_y
        else:
            y_len = self.boundaries.y_max - self.boundaries.y_min
            y = position.y - self.boundaries.y_min
            return floor(self.rooms_y*y/y_len) + 1
        
    # GetFloor
    def getFloorByPosition(self, position:Vector):
        if position.y == self.boundaries.z_max:
            return self.floors
        else:
            z_len = self.boundaries.z_max - self.boundaries.z_min
            z = position.z - self.boundaries.z_min
            return floor(self.floors*z/z_len) + 1
    
    def isIntersect(self, positionA:Vector, positionB:Vector):
        return self.boundaries.isIntersect(positionA, positionB)
    
    def to_dict(self):
         return {
              'id': self.id,
            #   'x': (self.boundaries.x_max + self.boundaries.x_min)/2,
            #   'y': (self.boundaries.y_max + self.boundaries.y_min)/2,
            #   'z': (self.boundaries.z_max + self.boundaries.z_min)/2,
              'x': self.boundaries.x_min,
              'y': self.boundaries.y_min,
              'z': self.boundaries.z_min,
              'width': self.boundaries.x_max - self.boundaries.x_min,
              'height': self.boundaries.y_max - self.boundaries.y_min
         }


class BuildingList(object):
    building_list = []
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(BuildingList, cls).__new__(cls)
        return cls.instance
    
    # allow access to class methods on the class without creating an instance.
    @classmethod
    def add(cls, building:Building):
        id = len(cls.building_list)
        cls.building_list.append(building)
        return id
    
    @classmethod
    def getBuildings(cls):
        return cls.building_list
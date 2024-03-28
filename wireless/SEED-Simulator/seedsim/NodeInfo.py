#!/bin/env python3

from typing import Tuple
from json import JSONEncoder
import random
from .mobility import *

class NodeInfoEncoder(JSONEncoder):
        def default(self, o):
            return o.to_dict() 
        
class NodeInfo:
    id:int
    # position : (x, y)
    x:int
    y:int
    z:int
    # direction : (dx, dy)
    direction:Tuple[int, int]
    mobility:MobilityModel
    container_id:str
    ipaddress:str
    distance:dict
    connectivity:list
    is_moved:bool

    def __init__(self, node_id:int, container_id:str, ipaddress:str,
                 x:int=None, y:int=None, z:int=None, distance:dict={}, connectivity:list=[],
                 direction:list=None) -> None:
        self.id = node_id
        self.ipaddress = ipaddress
        self.container_id = container_id
        self.distance = distance
        self.connectivity = connectivity

        self.x = int(node_id%6) * 10 if x is None else x  
        self.y = int(node_id//6) * 10 if y is None else y
        self.z = int(node_id%6) * 10 if z is None else z

        if direction: self.direction = direction
        else: self.__setDirection()

        self.mobility = ConstantVelocityMobilityModel(position=Vector(self.x, self.y, self.z), velocity=Vector(self.direction[0], self.direction[1], 0))
        self.is_moved = False

    def __setDirection(self):
        dx = random.randint(-10, 10)
        dy = random.randint(-10, 10)
        self.direction = (dx, dy)

    def getMobility(self):
        return self.mobility

    def getPosition(self):
        #  print(self.x, self.y, self.z)
         return (self.x, self.y, self.z)
    
    def setMobility(self, mobility):
         self.mobility = mobility
         return self
    
    def to_dict(self):
         return {
              'id': self.id,
              'x': self.x,
              'y': self.y,
              'z': self.z,
              'direction': self.direction,
              'distance': self.distance,
              'container_id': self.container_id,
              'ipaddress': self.ipaddress,
              'connectivity': self.connectivity
         }

    # def move(self):
    #     x, y = self.x, self.y
    #     dx, dy = self.direction

    #     if x+dx > 100 or x+dx < 0:
    #         dx *= (-1)

    #     if y+dy > 100 or y+dy < 0:
    #         dy *= (-1)

    #     self.x, self.y = (x+dx, y+dy)
    #     self.direction = (dx, dy)

    #     return self
    
    def move(self):
        '''
        @brief move nodes according to the mobility model. 
        @return time the node moves
        '''
        prevPosition = self.mobility.getPosition()
        self.mobility.updatePosition()
        position = self.mobility.getPosition()
        self.is_moved = prevPosition.isMoved(position)
        self.x, self.y, self.z = position.x, position.y, position.z

        return self
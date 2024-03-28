from .MobilityModel import *
from .Box import *
import time
from ..SeedSimLogger import *

class ConstantVelocityHelper():
    isPaused:bool
    isInitialPosition:bool
    position:Vector
    velocity:Vector
    lastUpdate:float

    def __init__(self, position=None, velocity=None, paused=True):
        self.position = position if position else Vector(0,0,0)
        self.velocity = velocity if velocity else Vector(0,0,0)
        self.isPaused = paused
        self.isInitialPosition = True
    def getVelocity(self):
        return Vector(0,0,0) if self.isPaused else self.velocity
    
    def setVelocity(self, velocity):
        self.velocity = velocity
        self.lastUpdate = time.time()
    
    def getPosition(self):
        return self.position
    
    def setPosition(self, position):
        self.position = position
    
    def updatePosition(self, bounds:Box=None, isBouncy:bool=False, isRealtime:bool=False, deltaS:int = 1):
        now = time.time()
        if self.isInitialPosition:
            self.isInitialPosition=False
            return
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
            self.position.x += self.velocity.x * deltaS
            self.position.y += self.velocity.y * deltaS
            self.position.z += self.velocity.z * deltaS

            if bounds:
                self.position.x = min(bounds.x_max, self.position.x)
                self.position.x = max(bounds.x_min, self.position.x)
                self.position.y = min(bounds.y_max, self.position.y)
                self.position.y = max(bounds.y_min, self.position.y)
                self.position.z = min(bounds.z_max, self.position.z)
                self.position.z = max(bounds.z_min, self.position.z)
                if isBouncy:
                    if self.position.x in [bounds.x_max, bounds.x_min]:
                        self.velocity.x *= -1
                    if self.position.y in [bounds.y_max, bounds.y_min]:
                        self.velocity.y *= -1

    def pause(self):
        self.isPaused = True
        return self
    
    def unpause(self):
        self.isPaused = False
        return self
    
class ConstantVelocityMobilityModel(MobilityModel):
    helper:ConstantVelocityHelper

    def __init__(self, position=None, velocity=None):
        super().__init__(position, velocity)
        self.helper = ConstantVelocityHelper()
        self.helper.setPosition(position)
        if velocity is not None:
            self.setVelocity(velocity)

    def doGetVelocity(self):
        return self.helper.getVelocity()
    
    def doUpdatePosition(self):
        return self.helper.updatePosition(self.boundary, self.isBouncy, deltaS=self.deltaS)

    def doGetPosition(self):
        # self.helper.updatePosition(self.boundary, self.isBouncy)
        return self.helper.getPosition()
    
    def doSetPosition(self, position):
        self.helper.setPosition(position)
    
    def setVelocity(self, velocity):
        self.helper.setVelocity(velocity)
        self.helper.unpause()
        return self
        #notifyCourseChange()
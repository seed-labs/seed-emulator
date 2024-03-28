from .MobilityModel import *
from .Box import *
    
class ConstantPositionMobilityModel(MobilityModel):

    def __init__(self, position):
        super().__init__(position)
    
    def doGetPosition(self):
        return self.position
    
    def doSetPosition(self, position):
        self.position = position
    
    def doGetVelocity(self):
        return Vector(0.0, 0.0, 0.0)
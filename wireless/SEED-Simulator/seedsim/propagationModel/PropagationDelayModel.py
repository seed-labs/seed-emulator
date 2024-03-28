import random

class PropagationDelayModel:
    def getDelay(self, dist):
        pass

class ConstantSpeedPropagationDelayModel(PropagationDelayModel):
    __speed:float

    def __init__(self):
        # speed of light
        self.__speed = 299792458

    def getDelay(self, dist):
        microseconds = dist / self.__speed * 10**6
        
        return microseconds
    
class RandomPropagationDelayModel(PropagationDelayModel):
    __min:float
    __max:float

    def __init__(self) -> None:
        self.__min = 0.0
        self.__max = 1.0

    def getDelay(self, dist):
        microseconds = random.uniform(self.__min, self.__max)* 10**6
        return microseconds
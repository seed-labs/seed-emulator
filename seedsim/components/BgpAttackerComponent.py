from seedsim.core import Component, Simulator, AutonomousSystem
from seedsim.layers import Base, Router, Routing

class BgpAttackerComponent(Component):

    __data: Simulator
    __hijacker_as: AutonomousSystem
    __routing: Routing
    __hijacker: Router
    __counter: int

    def __init__(self):
        self.__data = Simulator()
        self.__counter = 0

        base = Base()
        self.__routing = Routing()

        self.__hijacker_as = base.createAutonomousSystem(666)
        self.__hijacker = self.__hijacker_as.createRouter('hijacker')

        self.__data.addLayer(base)
        self.__data.addLayer(self.__routing)

    def get(self) -> Simulator:
        return self.__data

    def addHijackedPrefix(self, prefix: str):
        netname = 'h{}'.format(self.__counter)
        self.__hijacker_as.createNetwork(netname, prefix)
        self.__hijacker.joinNetwork(netname)
        self.__routing.addDirect(666, netname)
        self.__counter += 1

    def joinInternetExchange(self, ix: str, addr: str):
        self.__hijacker.joinNetwork(ix, addr)
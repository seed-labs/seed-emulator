from seedsim.core import Component, Simulator, AutonomousSystem
from seedsim.layers import Base, Router

class BgpAttackerComponent(Component):

    __data: Simulator
    __hijacker_as: AutonomousSystem
    __hijacker: Router
    __counter: int

    def __init__(self):
        self.__data = Simulator()
        self.__counter = 0

        base = Base()

        self.__hijacker_as = base.createAutonomousSystem(666)
        self.__hijacker = self.__hijacker_as.createRouter('hijacker')

        self.__data.addLayer(base)

    def get(self) -> Simulator:
        return self.__data

    def addHijackedPrefix(self, prefix: str):
        self.__hijacker.addProtocol('static', 'h{}'.format(self.__counter), '''
            route {} via blackhole;
        ''')
        self.__counter += 1
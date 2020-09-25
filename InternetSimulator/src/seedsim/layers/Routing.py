from .Layer import Layer
from seedsim.core import Registry
from typing import List

class Routing(Layer):
    """!
    @brief The Routing layer.

    This layer provides routing support for routers. i.e., this layer install
    BIRD on nodes and allow BGP/OSPF to work.

    This layer will also setup direct protocol for host networks, kernel
    protocol, etc.
    """

    __reg: Registry = Registry()
    
    def getName(self) -> str:
        return "Routing"

    def getDependencies(self) -> List[str]:
        return ["Base"]

    def onRender(self):
        for ((scope, type, name), obj) in self.__reg.getAll().items():
            if type == 'rs':
                print("===== RoutingLayer: TODO: Bootstrap bird.conf for RS {}".format(name))
                
            if type == 'rnode':
                print("===== RoutingLayer: TODO: Bootstrap bird.conf for AS{} router {}".format(scope, name))

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'RoutingLayer\n'

        return out
from seedsim.layers.Layer import Layer
from seedsim.core import AutonomousSystem
from seedsim.core import Simulator
from seedsim.core import Printable
from typing import Dict, List

class Base(Layer):
    """!
    The base layer.
    """

    __ases: Dict[int, AutonomousSystem]

    def __init__(self):
        """!
        @brief Base layer constructor.
        """
        self.__ases = {}

    def getName(self) -> str:
        return "Base"

    def getDependencies(self) -> List[str]:
        return []

    def onRender(self, simulator: Simulator) -> None:
        pass

    def createAutonomousSystem(self, asn: int) -> AutonomousSystem:
        """!
        @brief Create a new AutonomousSystem.

        @param asn ASN of the new AS.
        @returns created AS.
        @throws AssertionError if asn exists.
        """
        assert asn not in self.__ases, "as{} already exist.".format(asn)
        self.__ases[asn] = AutonomousSystem(asn)
        return self.__ases[asn]

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BaseLayer:\n'

        for _as in self.__ases.values():
            out += _as.print(indent + 4)

        return out
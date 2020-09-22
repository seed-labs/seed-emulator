from seedsim.layers.Layer import Layer
from seedsim.core.AutonomousSystem import AutonomousSystem
from seedsim.core.Simulator import Simulator
from typing import Dict, List

class Base(Layer):
    """!
    The base layer.
    """

    __ases: Dict[int, AutonomousSystem] = {}

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
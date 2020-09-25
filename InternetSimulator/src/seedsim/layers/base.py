from seedsim.layers.Layer import Layer
from seedsim.core import AutonomousSystem, InternetExchange, Printable, Registry, AddressAssignmentConstraint
from typing import Dict, List

class Base(Layer):
    """!
    The base layer.
    """

    __ases: Dict[int, AutonomousSystem]
    __ixes: Dict[int, InternetExchange]
    __reg = Registry()

    def __init__(self):
        """!
        @brief Base layer constructor.
        """
        self.__ases = {}
        self.__ixes = {}

    def getName(self) -> str:
        return "Base"

    def getDependencies(self) -> List[str]:
        return []

    def onRender(self) -> None:
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

    def createInternetExchange(self, asn: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None) -> InternetExchange:
        """!
        @brief Create a new InternetExchange.

        @param asn ASN of the new IX.
        @param prefix (optional) prefix of the IX peering LAN.
        @param aac (optional) Address assigment constraint.
        @returns created IX.
        @throws AssertionError if IX exists.
        """
        assert asn not in self.__ases, "ix{} already exist.".format(asn)
        self.__ixes[asn] = InternetExchange(asn, prefix, aac)
        return self.__ixes[asn]

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BaseLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'AutonomousSystems:\n'
        for _as in self.__ases.values():
            out += _as.print(indent + 4)

        out += ' ' * indent
        out += 'InternetExchanges:\n'
        for _as in self.__ixes.values():
            out += _as.print(indent + 4)

        return out
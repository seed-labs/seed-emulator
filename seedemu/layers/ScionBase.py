from __future__ import annotations
from typing import Dict, List, Optional

from seedemu.core import Emulator, IsolationDomain, ScionAutonomousSystem
from seedemu.layers import Base


class ScionBase(Base):
    """!
    @brief Base layer for SCION.
    """

    __isds: Dict[int, IsolationDomain]

    def __init__(self):
        super().__init__()
        self.__isds = {}

    def configure(self, emulator: Emulator) -> None:
        super().configure(emulator)

    def render(self, emulator: Emulator) -> None:
        super().render(emulator)

    def createAutonomousSystem(self, asn: int) -> ScionAutonomousSystem:
        """!
        @copydoc Base.createAutonomousSystem()
        """
        as_ = ScionAutonomousSystem(asn)
        super().setAutonomousSystem(as_)
        return as_

    def setAutonomousSystem(self, asObject: ScionAutonomousSystem):
        """!
        @copydoc Base.setAutonomousSystem()
        """
        assert issubclass(asObject.__class__, ScionAutonomousSystem), "AS must be derived from ScionAutonomousSystem"
        super().setAutonomousSystem(asObject)

    def createIsolationDomain(self, isd: int, label: Optional[str] = None) -> IsolationDomain:
        """!
        @brief Create a new insolation domain.

        @param isd ISD ID.
        @param label Descriptive name for the ISD.
        @throws AssertionError if ISD already exists.
        @returns Created isolation domain.
        """
        assert isd not in self.__isds
        self.__isds[isd] = IsolationDomain(isd, label)
        return self.__isds[isd]

    def getIsolationDomains(self, isd: int) -> IsolationDomain:
        """!
        @brief Retrieve an IsolationDomain.
        @param isd ID os the isolation domain.
        @throws AssertionError if isd does not exist.
        @returns IsolationDomain.
        """
        assert isd in self.__isds, "isd{} does not exist.".format(isd)
        return self.__isds[isd]

    def getIsolationDomains(self) -> List[int]:
        """!
        @brief Get a list of all ISD IDs.

        @returns List of ISD IDs.
        """
        return list(self.__isds.keys())
    
    def _doCreateGraphs(self, emulator: Emulator):
        super()._doCreateGraphs(emulator)

    def print(self, indent: int) -> str:
        out = super().print(indent)

        indent += 4
        out += ' ' * indent
        out += 'IsolationDomains:\n'
        for isd in self.__isds.values():
            out += isd.print(indent + 4)

        return out

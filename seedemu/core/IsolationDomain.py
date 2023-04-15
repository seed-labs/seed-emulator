from __future__ import annotations
from typing import Optional

from .Printable import Printable


class IsolationDomain(Printable):
    """!
    @brief SCION isolation domain.
    """

    __id: int
    __label: Optional[str]

    def __init__(self, id: int, label: Optional[str]):
        self.__id = id
        self.__label = label

    def getId(self) -> int:
        """!
        @brief Get the unique numerical identifier of the ISD.
        """
        return self.__id

    def getLabel(self) -> Optional[str]:
        """!
        @brief Get the optional human-readable ISD label.
        """
        return self.__label

    def setLabel(self, label: str) -> IsolationDomain:
        """!
        @brief Set a human-readable label or name for the ISD.

        @param label New label to set.
        @returns self, for chaining API calls.
        """
        self.__label = label
        return self

    def print(self, indent: int) -> str:
        return "{}ISD {} (label: {})".format(
            " " * indent, self.__id, self.__label)

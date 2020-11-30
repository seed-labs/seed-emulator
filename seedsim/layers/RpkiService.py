from __future__ import annotations
from .Service import Server, Service
from typing import List

class RpkiServer(Server):
    """!
    @brief RPKI server.
    """

    def newChild(self, handle: str, delegations: List[str]) -> RpkiServer:
        """!
        @brief Create a new child.

        @param handle Child handle.
        @param delegations IPv4 prefixes to delegate to the child.

        @returns child server.

        @throws AssertionError if child handle exists.
        """

    def hadChild(self, handle: str) -> bool:
        """!
        @brief Tesi if child exists.

        @param handle Child handle.

        @returns True if exist, False otherwise.
        """

    def getChild(self, handle: str) -> RpkiServer:
        """!
        @brief Get a child.

        @param handle Child handle.

        @returns child server.
        
        @throws AssertionError if child handle does not exist.
        """
        pass

    def addRoa(self, prefix: str, asn: int, maxLength: int):
        """!
        @brief Add new ROA (route origin authorization).

        @param prefix prefix.
        @param asn asn.
        @param maxLength max prefix length.
        """
        pass

    def hostTa(self):
        """!
        @brief Host TA (trust anchor) on this node.
        """
        pass

class RpkiService(Service):
    """!
    @brief RPKI service.
    """


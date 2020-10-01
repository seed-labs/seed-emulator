from .Service import Service, Server
from seedsim.core import Node
from typing import List

class Zone:
    """!
    @brief Domain name.
    """
    def addRecord(self, record: str):
        pass

class DomainNameServer(Server):
    """!
    @brief The domain name server.
    """

class DomainNameService(Service):
    """!
    @brief The domain name service.
    """

    def getZone(self, domain: str) -> Zone:
        """!
        @brief Get a zone, create it if not exist.

        This method only create the zone. Host it with hostZoneOn.

        @param domain zone name.

        @returns zone handler.
        """
        pass

    def hostZoneOn(self, domain: str, node: Node):
        """!
        @brief Host a zone on the given node.

        Zone must be created with getZone first.

        @param domain zone name.
        @param node target node.
        """
        pass

    def autoNameServer(self):
        """!
        @brief Try to automatically add NS records of children to parent zones.
        """
        pass


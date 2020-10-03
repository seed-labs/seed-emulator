from .Service import Service, Server
from seedsim.core import Node, Printable
from typing import List, Dict
from __future__ import annotations
from re import sub

class Zone(Printable):
    """!
    @brief Domain name zone.
    """
    __zonename: str
    __subzones: Dict[str, Zone]
    __records: List[str]

    def __init__(self, name: str):
        """!
        @brief Zone constructor.
        
        @param name full zonename.
        """
        self.__zonename = name
        self.__subzones = {}
        self.__records = []

    def getName(self) -> str:
        """!
        @brief Get zonename.

        @returns zonename.
        """
        return self.__zonename

    def getSubZone(self, name: str) -> Zone:
        """!
        @brief Get a subzone, if not exists, a new one will be created.

        @param name partial zonename. For example, if current zone is "com.", to
        get "example.com.", use getSubZone("example")

        @returns zone.
        @throws AssertionError if invalid zonename.
        """
        assert '.' not in name, 'invalid subzone name "{}"'.format(name)
        if name in self.__subzones: return self.__subzones[name]
        self.__subzones[name] = Zone('{}.{}'.format(name, self.__zonename))
        return self.__subzones[name]
    
    def getSubZones(self) -> Dict[str, Zone]:
        """!
        @brief Get all subzones.

        @return subzones dict.
        """
        return self.__subzones

    def addRecord(self, record: str):
        """!
        @brief Add a new record to zone.
        """
        self.__records.append(record)

    def getRecords(self) -> List[str]:
        """!
        @brief Get all records.

        @return list of records.
        """
        return self.__records

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'Zone "{}":\n'.format(self.__zonename)

        indent += 4
        out += ' ' * indent
        out += 'Records:\n'

        indent += 4
        for record in self.__records:
            out += ' ' * indent
            out += '{}\n'.format(record)

        indent -= 4
        out += ' ' * indent
        out += 'Subzones:\n'
        
        indent += 4
        for subzone in self.__subzones:
            out += subzone.print(indent)

        return out

class DomainNameServer(Server):
    """!
    @brief The domain name server.
    """

class DomainNameService(Service):
    """!
    @brief The domain name service.
    """

    __rootZone: Zone = Zone('.') # singleton

    def getZone(self, domain: str) -> Zone:
        """!
        @brief Get a zone, create it if not exist.

        This method only create the zone. Host it with hostZoneOn.

        @param domain zone name.

        @returns zone handler.
        """
        path: List[str] = domain.sub(r'\.$', '', domain).split('.')
        path.reverse()
        zoneptr = self.__rootZone
        for z in path:
            zoneptr = zoneptr.getSubZone(z)

        return zoneptr

    def getRootZone(self) -> Zone:
        """!
        @brief Get the root zone.

        @return root zone.
        """
        return self.__rootZone

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

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'DomainNameService:\n'

        indent += 4
        out += self.__rootZone.print(indent)

        return out
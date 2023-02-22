from __future__ import annotations
import base64
import os
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .AutonomousSystem import AutonomousSystem
from .Emulator import Emulator
from .enums import NodeRole
from .Node import Node, ScionRouter


class ScionAutonomousSystem(AutonomousSystem):
    """!
    @brief SCION-enabled AutonomousSystem.

    This class represents an autonomous system with support for SCION.
    """

    __keys: Optional[Tuple[str, str]]
    __attributes: Dict[str, Any]
    __mtu: Optional[int]
    __control_services: Dict[str, Node]

    # Next IFID assigned to a link
    __next_ifid: int

    def __init__(self, asn: int, subnetTemplate: str = "10.{}.0.0/16"):
        """!
        @copydoc AutonomousSystem
        """
        super().__init__(asn, subnetTemplate)
        self.__control_services = {}
        self.__keys = None
        self.__attributes = {}
        self.__mtu = None
        self.__next_ifid = 1

    def registerNodes(self, emulator: Emulator):
        """!
        @copydoc AutonomousSystem.registerNodes()
        """
        super().registerNodes(emulator)
        reg = emulator.getRegistry()
        asn = str(self.getAsn())
        for (key, val) in self.__control_services.items(): reg.register(asn, 'csnode', key, val)

    def configure(self, emulator: Emulator):
        """!
        @copydoc AutonomousSystem.configure()
        """
        super().configure(emulator)

        for cs in self.__control_services.values():
            if len(cs.getNameServers()) == 0:
                cs.setNameServers(self.getNameServers())
            cs.configure(emulator)

        # Set MTU to the smallest MTU of all AS-internal networks
        reg = emulator.getRegistry()
        self.__mtu = min(net.getMtu() for net in reg.getByType(str(self.getAsn()), 'net'))

        # Create secret keys
        self.__keys = (
            base64.b64encode(os.urandom(16)).decode(),
            base64.b64encode(os.urandom(16)).decode())

    def getNextIfid(self) -> int:
        """!
        @brief Get next unused IFID. Called during configuration.
        """
        ifid = self.__next_ifid
        self.__next_ifid += 1
        return ifid

    def getSecretKeys(self) -> Tuple[str, str]:
        """!
        @brief Get AS secret keys.
        """
        assert self.__keys is not None, "AS is not configured yet"
        return self.__keys

    # TODO(lschulz): Rework how these attributes work
    def setAsAttribute(self, attribute: str, value: Any) -> ScionAutonomousSystem:
        """!
        @brief Set an AS attribute. Called during configuration.

        @param attribute Name of the attribute to set/change
        @param value New value. Must be serializable to JSON.
        @returns self
        """
        self.__attributes[attribute] = value
        return self

    def setAsAttributes(self, attributes: Mapping[str, Any]) -> ScionAutonomousSystem:
        """!
        @brief Set an AS attributes. Called during configuration.

        @param attributes
        @returns self
        """
        self.__attributes.update(attributes)

    def getAsAttributes(self) -> Dict[str, Any]:
        """!
        @brief Return a dictionary of all attributes.
        """
        return self.__attributes

    def getTopology(self, isd: int) -> Dict:
        """!
        @brief Create the AS topology definition.

        Called during rendering.

        @param isd is the AS's ISD
        @return Topology dictionary (can be serialized to "topology.json")
        """
        # Control service
        control_services = {}
        for name, cs in self.__control_services.items():
            ifaces = cs.getInterfaces()
            if len(ifaces) > 0:
                cs_addr = f"{ifaces[0].getAddress()}:30252"
                control_services[name] = { 'addr': cs_addr }

        # Border routers
        border_routers = {}
        for router in self.getRouters():
            rnode: ScionRouter = self.getRouter(router)

            border_routers[rnode.getName()] = {
                "internal_addr": f"{rnode.getLoopbackAddress()}:30042",
                "interfaces": rnode.getScionInterfaces()
            }

        return {
            'attributes': [attr for attr, is_set in self.__attributes.items() if is_set],
            'isd_as': f'{isd}-{self.getAsn()}',
            'mtu': self.__mtu,
            'control_service': control_services,
            'discovery_service': control_services,
            'border_routers': border_routers,
            'colibri_service': {},
        }

    def createControlService(self, name: str) -> Node:
        """!
        @brief Create a SCION control service node.

        @param name name of the new node.
        @returns Node.
        """
        assert name not in self.__control_services, 'Control service with name {} already exists.'.format(name)
        self.__control_services[name] = Node(name, NodeRole.Host, self.getAsn())

        return self.__control_services[name]

    def getControlServices(self) -> List[str]:
        """!
        @brief Get list of names of SCION control services.

        @returns list of routers.
        """
        return list(self.__control_services.keys())

    def getControlService(self, name: str) -> Node:
        """!
        @brief Retrieve a control service node.

        @param name name of the node.
        @returns Node.
        """
        return self.__control_services[name]

    def print(self, indent: int) -> str:
        """!
        @copydoc AutonomousSystem.print()
        """
        out = super.print(indent)

        out += ' ' * indent
        out += 'SCION Control Services:\n'

        for node in self.__control_services.values():
            out += node.print(indent + 4)

        return out

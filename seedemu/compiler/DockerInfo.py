from seedemu.core import Registry, Compiler
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NodeRole
import os
from re import sub
import json
import math

class DockerInfo(Compiler):
    __naming_scheme: str
    __network: str
    def __init__(self, network="net-wireless"):
        self.__naming_scheme = "as{asn}{role}-{displayName}-{primaryIp}"
        self.__network = network

    def getName(self) -> str:
        return "DockerInfo"

    def _contextToPrefix(self, scope: str, type: str) -> str:
        """!
        @brief Convert context to prefix.

        @param scope scope.
        @param type type.

        @returns prefix string.
        """
        return '{}_{}_'.format(type, scope)
    
    def _nodeRoleToString(self, role: NodeRole):
        """!
        @brief convert node role to prefix string

        @param role node role

        @returns prefix string
        """
        if role == NodeRole.Host: return 'h'
        if role == NodeRole.Router: return 'r'
        if role == NodeRole.RouteServer: return 'rs'
        assert False, 'unknown node role {}'.format(role)

    def _get_dist(self, node1, node2):
        x1, y1 = node1
        x2, y2 = node2
        dist = math.sqrt( (x2 - x1)**2 + (y2 - y1)**2 )
        return dist

    def _doCompile(self, emulator:Emulator):
        registry = emulator.getRegistry()
        node_info = {
            "node_count" : 0
        }
        nodes = []

        for ((scope, type, name), obj) in registry.getAll().items():
            if type in ['rnode', 'hnode']:
                print(type)
                node = obj
                name = self.__naming_scheme.format(
                    asn = node.getAsn(),
                    role = self._nodeRoleToString(node.getRole()),
                    name = node.getName(),
                    displayName = node.getDisplayName() if node.getDisplayName() != None else node.getName(),
                    primaryIp = node.getInterfaces()[0].getAddress()
                )

                name = sub(r'[^a-zA-Z0-9_.-]', '_', name)

                (scope, type, _) = node.getRegistryInfo()
                prefix = self._contextToPrefix(scope, type)

                for iface in node.getInterfaces():
                    net = iface.getNet()
                    address = iface.getAddress()
                    if net.getName().startswith(self.__network):
                        nodes.append({"id": int(str(address).split(".")[-1])-100,
                                      "container_id": name,
                            "ipaddress": str(address),
                                        "x":0,
                                        "y":0,
                                        "dist":{},
                                        "loss": {}})

        for i in range(len(nodes)):
            nodes[i]["x"] = int(i%6) * 100
            nodes[i]["y"] = int(i//6) * 100

        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                nodes[i]["dist"][j] = self._get_dist((nodes[i]["x"],nodes[i]["y"]), (nodes[j]["x"], nodes[j]["y"]))
                nodes[i]["loss"][j] = 0
                
        node_info['node_count'] = len(nodes)
        node_info['node_info'] = nodes
        json_object = json.dumps(node_info, indent=4)

        print(json_object, file=open('node_pos.json', 'w'))
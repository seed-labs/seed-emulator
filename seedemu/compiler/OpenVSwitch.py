from seedemu.core import Registry, Compiler
from seedemu.core.Emulator import Emulator
from seedemu.core.enums import NodeRole
import os
from re import sub
import json
import math

OVS_CMD = '''\
#!/bin/bash

{add_switch}

{add_port}

sudo ovs-ofctl del-flows sdn0

{if_setup}
'''

OVS_ADD_SWITCH='''\
sudo ovs-vsctl add-br {switch_name}
sudo ifconfig {switch_name} {ip} netmask 255.255.255.0 up
'''

OVS_ADD_PORT='''\
sudo ovs-docker add-port {switch_name} eth1 {node_name} --ipaddress={ip}
'''

DOCKER_EXEC_INTERFACE_SETUP='''\
docker exec {node_name} /tc_init
'''

class OpenVSwitch(Compiler):
    __naming_scheme: str
    def __init__(self):
        self.__naming_scheme = "as{asn}{role}-{displayName}-{primaryIp}"

    def getName(self) -> str:
        return "OpenVSwitch"

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
        scopes = []
        add_port = ""
        if_setup = ""
        node_info = {
            "node_count" : 0
        }
        nodes = []

        for ((scope, type, name), obj) in registry.getAll().items():
            if type in ['rnode', 'hnode']:
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
                    if net.getName().startswith('sdn'):
                        scopes.append(str(address).split('.')[2])
                        add_port += OVS_ADD_PORT.format(switch_name='sdn'+str(address).split('.')[2],
                                            node_name=name,
                                            ip=str(address)+"/24")
                        if_setup += DOCKER_EXEC_INTERFACE_SETUP.format(
                            node_name=name
                        )
                        nodes.append({"id": int(str(address).split(".")[-1]),
                            "ipaddress": str(address),
                                        "x":0,
                                        "y":0,
                                        "dist":{}})
                        
        scopes = list(set(scopes))
        add_switch = ""
        for asn in scopes:
            add_switch += OVS_ADD_SWITCH.format(
                switch_name = 'sdn'+asn,
                ip = "10.0.0.254"
                # ip = "192.168.{asn}.254".format(asn = asn)
            )

        print(OVS_CMD.format(
            add_switch = add_switch, 
            add_port=add_port,
            if_setup=if_setup
        ), file=open('ovs-command', 'w'))

        os.system('chmod +x ovs-command')

        for i in range(len(nodes)):
            nodes[i]["x"] = int(i%10+1) * 100
            nodes[i]["y"] = int(i//10+1) * 100

        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                nodes[i]["dist"][j+1] = self._get_dist((nodes[i]["x"],nodes[i]["y"]), (nodes[j]["x"], nodes[j]["y"]))
                
        node_info['node_count'] = len(nodes)
        node_info['node_info'] = nodes
        json_object = json.dumps(node_info, indent=4)

        print(json_object, file=open('node_pos.json', 'w'))
from seedsim.core import Registry, Node, Network
from .Compiler import Compiler
from typing import Dict

DockerCompilerFileTemplates: Dict[str, str] = {}

DockerCompilerFileTemplates['dockerfile'] = """\
FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
"""

DockerCompilerFileTemplates['compose'] = """\
version: "3"
services:
{services}
networks:
{networks}
"""

DockerCompilerFileTemplates['compose_service'] = """\
    {nodeId}:
        build: ./{nodeId}
        cap_add:
            - ALL
        sysctls:
            - net.ipv4.ip_forward=1
        networks:
{networks}
"""

DockerCompilerFileTemplates['compose_service_network'] = """\
            {netId}:
                {address}
"""

DockerCompilerFileTemplates['compose_network'] = """\
    {netId}:
        ipam:
            config:
                - subnet: {prefix}
"""

class Docker(Compiler):
    """!
    @brief The Docker compiler class.

    Docker is one of the compiler driver. It compiles the lab to docker
    containers.
    """

    __services: str
    __networks: str

    def __init__(self):
        """!
        @brief Docker compiler constructor.
        """
        self.__networks = ""
        self.__services = ""

    def getName(self) -> str:
        return "Docker"

    def __contextToPrefix(self, scope: str, type: str) -> str:
        """!
        @brief Convert context to prefix.

        @param scope scope.
        @param type type.

        @returns prefix string.
        """
        return '{}_{}_'.format(type, scope)

    def __compileNode(self, node: Node):
        """!
        @brief Compile a single node.

        @param node node to compile.
        """
        (scope, type, _) = node.getRegistryInfo()
        prefix = self.__contextToPrefix(scope, type)
        real_nodename = '{}{}'.format(prefix, node.getName())

        node_nets = ''

        for iface in node.getInterfaces():
            net = iface.getNet()
            (netscope, _, _) = net.getRegistryInfo()
            net_prefix = self.__contextToPrefix(netscope, 'net')
            real_netname = '{}{}'.format(net_prefix, net.getName())

            node_nets += DockerCompilerFileTemplates['compose_service_network'].format(
                netId = real_netname,
                address = iface.getAddress()
            )
        
        self._log('!! TODO: make dir for node {}'.format(real_nodename))

        self.__services += DockerCompilerFileTemplates['compose_service'].format(
            nodeId = real_nodename,
            networks = node_nets
        )

    def __compileNet(self, net: Network):
        (scope, _, _) = net.getRegistryInfo()
        self.__networks += DockerCompilerFileTemplates['compose_network'].format(
            netId = '{}{}'.format(self.__contextToPrefix(scope, 'net'), net.getName()),
            prefix = net.getPrefix()
        )

    def _doCompile(self, registry: Registry):
        for ((scope, type, name), obj) in registry.getAll().items():

            if type == 'rnode':
                self._log('!! TODO: compiling router node {} for as{}'.format(name, scope))
                self.__compileNode(obj)

            if type == 'hnode':
                self._log('!! TODO: compiling host node {} for as{}'.format(name, scope))
                self.__compileNode(obj)

            if type == 'rs':
                self._log('!! TODO: compiling rs node for {}'.format(name))
                self.__compileNode(obj)

            if type == 'net':
                self._log('!! TODO: creating network: {}/{}'.format(scope, name))
                self.__compileNet(obj)

        print(DockerCompilerFileTemplates['compose'].format(
            services = self.__services,
            networks = self.__networks
        ), file=open('docker-compose.yml', 'w'))

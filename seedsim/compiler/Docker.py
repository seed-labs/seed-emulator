from seedsim.core import Registry, Node, Network
from .Compiler import Compiler
from typing import Dict
from hashlib import md5
from os import mkdir, chdir

DockerCompilerFileTemplates: Dict[str, str] = {}

DockerCompilerFileTemplates['dockerfile'] = """\
FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
"""

DockerCompilerFileTemplates['start_script'] = """\
#!/bin/bash
{startCommands}
echo "ready! run 'docker exec -it $HOSTNAME /bin/zsh' to attach to this node" >&2
tail -f /dev/null
"""

DockerCompilerFileTemplates['compose'] = """\
version: "3.4"
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
        privileged: {privileged}
        networks:
{networks}{ports}
"""
DockerCompilerFileTemplates['compose_ports'] = """\
        ports:
{portList}
"""

DockerCompilerFileTemplates['compose_port'] = """\
            - {hostPort}:{nodePort}/{proto}
"""

DockerCompilerFileTemplates['compose_service_network'] = """\
            {netId}:
                ipv4_address: {address}
"""

DockerCompilerFileTemplates['compose_network'] = """\
    {netId}:
        driver_opts:
            com.docker.network.driver.mtu: {mtu}
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

    def __addFile(self, path: str, content: str) -> str:
        """!
        @brief Stage file to local folder and return Dockerfile command.

        @param path path to file. (in container)
        @param content content of the file.
        """

        staged_path = md5(path.encode('utf-8')).hexdigest()
        print(content, file=open(staged_path, 'w'))
        return 'COPY {} {}\n'.format(staged_path, path)

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
        
        _ports = node.getPorts()
        ports = ''
        if len(_ports) > 0:
            lst = ''
            for (h, n, p) in _ports:
                lst += DockerCompilerFileTemplates['compose_port'].format(
                    hostPort = h,
                    nodePort = n,
                    proto = p
                )
            ports = DockerCompilerFileTemplates['compose_ports'].format(
                portList = lst
            )
        
        self.__services += DockerCompilerFileTemplates['compose_service'].format(
            nodeId = real_nodename,
            networks = node_nets,
            privileged = 'true' if node.isPrivileged() else 'false',
            ports = ports
        )

        dockerfile = DockerCompilerFileTemplates['dockerfile']
        mkdir(real_nodename)
        chdir(real_nodename)

        commsoft = node.getCommonSoftware()
        if len(commsoft) > 0: dockerfile += 'RUN apt-get install -y --no-install-recommends {}\n'.format(' '.join(sorted(commsoft)))

        soft = node.getSoftwares()
        if len(soft) > 0: dockerfile += 'RUN apt-get install -y --no-install-recommends {}\n'.format(' '.join(sorted(soft)))

        for cmd in node.getBuildCommands(): dockerfile += 'RUN {}\n'.format(cmd)

        start_commands = ''
        for (cmd, fork) in node.getStartCommands():
            start_commands += '{}{}\n'.format(cmd, ' &' if fork else '')

        dockerfile += self.__addFile('/start.sh', DockerCompilerFileTemplates['start_script'].format(
            startCommands = start_commands
        ))

        dockerfile += 'RUN chmod +x /start.sh\n'

        for file in node.getFiles():
            (path, content) = file.get()
            dockerfile += self.__addFile(path, content)

        dockerfile += 'CMD ["/start.sh"]\n'
        print(dockerfile, file=open('Dockerfile', 'w'))

        chdir('..')

    def __compileNet(self, net: Network):
        (scope, _, _) = net.getRegistryInfo()
        self.__networks += DockerCompilerFileTemplates['compose_network'].format(
            netId = '{}{}'.format(self.__contextToPrefix(scope, 'net'), net.getName()),
            prefix = net.getPrefix(),
            mtu = net.getMtu()
        )

    def _doCompile(self, registry: Registry):
        for ((scope, type, name), obj) in registry.getAll().items():

            if type == 'rnode':
                self._log('compiling router node {} for as{}...'.format(name, scope))
                self.__compileNode(obj)

            if type == 'hnode':
                self._log('compiling host node {} for as{}...'.format(name, scope))
                self.__compileNode(obj)

            if type == 'rs':
                self._log('compiling rs node for {}...'.format(name))
                self.__compileNode(obj)

            if type == 'snode':
                self._log('compiling service node {}...'.format(name))
                self.__compileNode(obj)

            if type == 'net':
                self._log('creating network: {}/{}...'.format(scope, name))
                self.__compileNet(obj)

        self._log('creating docker-compose.yml...'.format(scope, name))
        print(DockerCompilerFileTemplates['compose'].format(
            services = self.__services,
            networks = self.__networks
        ), file=open('docker-compose.yml', 'w'))

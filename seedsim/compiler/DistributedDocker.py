from seedsim.core import Registry, ScopedRegistry, Node, Network
from .Compiler import Compiler
from typing import Dict
from hashlib import md5
from os import mkdir, chdir, rmdir

DistributedDockerCompilerFileTemplates: Dict[str, str] = {}

DistributedDockerCompilerFileTemplates['dockerfile'] = """\
FROM ubuntu:20.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update
RUN apt-get install -y zsh curl
RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc
RUN echo 'exec zsh' > /root/.bashrc
"""

DistributedDockerCompilerFileTemplates['start_script'] = """\
#!/bin/bash
{startCommands}
echo "ready! run 'docker exec -it $HOSTNAME /bin/zsh' to attach to this node" >&2
tail -f /dev/null
"""

DistributedDockerCompilerFileTemplates['compose'] = """\
version: "3.4"
services:
{services}
networks:
{networks}
"""

DistributedDockerCompilerFileTemplates['compose_service'] = """\
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
DistributedDockerCompilerFileTemplates['compose_ports'] = """\
        ports:
{portList}
"""

DistributedDockerCompilerFileTemplates['compose_port'] = """\
            - {hostPort}:{nodePort}/{proto}
"""

DistributedDockerCompilerFileTemplates['compose_service_network'] = """\
            {netId}:
                ipv4_address: {address}
"""

DistributedDockerCompilerFileTemplates['compose_network'] = """\
    {netId}:
        driver_opts:
            com.docker.network.driver.mtu: {mtu}
        ipam:
            config:
                - subnet: {prefix}
"""

DistributedDockerCompilerFileTemplates['compose_network_ix_worker'] = """\
    {netId}:
        external:
            name: sim_ix_{netId}
        driver: overlay
"""

DistributedDockerCompilerFileTemplates['compose_network_ix_master'] = """\
    {netId}:
        driver: overlay
        ipam:
            config:
                - subnet: {prefix}
"""

class DistributedDocker(Compiler):
    """!
    @brief The DistributedDocker compiler class.

    DistributedDocker is one of the compiler driver. It compiles the lab to
    docker containers. This compiler will generate one set of containers with
    their docker-compose.yml for each AS, enable you to run the simulator
    distributed. 

    This works by making every IX network overlay network. 
    """

    def __init__(self):
        """!
        @brief DistributedDocker compiler constructor.
        """

    def getName(self) -> str:
        return "DistributedDocker"

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

    def __compileNode(self, node: Node) -> str:
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

            node_nets += DistributedDockerCompilerFileTemplates['compose_service_network'].format(
                netId = real_netname,
                address = iface.getAddress()
            )
        
        _ports = node.getPorts()
        ports = ''
        if len(_ports) > 0:
            lst = ''
            for (h, n, p) in _ports:
                lst += DistributedDockerCompilerFileTemplates['compose_port'].format(
                    hostPort = h,
                    nodePort = n,
                    proto = p
                )
            ports = DistributedDockerCompilerFileTemplates['compose_ports'].format(
                portList = lst
            )
        
        dockerfile = DistributedDockerCompilerFileTemplates['dockerfile']
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

        dockerfile += self.__addFile('/start.sh', DistributedDockerCompilerFileTemplates['start_script'].format(
            startCommands = start_commands
        ))

        dockerfile += 'RUN chmod +x /start.sh\n'

        for file in node.getFiles():
            (path, content) = file.get()
            dockerfile += self.__addFile(path, content)

        dockerfile += 'CMD ["/start.sh"]\n'
        print(dockerfile, file=open('Dockerfile', 'w'))

        chdir('..')

        return DistributedDockerCompilerFileTemplates['compose_service'].format(
            nodeId = real_nodename,
            networks = node_nets,
            privileged = 'true' if node.isPrivileged() else 'false',
            ports = ports
        )

    def __compileNet(self, net: Network) -> str:
        (scope, _, _) = net.getRegistryInfo()
        return DistributedDockerCompilerFileTemplates['compose_network'].format(
            netId = '{}{}'.format(self.__contextToPrefix(scope, 'net'), net.getName()),
            prefix = net.getPrefix(),
            mtu = net.getMtu()
        )

    def __compileIxNetMaster(self, net) -> str:
        (scope, _, _) = net.getRegistryInfo()
        return DistributedDockerCompilerFileTemplates['compose_network_ix_master'].format(
            netId = '{}{}'.format(self.__contextToPrefix(scope, 'net'), net.getName()),
            prefix = net.getPrefix()
        )

    def __compileIxNetWorker(self, net) -> str:
        (scope, _, _) = net.getRegistryInfo()
        return DistributedDockerCompilerFileTemplates['compose_network_ix_worker'].format(
            netId = '{}{}'.format(self.__contextToPrefix(scope, 'net'), net.getName())
        )

    def _doCompile(self):
        registry = Registry()
        scopes = set()
        for (scope, _, _) in registry.getAll().keys(): scopes.add(scope)

        ix_nets = ''

        for ixnet in ScopedRegistry('ix').getByType('net'):
            ix_nets += self.__compileIxNetWorker(ixnet)

        for scope in scopes:
            mkdir(scope)
            chdir(scope)

            services = ''
            networks = ''

            for ((_scope, type, name), obj) in registry.getAll().items():
                if _scope != scope: continue

                if type == 'rnode':
                    self._log('compiling router node {} for as{}...'.format(name, scope))
                    services += self.__compileNode(obj)

                if type == 'hnode':
                    self._log('compiling host node {} for as{}...'.format(name, scope))
                    services += self.__compileNode(obj)

                if type == 'rs':
                    self._log('compiling rs node for {}...'.format(name))
                    services += self.__compileNode(obj)

                if type == 'snode':
                    self._log('compiling service node {}...'.format(name))
                    services += self.__compileNode(obj)

                if type == 'net':
                    self._log('creating network: {}/{}...'.format(scope, name))
                    networks += self.__compileIxNetMaster(obj) if scope == 'ix' else self.__compileNet(obj)

            if len(services) > 0 or len(networks) > 0 :
                if scope != 'ix': networks += ix_nets
                self._log('creating docker-compose.yml...'.format(scope, name))
                print(DistributedDockerCompilerFileTemplates['compose'].format(
                    services = services,
                    networks = networks
                ), file=open('docker-compose.yml', 'w'))

                print('COMPOSE_PROJECT_NAME=sim_{}'.format(scope), file=open('.env', 'w'))

            chdir('..')

            if services == '' and networks == '': rmdir(scope)

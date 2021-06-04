from seedemu.core.Emulator import Emulator
from seedemu.core import Node, Network
from seedemu.core.enums import NodeRole, NetworkType
from .Compiler import Compiler
from typing import Dict, Generator
from hashlib import md5
from os import mkdir, chdir
from ipaddress import IPv4Network, IPv4Address

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

DockerCompilerFileTemplates['seedemu_sniffer'] = """\
#!/bin/bash
last_pid=0
while read -r expr; do {
    [ "$last_pid" != 0 ] && kill $last_pid 2> /dev/null
    [ -z "$expr" ] && continue
    tcpdump -e -i any -nn -p -q "$expr" &
    last_pid=$!
}; done
[ "$last_pid" != 0 ] && kill $last_pid
"""

DockerCompilerFileTemplates['replace_address_script'] = '''\
#!/bin/bash
ip -j addr | jq -cr '.[]' | while read -r iface; do {
    ifname="`jq -cr '.ifname' <<< "$iface"`"
    jq -cr '.addr_info[]' <<< "$iface" | while read -r iaddr; do {
        addr="`jq -cr '"\(.local)/\(.prefixlen)"' <<< "$iaddr"`"
        line="`grep "$addr" < /dummy_addr_map.txt`"
        [ -z "$line" ] && continue
        new_addr="`cut -d, -f2 <<< "$line"`"
        ip addr del "$addr" dev "$ifname"
        ip addr add "$new_addr" dev "$ifname"
    }; done
}; done
for f in /proc/sys/net/ipv4/conf/*/rp_filter; do echo 0 > "$f"; done
'''

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
        container_name: {nodeName}
        cap_add:
            - ALL
        sysctls:
            - net.ipv4.ip_forward=1
            - net.ipv4.conf.default.rp_filter=0
            - net.ipv4.conf.all.rp_filter=0
        privileged: true
        networks:
{networks}{ports}
        labels:
{labelList}
"""

DockerCompilerFileTemplates['compose_label_meta'] = """\
            org.seedsecuritylabs.seedemu.meta.{key}: "{value}"
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
        labels:
{labelList}
"""

class Docker(Compiler):
    """!
    @brief The Docker compiler class.

    Docker is one of the compiler driver. It compiles the lab to docker
    containers.
    """

    __services: str
    __networks: str
    __naming_scheme: str
    __self_managed_network: bool
    __dummy_network_pool: Generator[IPv4Network, None, None]

    def __init__(
        self,
        namingScheme: str = "as{asn}{role}-{name}-{primaryIp}",
        selfManagedNetwork: bool = False,
        dummyNetworksPool: str = '10.128.0.0/9',
        dummyNetworksMask: int = 24
    ):
        """!
        @brief Docker compiler constructor.

        @param namingScheme (optional) node naming scheme. Avaliable variables
        are: {asn}, {role} (r - router, h - host, rs - route server), {name},
        {primaryIp}
        @param selfManagedNetwork (optional) use self-managed network. Enable
        this to manage the network inside containers instead of using docker's
        network management. This works by first assigning "dummy" prefix and
        address to containers, then replace those address with "real" address
        when the containers start. This will allow the use of overlapping
        networks in the emulation and will allow the use of the ".1" address on
        nodes.
        @param dummyNetworksPool (optional) dummy networks pool. This should not
        overlap with any "real" networks used in the emulation, including
        loopback IP addresses. 
        @param dymmyNetworksMask (optional) mask of dummy networks.
        """
        self.__networks = ""
        self.__services = ""
        self.__naming_scheme = namingScheme
        self.__self_managed_network = selfManagedNetwork
        self.__dummy_network_pool = IPv4Network(dummyNetworksPool).subnets(new_prefix = dummyNetworksMask)

    def getName(self) -> str:
        return "Docker"

    def __getNetMeta(self, net: Network): 
        (scope, type, name) = net.getRegistryInfo()

        labels = ''

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'type',
            value = 'global' if scope == 'ix' else 'local'
        )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'scope',
            value = scope
        )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'name',
            value = name
        )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'prefix',
            value = net.getPrefix()
        )

        return labels

    def __getNodeMeta(self, node: Node):
        (scope, type, name) = node.getRegistryInfo()

        labels = ''

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'asn',
            value = node.getAsn()
        )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key = 'nodename',
            value = name
        )

        if type == 'hnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'Host'
            )

        if type == 'rnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'Router'
            )

        if type == 'snode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'Emulator Service Worker'
            )

        if type == 'rs':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'Route Server'
            )

        n = 0
        for iface in node.getInterfaces():
            net = iface.getNet()

            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'net.{}.name'.format(n),
                value = net.getName()
            )

            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'net.{}.address'.format(n),
                value = '{}/{}'.format(iface.getAddress(), net.getPrefix().prefixlen)
            )

            n += 1

        return labels

    def __nodeRoleToString(self, role: NodeRole):
        if role == NodeRole.Host: return 'h'
        if role == NodeRole.Router: return 'r'
        if role == NodeRole.RouteServer: return 'rs'
        assert False, 'unknow node role {}'.format(role)

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
        dummy_addr_map = ''

        for iface in node.getInterfaces():
            net = iface.getNet()
            (netscope, _, _) = net.getRegistryInfo()
            net_prefix = self.__contextToPrefix(netscope, 'net') 
            if net.getType() == NetworkType.Bridge: net_prefix = ''
            real_netname = '{}{}'.format(net_prefix, net.getName())
            address = iface.getAddress()

            if self.__self_managed_network and net.getType() != NetworkType.Bridge:
                d_index: int = net.getAttribute('dummy_prefix_index')
                d_prefix: IPv4Network = net.getAttribute('dummy_prefix')
                d_address: IPv4Address = d_prefix[d_index]

                net.setAttribute('dummy_prefix_index', d_index + 1)

                dummy_addr_map += '{}/{},{}/{}\n'.format(
                    d_address, d_prefix.prefixlen,
                    iface.getAddress(), iface.getNet().getPrefix().prefixlen
                )

                address = d_address
                
                self._log('using self-managed network: using dummy address {}/{} for {}/{} on as{}/{}'.format(
                    d_address, d_prefix.prefixlen, iface.getAddress(), iface.getNet().getPrefix().prefixlen,
                    node.getAsn(), node.getName()
                ))

            node_nets += DockerCompilerFileTemplates['compose_service_network'].format(
                netId = real_netname,
                address = address
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
            nodeName = self.__naming_scheme.format(
                asn = node.getAsn(),
                role = self.__nodeRoleToString(node.getRole()),
                name = node.getName(),
                primaryIp = node.getInterfaces()[0].getAddress()
            ),
            networks = node_nets,
            # privileged = 'true' if node.isPrivileged() else 'false',
            ports = ports,
            labelList = self.__getNodeMeta(node)
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

        if self.__self_managed_network:
            start_commands += 'chmod +x /replace_address.sh\n'
            start_commands += '/replace_address.sh\n'
            dockerfile += self.__addFile('/replace_address.sh', DockerCompilerFileTemplates['replace_address_script'])
            dockerfile += self.__addFile('/dummy_addr_map.txt', dummy_addr_map)

        for (cmd, fork) in node.getStartCommands():
            start_commands += '{}{}\n'.format(cmd, ' &' if fork else '')

        dockerfile += self.__addFile('/start.sh', DockerCompilerFileTemplates['start_script'].format(
            startCommands = start_commands
        ))

        dockerfile += self.__addFile('/seedemu_sniffer', DockerCompilerFileTemplates['seedemu_sniffer'])

        dockerfile += 'RUN chmod +x /start.sh\n'
        dockerfile += 'RUN chmod +x /seedemu_sniffer\n'

        for file in node.getFiles():
            (path, content) = file.get()
            dockerfile += self.__addFile(path, content)

        dockerfile += 'CMD ["/start.sh"]\n'
        print(dockerfile, file=open('Dockerfile', 'w'))

        chdir('..')

    def __compileNet(self, net: Network):
        (scope, _, _) = net.getRegistryInfo()
        if self.__self_managed_network and net.getType() != NetworkType.Bridge:
            pfx = next(self.__dummy_network_pool)
            net.setAttribute('dummy_prefix', pfx)
            net.setAttribute('dummy_prefix_index', 2)
            self._log('self-managed network: using dummy prefix {}'.format(pfx))

        net_prefix = self.__contextToPrefix(scope, 'net')
        if net.getType() == NetworkType.Bridge: net_prefix = ''

        self.__networks += DockerCompilerFileTemplates['compose_network'].format(
            netId = '{}{}'.format(net_prefix, net.getName()),
            prefix = net.getAttribute('dummy_prefix') if self.__self_managed_network and net.getType() != NetworkType.Bridge else net.getPrefix(),
            mtu = net.getMtu(),
            labelList = self.__getNetMeta(net)
        )

    def _doCompile(self, emulator: Emulator):
        registry = emulator.getRegistry()

        for ((scope, type, name), obj) in registry.getAll().items():

            if type == 'net':
                self._log('creating network: {}/{}...'.format(scope, name))
                self.__compileNet(obj)

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

        self._log('creating docker-compose.yml...'.format(scope, name))
        print(DockerCompilerFileTemplates['compose'].format(
            services = self.__services,
            networks = self.__networks
        ), file=open('docker-compose.yml', 'w'))

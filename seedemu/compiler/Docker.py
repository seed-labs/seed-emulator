from __future__ import annotations
from seedemu.core.Emulator import Emulator
from seedemu.core import Node, Network, Compiler, BaseSystem, BaseOption, Scope, ScopeType, ScopeTier, OptionHandling, BaseVolume, OptionMode
from seedemu.core.enums import NodeRole, NetworkType
from .DockerImage import DockerImage
from .DockerImageConstant import *
from typing import Dict, Generator, List, Set, Tuple
from hashlib import md5
from functools import cmp_to_key
from os import mkdir, chdir
from re import sub
from ipaddress import IPv4Network, IPv4Address
from shutil import copyfile
import json
from yaml import dump

SEEDEMU_INTERNET_MAP_IMAGE='handsonsecurity/seedemu-multiarch-map:buildx-latest'
SEEDEMU_ETHER_VIEW_IMAGE='handsonsecurity/seedemu-multiarch-etherview:buildx-latest'

DockerCompilerFileTemplates: Dict[str, str] = {}

DockerCompilerFileTemplates['dockerfile'] = """\
ARG DEBIAN_FRONTEND=noninteractive
"""
#RUN echo 'exec zsh' > /root/.bashrc

DockerCompilerFileTemplates['start_script'] = """\
#!/bin/bash
{startCommands}
echo "ready! run 'docker exec -it $HOSTNAME /bin/zsh' to attach to this node" >&2
{buildtime_sysctl}
tail -f /dev/null
"""

DockerCompilerFileTemplates['seedemu_sniffer'] = """\
#!/bin/bash
last_pid=0
while read -sr expr; do {
    [ "$last_pid" != 0 ] && kill $last_pid 2> /dev/null
    [ -z "$expr" ] && continue
    tcpdump -e -i any -nn -p -q "$expr" &
    last_pid=$!
}; done
[ "$last_pid" != 0 ] && kill $last_pid
"""

DockerCompilerFileTemplates['seedemu_worker'] = """\
#!/bin/bash

net() {
    [ "$1" = "status" ] && {
        ip -j link | jq -cr '.[] .operstate' | grep -q UP && echo "up" || echo "down"
        return
    }

    ip -j li | jq -cr '.[] .ifname' | while read -r ifname; do ip link set "$ifname" "$1"; done
}

bgp() {
    cmd="$1"
    peer="$2"
    [ "$cmd" = "bird_peer_down" ] && birdc dis "$2"
    [ "$cmd" = "bird_peer_up" ] && birdc en "$2"
}

while read -sr line; do {
    id="`cut -d ';' -f1 <<< "$line"`"
    cmd="`cut -d ';' -f2 <<< "$line"`"

    output="no such command."

    [ "$cmd" = "net_down" ] && output="`net down 2>&1`"
    [ "$cmd" = "net_up" ] && output="`net up 2>&1`"
    [ "$cmd" = "net_status" ] && output="`net status 2>&1`"
    [ "$cmd" = "bird_list_peer" ] && output="`birdc s p | grep --color=never BGP 2>&1`"

    [[ "$cmd" == "bird_peer_"* ]] && output="`bgp $cmd 2>&1`"

    printf '_BEGIN_RESULT_'
    jq -Mcr --arg id "$id" --arg return_value "$?" --arg output "$output" -n '{id: $id | tonumber, return_value: $return_value | tonumber, output: $output }'
    printf '_END_RESULT_'
}; done
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
'''

DockerCompilerFileTemplates['compose'] = """\
version: "3.4"
services:
{dummies}
{services}
networks:
{networks}
{volumes}
"""

DockerCompilerFileTemplates['compose_dummy'] = """\
    {imageDigest}:
        build:
            context: .
            dockerfile: dummies/{imageDigest}
        image: {imageDigest}
{dependsOn}
"""

DockerCompilerFileTemplates['depends_on'] = """\
        depends_on:
            - {dependsOn}
"""

DockerCompilerFileTemplates['compose_service'] = """\
    {nodeId}:
        build: ./{nodeId}
        container_name: {nodeName}
        depends_on:
            - {dependsOn}
        cap_add:
            - ALL
{sysctls}
        privileged: true
        networks:
{networks}{ports}{volumes}
        labels:
{labelList}
        environment:
        {environment}
"""

DockerCompilerFileTemplates['compose_sysctl'] =  """
        sysctls:

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

DockerCompilerFileTemplates['compose_volumes'] = """\
        volumes:
{volumeList}
"""

DockerCompilerFileTemplates['compose_service_network'] = """\
            {netId}:
{address}
"""

DockerCompilerFileTemplates['compose_service_network_address'] = """\
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

DockerCompilerFileTemplates['seedemu_internet_map'] = """\
    seedemu-internet-client:
        image: {clientImage}
        container_name: seedemu_internet_map
        volumes:
            - /var/run/docker.sock:/var/run/docker.sock
        privileged: true
"""

DockerCompilerFileTemplates['port_forwarding_entry'] = """\
        ports:
            - {port_forwarding_field}
"""

DockerCompilerFileTemplates['environment_variable_entry'] = """\
        environment:
"""

DockerCompilerFileTemplates['network_entry'] = """\
        networks:
             {network_name_field}:
                    {ipv4_address_field}
"""

DockerCompilerFileTemplates['seedemu_ether_view'] = """\
    seedemu-ether-client:
        image: {clientImage}
        container_name: seedemu_ether_view
        volumes:
            - /var/run/docker.sock:/var/run/docker.sock
        ports:
            - {clientPort}:5000/tcp
"""

DockerCompilerFileTemplates['zshrc_pre'] = """\
export NOPRECMD=1
alias st=set_title
"""

DockerCompilerFileTemplates['local_image'] = """\
    {imageName}:
        build:
            context: {dirName}
        image: {imageName}
"""

# class DockerImage(object):
#     """!
#     @brief The DockerImage class.

#     This class represents a candidate image for docker compiler.
#     """

#     __software: Set[str]
#     __name: str
#     __local: bool
#     __dirName: str

#     def __init__(self, name: str, software: List[str], local: bool = False, dirName: str = None) -> None:
#         """!
#         @brief create a new docker image.

#         @param name name of the image. Can be name of a local image, image on
#         dockerhub, or image in private repo.
#         @param software set of software pre-installed in the image, so the
#         docker compiler can skip them when compiling.
#         @param local (optional) set this image as a local image. A local image
#         is built locally instead of pulled from the docker hub. Default to False.
#         @param dirName (optional) directory name of the local image (when local
#         is True). Default to None. None means use the name of the image.
#         """
#         super().__init__()

#         self.__name = name
#         self.__software = set()
#         self.__local = local
#         self.__dirName = dirName if dirName != None else name

#         for soft in software:
#             self.__software.add(soft)

#     def getName(self) -> str:
#         """!
#         @brief get the name of this image.

#         @returns name.
#         """
#         return self.__name

#     def getSoftware(self) -> Set[str]:
#         """!
#         @brief get set of software installed on this image.

#         @return set.
#         """
#         return self.__software
#     def getDirName(self) -> str:
#         """!
#         @brief returns the directory name of this image.
#         @return directory name.
#         """
#         return self.__dirName

#     def isLocal(self) -> bool:
#         """!
#         @brief returns True if this image is local.

#         @return True if this image is local.
#         """
#         return self.__local

#     def addSoftwares(self, software) -> DockerImage:
#         """!
#         @brief add softwares to this image.
#         @return self, for chaining api calls.
#         """
#         for soft in software:
#             self.__software.add(soft)


class Docker(Compiler):
    """!
    @brief The Docker compiler class.

    Docker is one of the compiler driver. It compiles the lab to docker
    containers.
    """

    __services: str
    __custom_services: str

    __networks: str
    __naming_scheme: str
    __self_managed_network: bool
    __dummy_network_pool: Generator[IPv4Network, None, None]


    __internet_map_enabled: bool
    __internet_map_port: int


    __ether_view_enabled: bool
    __ether_view_port: int

    __client_hide_svcnet: bool

    __images: Dict[str, Tuple[DockerImage, int]]
    __forced_image: str
    __disable_images: bool
    __image_per_node_list: Dict[Tuple[str, str], DockerImage]
    _used_images: Set[str]
    __config: List[ Tuple[BaseOption , Scope] ] # all encountered Options for .env file
    __option_handling: OptionHandling # strategy how to deal with Options
    __basesystem_dockerimage_mapping: dict

    def __init__(
        self,
        platform:Platform = Platform.AMD64,
        namingScheme: str = "as{asn}{role}-{displayName}-{primaryIp}",
        selfManagedNetwork: bool = False,
        dummyNetworksPool: str = '10.128.0.0/9',
        dummyNetworksMask: int = 24,
        internetMapEnabled: bool = True,
        internetMapPort: int = 8080,
        etherViewEnabled: bool = False,
        etherViewPort: int = 5000,
        clientHideServiceNet: bool = True,
        option_handling: OptionHandling = OptionHandling.CREATE_SEPARATE_ENV_FILE
    ):
        """!
        @brief Docker compiler constructor.

        @param platform (optional) node cpu architecture Default to Platform.AMD64
        @param namingScheme (optional) node naming scheme. Available variables
        are: {asn}, {role} (r - router, h - host, rs - route server), {name},
        {primaryIp} and {displayName}. {displayName} will automatically fall
        back to {name} if
        Default to as{asn}{role}-{displayName}-{primaryIp}.
        @param selfManagedNetwork (optional) use self-managed network. Enable
        this to manage the network inside containers instead of using docker's
        network management. This works by first assigning "dummy" prefix and
        address to containers, then replace those address with "real" address
        when the containers start. This will allow the use of overlapping
        networks in the emulation and will allow the use of the ".1" address on
        nodes. Note this will break port forwarding (except for service nodes
        like real-world access node and remote access node.) Default to False.
        @param dummyNetworksPool (optional) dummy networks pool. This should not
        overlap with any "real" networks used in the emulation, including
        loopback IP addresses. Default to 10.128.0.0/9.
        @param dummyNetworksMask (optional) mask of dummy networks. Default to
        24.
        @param internetMapEnabled (optional) set if seedemu internetMap should be enabled.
        Default to False. Note that the seedemu internetMap allows unauthenticated
        access to all nodes, which can potentially allow root access to the
        emulator host. Only enable seedemu in a trusted network.
        @param internetMapPort (optional) set seedemu internetMap port. Default to 8080.
        @param etherViewEnabled (optional) set if seedemu EtherView should be enabled.
        Default to False.
        @param etherViewPort (optional) set seedemu EtherView port. Default to 5000.
        @param clientHideServiceNet (optional) hide service network for the
        client map by not adding metadata on the net. Default to True.
        """
        self.__option_handling = option_handling
        self.__networks = ""
        self.__services = ""
        self.__custom_services = ""
        self.__naming_scheme = namingScheme
        self.__self_managed_network = selfManagedNetwork
        self.__dummy_network_pool = IPv4Network(dummyNetworksPool).subnets(new_prefix = dummyNetworksMask)

        self.__internet_map_enabled = internetMapEnabled
        self.__internet_map_port = internetMapPort

        self.__ether_view_enabled = etherViewEnabled
        self.__ether_view_port = etherViewPort

        self.__client_hide_svcnet = clientHideServiceNet

        self.__images = {}
        self.__forced_image = None
        self.__disable_images = False
        self._used_images = set()
        self.__image_per_node_list = {}
        self.__config = [] # variables for '.env' file alongside 'docker-compose.yml'

        self.__volumes_dedup = (
            []
        )  # unforunately set(()) failed to automatically deduplicate
        self.__vol_names = []
        super().__init__()

        self.__platform = platform

        self.__basesystem_dockerimage_mapping = BASESYSTEM_DOCKERIMAGE_MAPPING_PER_PLATFORM[self.__platform]

        for name, image in self.__basesystem_dockerimage_mapping.items():
            priority = 0
            if name == BaseSystem.DEFAULT:
                priority = 1
            self.addImage(image, priority=priority)

    def _addVolume(self, vol: BaseVolume):
        """! @brief add a docker volume/bind mount/or tmpfs

        Remember them for later, to generate the top lvl 'volumes:' section of docker-compose.yml
        """
        # if vol.type() == 'volume': # then it is a named-volume
        key = vol.asDict()["source"]
        if key not in self.__vol_names:
            self.__volumes_dedup.append(vol)
            self.__vol_names.append(key)
        return self

    def _getVolumes(self) -> List[BaseVolume]:
        """! @brief get all docker volumes/mounts that must appear
            in docker-compose.yml top-level  'volumes:' section
        """
        return self.__volumes_dedup

    def optionHandlingCapabilities(self) -> OptionHandling:
        return OptionHandling.DIRECT_DOCKER_COMPOSE | OptionHandling.CREATE_SEPARATE_ENV_FILE

    def getName(self) -> str:
        return "Docker"

    def addImage(self, image: DockerImage, priority: int = -1) -> Docker:
        """!
        @brief add an candidate image to the compiler.

        @param image image to add.
        @param priority (optional) priority of this image. Used when one or more
        images with same number of missing software exist. The one with highest
        priority wins. If two or more images with same priority and same number
        of missing software exist, the one added the last will be used. All
        built-in images has priority of 0. Default to -1. All built-in images are
        prior to the added candidate image. To set a candidate image to a node,
        use setImageOverride() method.

        @returns self, for chaining api calls.
        """
        assert image.getName() not in self.__images, 'image with name {} already exists.'.format(image.getName())

        self.__images[image.getName()] = (image, priority)

        return self

    def getImages(self) -> List[Tuple[DockerImage, int]]:
        """!
        @brief get list of images configured.

        @returns list of tuple of images and priority.
        """

        return list(self.__images.values())

    def forceImage(self, imageName: str) -> Docker:
        """!
        @brief forces the docker compiler to use a image, identified by the
        imageName. Image with such name must be added to the docker compiler
        with the addImage method, or the docker compiler will fail at compile
        time. Set to None to disable the force behavior.

        @param imageName name of the image.

        @returns self, for chaining api calls.
        """
        self.__forced_image = imageName

        return self

    def disableImages(self, disabled: bool = True) -> Docker:
        """!
        @brief forces the docker compiler to not use any images and build
        everything for starch. Set to False to disable the behavior.

        @param disabled (option) disabled image if True. Default to True.

        @returns self, for chaining api calls.
        """
        self.__disable_images = disabled

        return self

    def setImageOverride(self, node:Node, imageName:str) -> Docker:
        """!
        @brief set the docker compiler to use a image on the specified Node.

        @param node target node to override image.
        @param imageName name of the image to use.

        @returns self, for chaining api calls.
        """
        asn = node.getAsn()
        name = node.getName()
        self.__image_per_node_list[(asn, name)]=imageName

    def _groupSoftware(self, emulator: Emulator):
        """!
        @brief Group apt-get install calls to maximize docker cache.

        @param emulator emulator to load nodes from.
        """

        registry = emulator.getRegistry()

        # { [imageName]: { [softName]: [nodeRef] } }
        softGroups: Dict[str, Dict[str, List[Node]]] = {}

        # { [imageName]: useCount }
        groupIter: Dict[str, int] = {}

        for ((scope, type, name), obj) in registry.getAll().items():
            if type not in ['rnode', 'csnode', 'hnode', 'snode', 'rs', 'snode']:
                continue

            node: Node = obj

            (img, _) = self._selectImageFor(node)
            imgName = img.getName()

            if not imgName in groupIter:
                groupIter[imgName] = 0

            groupIter[imgName] += 1

            if not imgName in softGroups:
                softGroups[imgName] = {}

            group = softGroups[imgName]

            for soft in node.getSoftware():
                if soft not in group:
                    group[soft] = []
                group[soft].append(node)

        for (key, val) in softGroups.items():
            maxIter = groupIter[key]
            self._log('grouping software for image "{}" - {} references.'.format(key, maxIter))
            step = 1

            for commRequired in range(maxIter, 0, -1):
                currentTier: Set[str] = set()
                currentTierNodes: Set[Node] = set()

                for (soft, nodes) in val.items():
                    if len(nodes) == commRequired:
                        currentTier.add(soft)
                        for node in nodes: currentTierNodes.add(node)

                for node in currentTierNodes:
                    if not node.hasAttribute('__soft_install_tiers'):
                        node.setAttribute('__soft_install_tiers', [])

                    node.getAttribute('__soft_install_tiers').append(currentTier)


                if len(currentTier) > 0:
                    self._log('the following software has been grouped together in step {}: {} since they are referenced by {} nodes.'.format(step, currentTier, len(currentTierNodes)))
                    step += 1


    def _selectImageFor(self, node: Node) -> Tuple[DockerImage, Set[str]]:
        """!
        @brief select image for the given node.

        @param node node.

        @returns tuple of selected image and set of missing software.
        """
        nodeSoft = node.getSoftware()
        nodeKey = (node.getAsn(), node.getName())

        # #1 Highest Priority (User Custom Image)
        if nodeKey in self.__image_per_node_list:
            image_name = self.__image_per_node_list[nodeKey]

            assert image_name in self.__images, 'image-per-node configured, but image {} does not exist.'.format(image_name)

            (image, _) = self.__images[image_name]

            self._log('image-per-node configured, using {}'.format(image.getName()))
            return (image, nodeSoft - image.getSoftware())

        # Should we keep this feature?
        if self.__disable_images:
            self._log('disable-imaged configured, using base image.')
            (image, _) = self.__images['ubuntu:20.04']
            return (image, nodeSoft - image.getSoftware())

        # Set Default Image for All Nodes
        if self.__forced_image != None:
            assert self.__forced_image in self.__images, 'forced-image configured, but image {} does not exist.'.format(self.__forced_image)

            (image, _) = self.__images[self.__forced_image]

            self._log('force-image configured, using image: {}'.format(image.getName()))

            return (image, nodeSoft - image.getSoftware())

        #Maintain a table : Virtual Image Name - Actual Image Name
        image = self.__basesystem_dockerimage_mapping[node.getBaseSystem()]

        return (image, nodeSoft - image.getSoftware())

        # candidates: List[Tuple[DockerImage, int]] = []
        # minMissing = len(nodeSoft)
        # for (image, prio) in self.__images.values():
        #     missing = len(nodeSoft - image.getSoftware())

        #     if missing < minMissing:
        #         candidates = []
        #         minMissing = missing
        #     if missing <= minMissing:
        #         candidates.append((image, prio))

        # assert len(candidates) > 0, '_electImageFor ended w/ no images?'

        # (selected, maxPrio) = candidates[0]

        # for (candidate, prio) in candidates:
        #     if prio >= maxPrio:
        #         maxPrio = prio
        #         selected = candidate

        # return (selected, nodeSoft - selected.getSoftware())


    def _getNetMeta(self, net: Network) -> str:
        """!
        @brief get net metadata labels.

        @param net net object.

        @returns metadata labels string.
        """

        (scope, type, name) = net.getRegistryInfo()

        labels = ''

        if self.__client_hide_svcnet and scope == 'seedemu' and name == '000_svc':
            return DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'dummy',
                value = 'dummy label for hidden node/net'
            )

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

        if net.getDisplayName() != None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'displayname',
                value = net.getDisplayName()
            )

        if net.getDescription() != None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'description',
                value = net.getDescription()
            )

        return labels

    def _getNodeMeta(self, node: Node) -> str:
        """!
        @brief get node metadata labels.

        @param node node object.

        @returns metadata labels string.
        """
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
        if type == 'brdnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'BorderRouter'
            )

        if type == 'csnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'role',
                value = 'SCION Control Service'
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

        if node.getDisplayName() != None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'displayname',
                value = node.getDisplayName()
            )

        if node.getDescription() != None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'description',
                value = node.getDescription()
            )

        if len(node.getClasses()) > 0:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = 'class',
                value = json.dumps(node.getClasses()).replace("\"", "\\\"")
            )

        for key, value in node.getLabel().items():
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key = key,
                value = value
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

    def _nodeRoleToString(self, role: NodeRole):
        """!
        @brief convert node role to prefix string

        @param role node role

        @returns prefix string
        """
        if role == NodeRole.Host: return 'h'
        if role == NodeRole.Router: return 'r'
        if role == NodeRole.ControlService: return 'cs'
        if role == NodeRole.RouteServer: return 'rs'
        if role == NodeRole.BorderRouter: return 'brd'
        assert False, 'unknown node role {}'.format(role)

    def _contextToPrefix(self, scope: str, type: str) -> str:
        """!
        @brief Convert context to prefix.

        @param scope scope.
        @param type type.

        @returns prefix string.
        """
        return '{}_{}_'.format(type, scope)

    def _addFile(self, path: str, content: str) -> str:
        """!
        @brief Stage file to local folder and return Dockerfile command.

        @param path path to file. (in container)
        @param content content of the file.

        @returns COPY expression for dockerfile.
        """

        staged_path = md5(path.encode('utf-8')).hexdigest()
        print(content, file=open(staged_path, 'w'))
        return 'COPY {} {}\n'.format(staged_path, path)

    def _importFile(self, path: str, hostpath: str) -> str:
        """!
        @brief Stage file to local folder and return Dockerfile command.

        @param path path to file. (in container)
        @param hostpath path to file. (on host)

        @returns COPY expression for dockerfile.
        """

        staged_path = md5(path.encode('utf-8')).hexdigest()
        copyfile(hostpath, staged_path)
        return 'COPY {} {}\n'.format(staged_path, path)


    def _getComposeNodeName(self, node: Node) -> str:
        """!
        @brief Given a node, compute its final container_name, as it will be
        known in the docker-compose file.
        """
        name = self.__naming_scheme.format(
            asn = node.getAsn(),
            role = self._nodeRoleToString(node.getRole()),
            name = node.getName(),
            displayName = node.getDisplayName() if node.getDisplayName() != None else node.getName(),
            primaryIp = node.getInterfaces()[0].getAddress()
        )

        return sub(r'[^a-zA-Z0-9_.-]', '_', name)

    def _getRealNodeName(self, node: Node) -> str:
        """!
        @brief Computes the sub directory names inside the output folder.
        """
        (scope, type, _) = node.getRegistryInfo()
        prefix = self._contextToPrefix(scope, type)
        return '{}{}'.format(prefix, node.getName())

    def _getRealNetName(self, net: Network):
          """!
          @brief Computes name  of a network as it will be known in the docker-compose file.
          """
          (netscope, _, _) = net.getRegistryInfo()
          net_prefix = self._contextToPrefix(netscope, 'net')
          if net.getType() == NetworkType.Bridge: net_prefix = ''
          return '{}{}'.format(net_prefix, net.getName())

    def _getComposeServicePortList(self, node: Node) -> str:
        """!
        @brief Computes the 'ports:' section of the service in docker-compose.yml.
        """
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
        return ports

    def _getComposeNodeNets(self, node: Node) -> str:

        node_nets = ''
        dummy_addr_map = ''

        for iface in node.getInterfaces():
            net = iface.getNet()
            real_netname = self._getRealNetName(net)
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

            if address == None:
                address = ""
            else:
                address = DockerCompilerFileTemplates['compose_service_network_address'].format(address = address)

            node_nets += DockerCompilerFileTemplates['compose_service_network'].format(
                netId = real_netname,
                address = address
            )
        return node_nets, dummy_addr_map

    def _getComposeNodeVolumes(self, node: Node) -> str:
        """ compute the docker-compose 'volumes:' section for this service(emulation node)"""

        volumes = ''
        # svcvols = map( lambda vol: ServiceLvlVolume(vol), node.getCustomVolumes() )
        svcvols = list (set(node.getDockerVolumes() ))
        for v in svcvols:
            v.mode = 'service'
        yamlvols = '\n'.join(map( lambda line: '        ' + line ,dump( svcvols ).split('\n') ) )

        volumes +='        volumes:\n' + yamlvols if len(node.getDockerVolumes()) > 0 else   ''


        # the top-level docker-compose volumes section is rendered at a later stage ..
        # Remember encountered volumes until then
        for v in node.getDockerVolumes():
            self._addVolume(v)

        return volumes

    def _computeDockerfile(self, node: Node) -> str:
        """!
        @brief Returns dockerfile contents for node.
        """
        dockerfile = DockerCompilerFileTemplates['dockerfile']

        (image, soft) = self._selectImageFor(node)

        if not node.hasAttribute('__soft_install_tiers') and len(soft) > 0:
            dockerfile += 'RUN apt-get update && apt-get install -y --no-install-recommends {}\n'.format(' '.join(sorted(soft)))

        if node.hasAttribute('__soft_install_tiers'):
            softLists: List[List[str]] = node.getAttribute('__soft_install_tiers')
            for softList in softLists:
                softList = set(softList) & soft
                if len(softList) == 0: continue
                dockerfile += 'RUN apt-get update && apt-get install -y --no-install-recommends {}\n'.format(' '.join(sorted(softList)))

        #included in the seedemu-base dockerImage.
        #dockerfile += 'RUN curl -L https://grml.org/zsh/zshrc > /root/.zshrc\n'
        dockerfile = 'FROM {}\n'.format(md5(image.getName().encode('utf-8')).hexdigest()) + dockerfile
        self._used_images.add(image.getName())

        for cmd in node.getDockerCommands(): dockerfile += '{}\n'.format(cmd)
        for cmd in node.getBuildCommands(): dockerfile += 'RUN {}\n'.format(cmd)

        start_commands = ''

        if self.__self_managed_network:
            start_commands += 'chmod +x /replace_address.sh\n'
            start_commands += '/replace_address.sh\n'
            dockerfile += self._addFile('/replace_address.sh', DockerCompilerFileTemplates['replace_address_script'])
            dockerfile += self._addFile('/root/.zshrc.pre', DockerCompilerFileTemplates['zshrc_pre'])

        for (cmd, fork) in node.getStartCommands():
            start_commands += '{}{}\n'.format(cmd, ' &' if fork else '')

        for (cmd, fork) in node.getPostConfigCommands():
            start_commands += '{}{}\n'.format(cmd, ' &' if fork else '')

        dockerfile += self._addFile('/start.sh', DockerCompilerFileTemplates['start_script'].format(
            startCommands = start_commands,
            buildtime_sysctl=self._getNodeBuildtimeSysctl(node)
        ))

        dockerfile += self._addFile('/seedemu_sniffer', DockerCompilerFileTemplates['seedemu_sniffer'])
        dockerfile += self._addFile('/seedemu_worker', DockerCompilerFileTemplates['seedemu_worker'])

        dockerfile += 'RUN chmod +x /start.sh\n'
        dockerfile += 'RUN chmod +x /seedemu_sniffer\n'
        dockerfile += 'RUN chmod +x /seedemu_worker\n'

        for file in node.getFiles():
            (path, content) = file.get()
            dockerfile += self._addFile(path, content)

        for (cpath, hpath) in node.getImportedFiles().items():
            dockerfile += self._importFile(cpath, hpath)

        dockerfile += 'CMD ["/start.sh"]\n'
        return dockerfile

    def _getNodeBuildtimeSysctl(self, node: Node) -> str:
        """!@brief get sysctl-flag settings for /start.sh script
            @note   if a sysctl-option is in BUILD_TIME mode, it will go to /start.sh
                otherwise if mode is RUNTIME the flag will be set in docker-compose.yml
                (except for custom named interfaces such as 'net0' which would still go to /start.sh
                because they simply don't exist yet once the container starts up
                and /interface_setup hasn't been called yet )
        """
        set_flags = []
        rp_opt = node.getOption('sysctl_netipv4_conf_rp_filter')
        for k, v in rp_opt.value.items():
            # custom interfaces are always BUILD_TIME
            if k not in ['all', 'default']:
                rp_filter = f'echo {int(v)} > /proc/sys/net/ipv4/conf/{k}/rp_filter'
                set_flags.append(rp_filter)
            elif rp_opt.mode == OptionMode.BUILD_TIME:
                # flags for 'all' and 'default' interfaces
                # could be set in docker-compose.yml already if OptionMode is RUNTIME
                rp_filter = f'echo {int(v)} > /proc/sys/net/ipv4/conf/{k}/rp_filter'
                set_flags.append(rp_filter)



        if opts := node.getScopedOptions(prefix='sysctl'):
            for o, _ in opts:
                if o.mode != OptionMode.BUILD_TIME:
                    # then its already set in docker-compose.yml
                    continue
                if o.fullname() == 'sysctl_netipv4_conf_rp_filter': continue
                for s in repr(o).split('\n'):
                   set_flags.append(f'sysctl -w {s.strip()} > /dev/null 2>&1')


        return '\n'.join(set_flags)

    def _compileNode(self, node: Node ) -> str:
        """!
        @brief Compile a single node. Will create folder for node and the
        dockerfile.

        @param node node to compile.

        @returns docker-compose service string.
        """
        real_nodename = self._getRealNodeName(node)
        node_nets, dummy_addr_map = self._getComposeNodeNets(node)
        if self.__self_managed_network:
            node.setFile('/dummy_addr_map.txt', dummy_addr_map)

        mkdir(real_nodename)
        chdir(real_nodename)

        image,_ = self._selectImageFor(node)
        dockerfile = self._computeDockerfile(node)
        print(dockerfile, file=open('Dockerfile', 'w'))

        chdir('..')

        name = self._getComposeNodeName(node)
        return DockerCompilerFileTemplates['compose_service'].format(
            nodeId = real_nodename,
            nodeName = name,
            dependsOn = md5(image.getName().encode('utf-8')).hexdigest(),
            networks = node_nets,
            sysctls = self._getNodeSysctls(node),
            # privileged = 'true' if node.isPrivileged() else 'false',
            ports = self._getComposeServicePortList(node),
            labelList = self._getNodeMeta(node),
            volumes = self._getComposeNodeVolumes(node),
            environment= "    - CONTAINER_NAME={}\n            ".format(name) + self._computeNodeEnvironment(node)
        )

    def _getNodeSysctls(self, node: Node) -> str:
        """!@brief compute the 'sysctl:' section of the node's service
                    in docker-compose.yml file
            @note sysctl flags which are set in the docker-compose.yml file
                can be changed, without having to recompile any images and
                thus correspond to OptionMode.RUN_TIME
        """
        opt_keyvals = [] # 'repr' of all sysctl options set on this node i.e. : '- net.ipv4.ip_forwarding = 0'
        #TODO: check if option mode is runtime
        # if not the setting of this option should go to the /start.sh script (BUILD_TIME)
        # Also interfaces other than 'all'|'default' cant go in the docker-compose.yml file
        # because they only exist under this name once the /interface_setup script has run
        # and renamed them to their final/expected names i.e. 'net0'
        if opts := node.getScopedOptions(prefix='sysctl'):
            for o, _ in opts:
                if o.mode == OptionMode.RUN_TIME:
                    if (val := o.repr_runtime()) != None:
                        for s in val.split('\n'):
                            opt_keyvals.append(f'- {s.strip()}')
                    else:
                        opt_keyvals.append(repr(o))
        if len(opt_keyvals) > 0:
            return DockerCompilerFileTemplates['compose_sysctl'] + '           ' + '\n           '.join( opt_keyvals )
        else:
            return ''

    def _computeNodeEnvironment(self, node: Node) -> str:
        """!
        @brief computes the environment section
          of the docker-compose service for the given node
        """

        # just copy all nodes scoped runtime opts into a  list (tuple(opt, scope))
        # and sort the list ascending by scope (specific to more general )
        #  Then uniqueify the list  -> whats left is the .env file's content...
        # minimal without duplicates

        def unique_partial_order_snd(elements):
            unique_list = []

            for elem in elements:
                #if not any(elem == existing or existing < elem or elem < existing for existing in unique_list):
                if not any((elem[1] == existing[1]) and (elem[0].name == existing[0].name) for existing in unique_list):
                    unique_list.append(elem)

            return unique_list


        def cmp_snd(a, b):
            """Custom comparator for sorting based on the second tuple element."""
            try:
                if a[1] < b[1]:
                    return -1
                elif a[1] > b[1]:
                    return 1
                else:
                    return 0
            except TypeError:
                return 0

        scopts = node.getScopedRuntimeOptions()

        if self.__option_handling == OptionHandling.DIRECT_DOCKER_COMPOSE:
            keyval_list = map(lambda x: f'- {x.name.upper()}={x.value}', [ o for o,s in scopts] )
            return '\n            '.join(keyval_list)
        elif self.__option_handling == OptionHandling.CREATE_SEPARATE_ENV_FILE:

            self.__config.extend(scopts)

            res= sorted( self.__config, key=cmp_to_key(cmp_snd) )
            #remember encountered variables for .env file generation later..
            self.__config = unique_partial_order_snd(res)
            keyval_list = map(lambda x: f'- {x[0].name.upper()}=${{{ self._sndary_key(x[0],x[1])}}}',  scopts )
            return '\n            '.join(keyval_list)

    def _sndary_key(self, o: BaseOption, s: Scope )   -> str:
        base = o.name.upper()
        match s.tier:
            case ScopeTier.Global:
                match s.type:
                    case ScopeType.ANY:
                        return base
                    case ScopeType.BRDNODE:
                        return f'{base}_BRDNODE'
                    case ScopeType.HNODE:
                        return f'{base}_HNODE'
                    case ScopeType.CSNODE:
                        return f'{base}_CSNODE'
                    case ScopeType.RSNODE:
                        return f'{base}_RSNODE'
                    case ScopeType.RNODE:
                        return f'{base}_RNODE'
                    case _:
                        #TODO: combination (ORed) Flags not yet implemented
                        raise NotImplementedError
            case ScopeTier.AS:
                match s.type:
                    case ScopeType.ANY:
                        return f'{base}_{s.asn}'
                    case ScopeType.BRDNODE:
                        return f'{base}_{s.asn}_BRDNODE'
                    case ScopeType.HNODE:
                        return f'{base}_{s.asn}_HNODE'
                    case ScopeType.CSNODE:
                        return f'{base}_{s.asn}_CSNODE'
                    case ScopeType.RSNODE:
                        return f'{base}_{s.asn}_RSNODE'
                    case ScopeType.RNODE:
                        return f'{base}_{s.asn}_RNODE'
                    case _:
                        # combination (ORed) Flags not yet implemented
                        #TODO: How should we call CSNODE|HNODE or BRDNODE|RSNODE|RNODE ?!
                        raise NotImplementedError
            case ScopeTier.Node:
                return f'{base}_{s.asn}_{s.node.upper()}' # maybe add type here

    def _compileNet(self, net: Network) -> str:
        """!
        @brief compile a network.

        @param net net object.

        @returns docker-compose network string.
        """
        if self.__self_managed_network and net.getType() != NetworkType.Bridge:
            pfx = next(self.__dummy_network_pool)
            net.setAttribute('dummy_prefix', pfx)
            net.setAttribute('dummy_prefix_index', 2)
            self._log('self-managed network: using dummy prefix {}'.format(pfx))


        return DockerCompilerFileTemplates['compose_network'].format(
            netId = self._getRealNetName(net),
            prefix = net.getAttribute('dummy_prefix') if self.__self_managed_network and net.getType() != NetworkType.Bridge else net.getPrefix(),
            mtu = net.getMtu(),
            labelList = self._getNetMeta(net)
        )

    def generateEnvFile(self, scope: Scope, dir_prefix: str = '/'):
        """!
           @brief   generates the '.env' file that accompanies any 'docker-compose.yml' file
           @param scope  filter ENV variables by scope (i.e. ASN).
                This is required i.e. by DistributedDocker compiler which generates a separate .env file per AS,
                which contains only the relevant subset of all variables.
        """

        prefix=dir_prefix
        if dir_prefix != '' and not dir_prefix.endswith('/'):
            prefix += '/'

        vars = []
        for o,s in self.__config:
            try:
                if s < scope or s == scope:
                    sndkey = self._sndary_key(o,s)
                    val = o.value
                    vars.append( f'{sndkey}={val}')
            except:
                pass
        assert len(vars)==len(self.__config), 'implementation error'
        print( '\n'.join(vars) ,file=open(f'{prefix}.env','w'))

    def _makeDummies(self) -> str:
        """!
        @brief create dummy services to get around docker pull limits.

        @returns docker-compose service string.
        """
        mkdir('dummies')
        chdir('dummies')

        dummies = ''

        for image in self._used_images:
            self._log('adding dummy service for image {}...'.format(image))

            imageDigest = md5(image.encode('utf-8')).hexdigest()
            dockerImage, _ = self.__images[image]
            if dockerImage.isLocal():
                dummies += DockerCompilerFileTemplates['compose_dummy'].format(
                    imageDigest = imageDigest,
                    dependsOn= DockerCompilerFileTemplates['depends_on'].format(
                        dependsOn = image
                    )
                )
            else:
                dummies += DockerCompilerFileTemplates['compose_dummy'].format(
                    imageDigest = imageDigest,
                    dependsOn= ""
                )

            dockerfile = 'FROM {}\n'.format(image)
            print(dockerfile, file=open(imageDigest, 'w'))

        chdir('..')

        return dummies

    def _doCompile(self, emulator: Emulator):
        registry = emulator.getRegistry()

        self._groupSoftware(emulator)

        for ((scope, type, name), obj) in registry.getAll().items():

            if type == 'net':
                self._log('creating network: {}/{}...'.format(scope, name))
                self.__networks += self._compileNet(obj)

        for ((scope, type, name), obj) in registry.getAll().items():
            if type == 'rnode':
                self._log('compiling router node {} for as{}...'.format(name, scope))
                self.__services += self._compileNode(obj)

            if type == 'csnode':
                self._log('compiling control service node {} for as{}...'.format(name, scope))
                self.__services += self._compileNode(obj)

            if type == 'hnode':
                self._log('compiling host node {} for as{}...'.format(name, scope))
                self.__services += self._compileNode(obj)

            if type == 'rs':
                self._log('compiling rs node for {}...'.format(name))
                self.__services += self._compileNode(obj)

            if type == 'snode':
                self._log('compiling service node {}...'.format(name))
                self.__services += self._compileNode(obj)

        # Add the Internet Map contaienr to the emulator
        if self.__internet_map_enabled:
            self._log('enabling seedemu-internet-map...')

            # Attach the Map container to the default network
            self.attachInternetMap(port_forwarding="{}:8080/tcp".format(self.__internet_map_port))


        # Add the Ether View contaienr to docker's default network
        if self.__ether_view_enabled:
            self._log('enabling seedemu-ether-view...')

            self.__services += DockerCompilerFileTemplates['seedemu_ether_view'].format(
                clientImage = SEEDEMU_ETHER_VIEW_IMAGE,
                clientPort = self.__ether_view_port
            )
            self.__services += '\n'


        # Add custom entries (typically added through Docker::attachCustomContainer APIs)
        self.__services += self.__custom_services


        local_images = ''

        for (image, _) in self.__images.values():
            if image.getName() not in self._used_images or not image.isLocal(): continue
            local_images += DockerCompilerFileTemplates['local_image'].format(
                imageName = image.getName(),
                dirName = image.getDirName()
            )

        toplevelvolumes = self._computeComposeTopLvlVolumes()

        self._log('creating docker-compose.yml...'.format(scope, name))
        print(DockerCompilerFileTemplates['compose'].format(
            services = self.__services,
            networks = self.__networks,
            volumes = toplevelvolumes,
            dummies = local_images + self._makeDummies()
        ), file=open('docker-compose.yml', 'w'))

        self.generateEnvFile(Scope(ScopeTier.Global),'')

    def _computeComposeTopLvlVolumes(self) -> str:
        """!@brief render the 'volumes:' section of the docker-compose.yml file
        It contains named volumes but not bind-mounts.
        """
        toplevelvolumes = ''
        if len(topvols := self._getVolumes()) > 0:
            hit = False
            #topvols = set(map( lambda vol: TopLvlVolume(vol), pool.getVolumes() ))

            for v in  topvols:
                v.mode = 'toplevel'

            #toplevelvolumes += '\n'.join(map( lambda line: '        ' + line ,dump( topvols ).split('\n') ) )

            # sharedFolders/bind mounts do not belong in the top-level volumes section
            for v in [vv  for  vv in topvols if vv.asDict()['type'] == 'volume' ]:
                hit = True
                toplevelvolumes += '  {}:\n'.format(v.asDict()['source']) # why not 'name'
                lines = dump( v ).rstrip('\n').split('\n')
                toplevelvolumes += '\n'.join( map( lambda x: '        '
                                                  if x[0] != 0 else '        ' + x[1]
                                                  if x[1] != ''else '' , enumerate(lines ) ) )
                toplevelvolumes += '\n'

            if hit: toplevelvolumes = 'volumes:\n' + toplevelvolumes
        return toplevelvolumes

        def attachInternetMap(self, asn: int = -1, net: str = '', ip_address: str = '',
                          port_forwarding: str = '', env: list = [],
                          show_on_map=False, node_name='seedemu_internet_map') -> Docker:
        """!
        @brief add the pre-built Map container to the emulator (the entry should not
            include any network entry, as the network entry will be added here)

        @param asn the autonomous system number of the network. -1 means no network
            information is provided, so the container will be attached to the default
            network provided by the docker
        @param net the name of the network that this container is attached to.
        @param ip_address the IP address set for this container. If no IP address is provided,
            docker will provide one when building the image.
        @param port_forwarding the port forwarding field.
        @param env the list of the environment variables.
        @param show_on_map it is show on the map.
        @param node_name.

        @returns self, for chaining API calls.
        """

        self._log('attaching the Internet Map container to {}:{}'.format(asn, net))

        # If this is not set to False, Docker compiler will attach another copy of the MAP
        # container to the default network. This is to avoid that.
        self.__internet_map_enabled = False

        self.attachCustomContainer(DockerCompilerFileTemplates['seedemu_internet_map'].format(
            clientImage=SEEDEMU_INTERNET_MAP_IMAGE), asn=asn, net=net, ip_address=ip_address,
            port_forwarding=port_forwarding, env=env, show_on_map=show_on_map, node_name=node_name)
        return self

    def attachCustomContainer(self, compose_entry: str, asn: int = -1, net: str = '',
                              ip_address: str = '', port_forwarding: str = '', env: list = [],
                              show_on_map=False, node_name: str = 'unnamed') -> Docker:
        """!
        @brief add an pre-built container image to the emulator (the entry should not
            include any network entry, as the network entry will be added here)

        @param entry the docker compose entry (without the network entry)
        @param asn the autonomous system number of the network. -1 means no network
            information is provided, so the container will be attached to the default
            network provided by the docker
        @param net the name of the network that this container is attached to.
        @param ip_address the IP address set for this container. If no IP address is provided,
            docker will provide one when building the image.
        @param port_forwarding the port forwarding field.

        @param env the list of the environment variables.
        @param show_on_map it is show on the map.
        @param node_name.

        @returns self, for chaining API calls.
        """

        self._log('attaching an existing container to {}:{}'.format(asn, net))

        self.__custom_services += compose_entry

        if port_forwarding != '':
            self.__custom_services += DockerCompilerFileTemplates['port_forwarding_entry'].format(
                port_forwarding_field=port_forwarding
            )

        if env:
            self.__custom_services += DockerCompilerFileTemplates['environment_variable_entry']

            field_name = DockerCompilerFileTemplates['environment_variable_entry']
            # count how many leading spaces this field name has (for alignment purpose)
            leading_spaces = len(field_name) - len(field_name.lstrip())
            for e in env:
                self.__custom_services += '{}- {}\n'.format(' ' * (leading_spaces + 4), e)

        if asn < 0:  # Do not set the network entry; will use the default docker network
            self.__custom_services += '\n'
        else:
            net_prefix = self._contextToPrefix(asn, 'net')
            real_netname = '{}{}'.format(net_prefix, net)

            # Construct the IP address field (leave it empty if IP address is not provided)
            if ip_address == '':
                ipv4_address_entry = ''
            else:
                ipv4_address_entry = 'ipv4_address: {}'.format(ip_address)

            self.__custom_services += DockerCompilerFileTemplates['network_entry'].format(
                network_name_field=real_netname,
                ipv4_address_field=ipv4_address_entry
            )
            self.__custom_services += '\n'

        if show_on_map:
            self.__custom_services += DockerCompilerFileTemplates['custom_compose_label_meta'].format(labelList=self._getCustomNodeMeta(
                asn, node_name, net, ip_address
            ))
            self.__custom_services += '\n'

        return self

    def _getCustomNodeMeta(self, asn: int = -1, node_name: str = '', net: str = '', ip_address: str = '', ) -> str:
        """!
        @brief get custom node metadata labels.

        @returns metadata labels string.
        """
        labels = ''

        if asn > -1:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='asn',
                value=asn
            )
        if node_name:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='nodename',
                value=node_name
            )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key='role',
            value='Host'
        )
        if net:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='net.0.name',
                value=net
            )
        if ip_address:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='net.0.address',
                value=ip_address
            )
        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key='custom',
            value='custom'
        )

        return labels

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from seedemu.core.Emulator import Emulator
from seedemu.core import (
    Node, Network, Compiler, BaseSystem, BaseOption,
    Scope, ScopeType, ScopeTier, OptionHandling,
    BaseVolume, OptionMode
)
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
import shlex
from yaml import dump

from seedemu.core.ExternalEmulation import ExternalEmuSpec, ExternalNetRef, ExternalFileSpec


SEEDEMU_INTERNET_MAP_IMAGE = 'handsonsecurity/seedemu-multiarch-map:buildx-latest'
SEEDEMU_ETHER_VIEW_IMAGE = 'handsonsecurity/seedemu-multiarch-etherview:buildx-latest'


DockerCompilerFileTemplates: Dict[str, str] = {}

# ----------------------------
# External Emulation (Task 3)
# ----------------------------

DockerCompilerFileTemplates['compose_external_emu'] = """\
    {serviceId}:
        image: {image}
        container_name: {containerName}
{privileged}{cap_add}{workdir}{command}        volumes:
            - ./{bundleDir}:{mountTo}
{networks_block}{environment_block}
"""

# ----------------------------
# Existing templates
# ----------------------------

DockerCompilerFileTemplates['compose_external_service'] = """\
    {serviceId}:
        build: ./{serviceId}
        container_name: {containerName}
{cap_add}{privileged}        networks:
{networks}{ports}{volumes}        environment:
{environment}
"""

DockerCompilerFileTemplates['dockerfile'] = """\
ARG DEBIAN_FRONTEND=noninteractive
"""

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
    ip -j link | jq -cr '.[] .ifname' | while read -r ifname; do
        ip link set "$ifname" "$1"
    done
}

bgp() {
    cmd="$1"
    peer="$2"
    [ "$cmd" = "bird_peer_down" ] && birdc dis "$peer"
    [ "$cmd" = "bird_peer_up" ] && birdc en "$peer"
}

while read -sr line; do {
    id="`cut -d ';' -f1 <<< "$line"`"
    cmd="`cut -d ';' -f2 <<< "$line"`"
    peer="`cut -d ';' -f3 <<< "$line"`"

    output="no such command."

    [ "$cmd" = "net_down" ] && output="`net down 2>&1`"
    [ "$cmd" = "net_up" ] && output="`net up 2>&1`"
    [ "$cmd" = "net_status" ] && output="`net status 2>&1`"
    [ "$cmd" = "bird_list_peer" ] && output="`birdc s p | grep --color=never BGP 2>&1`"

    [[ "$cmd" == "bird_peer_"* ]] && output="`bgp "$cmd" "$peer" 2>&1`"

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
    {serviceName}:
        image: {clientImage}
        container_name: {containerName}
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

DockerCompilerFileTemplates['custom_compose_label_meta'] = """\
        labels:
{labelList}
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
    __config: List[Tuple[BaseOption, Scope]]  # all encountered Options for .env file
    __option_handling: OptionHandling  # strategy how to deal with Options
    __basesystem_dockerimage_mapping: dict

    def __init__(
        self,
        platform: Platform = Platform.AMD64,
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
        self.__option_handling = option_handling
        self.__networks = ""
        self.__services = ""
        self.__custom_services = ""
        self.__naming_scheme = namingScheme
        self.__self_managed_network = selfManagedNetwork
        self.__dummy_network_pool = IPv4Network(dummyNetworksPool).subnets(new_prefix=dummyNetworksMask)

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
        self.__config = []  # variables for '.env' file alongside 'docker-compose.yml'

        self.__volumes_dedup = []
        self.__vol_names = []
        super().__init__()

        self.__platform = platform
        self.__basesystem_dockerimage_mapping = BASESYSTEM_DOCKERIMAGE_MAPPING_PER_PLATFORM[self.__platform]

        for name, image in self.__basesystem_dockerimage_mapping.items():
            priority = 0
            if name == BaseSystem.DEFAULT:
                priority = 1
            self.addImage(image, priority=priority)

    # ----------------------------
    # External Emulation (Task 3)
    # ----------------------------

    def _resolve_external_net(self, emulator: Emulator, ref: ExternalNetRef) -> str:
        """
        Map ExternalNetRef -> docker-compose network name used by SEED.
        """
        reg = emulator.getRegistry()

        if ref.scope == "ix":
            target_scope = "ix"
            target_name = ref.name
        elif ref.scope == "as":
            assert ref.asn is not None, "ExternalNetRef(scope='as') requires asn"
            target_scope = str(ref.asn)
            target_name = ref.name
        else:
            raise ValueError(f"Unknown ExternalNetRef.scope: {ref.scope}")

        for ((scope, typ, name), obj) in reg.getAll().items():
            if typ != "net":
                continue
            if str(scope) == str(target_scope) and name == target_name:
                return self._getRealNetName(obj)

        raise KeyError(f"Could not find network: scope={target_scope} name={target_name}")

    def _writeExternalEmuBundles(self, output_dir: str, specs: List[ExternalEmuSpec]) -> None:
        """
        Writes generated files for ExternalEmuSpec into:
          <output_dir>/external_emulations/<spec.name>/...
        """
        out = Path(output_dir).resolve()
        base = out / "external_emulations"
        base.mkdir(parents=True, exist_ok=True)

        for spec in specs:
            spec_dir = base / spec.name
            spec_dir.mkdir(parents=True, exist_ok=True)

            for fs in spec.files:
                fpath = spec_dir / fs.relpath
                fpath.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(fs.content, bytes):
                    fpath.write_bytes(fs.content)
                else:
                    fpath.write_text(str(fs.content), encoding="utf-8")

        self._log(f"Wrote external emulation bundles to: {base}")

    def _compileExternalEmuService(self, emulator: Emulator, spec: ExternalEmuSpec) -> str:
        """
        Adds a docker-compose service for one ExternalEmuSpec.
        """
        service_id = sub(r'[^a-zA-Z0-9_.-]', '_', f"extemu_{spec.name}")
        container_name = service_id
        bundle_dir = str((Path("external_emulations") / spec.name)).replace("\\", "/")

        privileged = "        privileged: true\n" if getattr(spec, "privileged", True) else ""
        cap_add = "        cap_add:\n            - ALL\n" if getattr(spec, "cap_add_all", True) else ""

        workdir = ""
        if getattr(spec, "workdir", None):
            workdir = f"        working_dir: {json.dumps(spec.workdir)}\n"

        command = ""
        if getattr(spec, "command", None):
            command = f"        command: {json.dumps(spec.command)}\n"

        # networks block
        networks_block = ""
        if getattr(spec, "networks", None):
            nets = ""
            for nref in spec.networks:
                net_name = self._resolve_external_net(emulator, nref)
                if getattr(nref, "ipv4", None):
                    nets += f"            {net_name}:\n                ipv4_address: {nref.ipv4}\n"
                else:
                    nets += f"            {net_name}:\n"
            networks_block = "        networks:\n" + nets

        # environment block (optional)
        environment_block = ""
        if getattr(spec, "env", None):
            env_lines = ""
            for k, v in spec.env.items():
                env_lines += f"            - {k}={v}\n"
            environment_block = "        environment:\n" + env_lines

        return DockerCompilerFileTemplates['compose_external_emu'].format(
            serviceId=service_id,
            image=spec.image,
            containerName=container_name,
            privileged=privileged,
            cap_add=cap_add,
            workdir=workdir,
            command=command,
            bundleDir=bundle_dir,
            mountTo=getattr(spec, "mount_to", "/seedext"),
            networks_block=networks_block,
            environment_block=environment_block
        ) + "\n"

    # ----------------------------
    # Existing Docker compiler code
    # ----------------------------

    def _addVolume(self, vol: BaseVolume):
        key = vol.asDict()["source"]
        if key not in self.__vol_names:
            self.__volumes_dedup.append(vol)
            self.__vol_names.append(key)
        return self

    def _getVolumes(self) -> List[BaseVolume]:
        return self.__volumes_dedup

    def optionHandlingCapabilities(self) -> OptionHandling:
        return OptionHandling.DIRECT_DOCKER_COMPOSE | OptionHandling.CREATE_SEPARATE_ENV_FILE

    def getName(self) -> str:
        return "Docker"

    def addImage(self, image: DockerImage, priority: int = -1) -> "Docker":
        assert image.getName() not in self.__images, f'image with name {image.getName()} already exists.'
        self.__images[image.getName()] = (image, priority)
        return self

    def getImages(self) -> List[Tuple[DockerImage, int]]:
        return list(self.__images.values())

    def forceImage(self, imageName: str) -> "Docker":
        self.__forced_image = imageName
        return self

    def disableImages(self, disabled: bool = True) -> "Docker":
        self.__disable_images = disabled
        return self

    def setImageOverride(self, node: Node, imageName: str) -> "Docker":
        asn = node.getAsn()
        name = node.getName()
        self.__image_per_node_list[(asn, name)] = imageName
        return self

    def _groupSoftware(self, emulator: Emulator):
        registry = emulator.getRegistry()

        # --- Task 2: export external components config for hardware/standalone hookup ---
        externals = getattr(emulator, "getExternalComponents", lambda: {})()
        self._log(f"External components detected: {list(externals.keys())}")

        external_dump = {}
        for name, ext in externals.items():
            external_dump[name] = {
                "name": getattr(ext, "name", name),
                "role": getattr(ext, "role", None),
                "asn": getattr(ext, "asn", None),
                "impl_type": getattr(ext, "impl_type", None),
                "interfaces": [
                    {
                        "name": getattr(i, "name", None),
                        "network": getattr(i, "network", None),
                        "ip": getattr(i, "ip", None),
                        "mac": getattr(i, "mac", None),
                    }
                    for i in getattr(ext, "interfaces", [])
                ],
                "scion": getattr(ext, "scion", {}),
            }

        if external_dump:
            with open("externals.json", "w", encoding="utf-8") as f:
                json.dump(external_dump, f, indent=2)
            self._log("Wrote externals.json (for hardware/standalone integration).")

        softGroups: Dict[str, Dict[str, List[Node]]] = {}
        groupIter: Dict[str, int] = {}

        for ((scope, type, name), obj) in registry.getAll().items():
            if type not in ['rnode', 'csnode', 'hnode', 'snode', 'rs', 'snode']:
                continue

            node: Node = obj
            (img, _) = self._selectImageFor(node)
            imgName = img.getName()

            if imgName not in groupIter:
                groupIter[imgName] = 0
            groupIter[imgName] += 1

            if imgName not in softGroups:
                softGroups[imgName] = {}

            group = softGroups[imgName]

            for soft in node.getSoftware():
                if soft not in group:
                    group[soft] = []
                group[soft].append(node)

        for (key, val) in softGroups.items():
            maxIter = groupIter[key]
            self._log(f'grouping software for image "{key}" - {maxIter} references.')
            step = 1

            for commRequired in range(maxIter, 0, -1):
                currentTier: Set[str] = set()
                currentTierNodes: Set[Node] = set()

                for (soft, nodes) in val.items():
                    if len(nodes) == commRequired:
                        currentTier.add(soft)
                        for node in nodes:
                            currentTierNodes.add(node)

                for node in currentTierNodes:
                    if not node.hasAttribute('__soft_install_tiers'):
                        node.setAttribute('__soft_install_tiers', [])
                    node.getAttribute('__soft_install_tiers').append(currentTier)

                if len(currentTier) > 0:
                    self._log(
                        f'the following software has been grouped together in step {step}: {currentTier} '
                        f'since they are referenced by {len(currentTierNodes)} nodes.'
                    )
                    step += 1

    def _selectImageFor(self, node: Node) -> Tuple[DockerImage, Set[str]]:
        nodeSoft = node.getSoftware()
        nodeKey = (node.getAsn(), node.getName())

        if nodeKey in self.__image_per_node_list:
            image_name = self.__image_per_node_list[nodeKey]
            assert image_name in self.__images, f'image-per-node configured, but image {image_name} does not exist.'
            (image, _) = self.__images[image_name]
            self._log(f'image-per-node configured, using {image.getName()}')
            return (image, nodeSoft - image.getSoftware())

        if self.__disable_images:
            self._log('disable-imaged configured, using base image.')
            (image, _) = self.__images['ubuntu:20.04']
            return (image, nodeSoft - image.getSoftware())

        if self.__forced_image is not None:
            assert self.__forced_image in self.__images, f'forced-image configured, but image {self.__forced_image} does not exist.'
            (image, _) = self.__images[self.__forced_image]
            self._log(f'force-image configured, using image: {image.getName()}')
            return (image, nodeSoft - image.getSoftware())

        image = self.__basesystem_dockerimage_mapping[node.getBaseSystem()]
        return (image, nodeSoft - image.getSoftware())

    def _getNetMeta(self, net: Network) -> str:
        (scope, type, name) = net.getRegistryInfo()
        labels = ''

        if self.__client_hide_svcnet and scope == 'seedemu' and name == '000_svc':
            return DockerCompilerFileTemplates['compose_label_meta'].format(
                key='dummy',
                value='dummy label for hidden node/net'
            )

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(
            key='type',
            value='global' if scope == 'ix' else 'local'
        )
        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='scope', value=scope)
        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='name', value=name)
        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='prefix', value=net.getPrefix())

        if net.getDisplayName() is not None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='displayname', value=net.getDisplayName()
            )
        if net.getDescription() is not None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='description', value=net.getDescription()
            )

        return labels

    def _getNodeMeta(self, node: Node) -> str:
        (scope, type, name) = node.getRegistryInfo()
        labels = ''

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='asn', value=node.getAsn())
        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='nodename', value=name)

        if type == 'hnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='Host')
        if type == 'rnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='Router')
        if type == 'brdnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='BorderRouter')
        if type == 'csnode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='SCION Control Service')
        if type == 'snode':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='Emulator Service Worker')
        if type == 'rs':
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='Route Server')

        if node.getDisplayName() is not None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='displayname', value=node.getDisplayName()
            )
        if node.getDescription() is not None:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='description', value=node.getDescription()
            )

        if len(node.getClasses()) > 0:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key='class',
                value=json.dumps(node.getClasses()).replace("\"", "\\\"")
            )

        for key, value in node.getLabel().items():
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key=key, value=value)

        n = 0
        for iface in node.getInterfaces():
            net = iface.getNet()
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key=f'net.{n}.name', value=net.getName())
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(
                key=f'net.{n}.address',
                value=f'{iface.getAddress()}/{net.getPrefix().prefixlen}'
            )
            n += 1

        return labels

    def _nodeRoleToString(self, role: NodeRole):
        if role == NodeRole.Host:
            return 'h'
        if role == NodeRole.Router:
            return 'r'
        if role == NodeRole.OpenVpnRouter:
            return 'r'
        if role == NodeRole.ControlService:
            return 'cs'
        if role == NodeRole.RouteServer:
            return 'rs'
        if role == NodeRole.BorderRouter:
            return 'brd'
        assert False, f'unknown node role {role}'

    def _contextToPrefix(self, scope: str, type: str) -> str:
        return f'{type}_{scope}_'

    def _addFile(self, path: str, content: str) -> str:
        staged_path = md5(path.encode('utf-8')).hexdigest()
        print(content, file=open(staged_path, 'w'))
        return f'COPY {staged_path} {path}\n'

    def _importFile(self, path: str, hostpath: str) -> str:
        staged_path = md5(path.encode('utf-8')).hexdigest()
        copyfile(hostpath, staged_path)
        return f'COPY {staged_path} {path}\n'

    def _getComposeNodeName(self, node: Node) -> str:
        name = self.__naming_scheme.format(
            asn=node.getAsn(),
            role=self._nodeRoleToString(node.getRole()),
            name=node.getName(),
            displayName=node.getDisplayName() if node.getDisplayName() is not None else node.getName(),
            primaryIp=node.getInterfaces()[0].getAddress()
        )
        return sub(r'[^a-zA-Z0-9_.-]', '_', name)

    def _getRealNodeName(self, node: Node) -> str:
        (scope, type, _) = node.getRegistryInfo()
        prefix = self._contextToPrefix(scope, type)
        return f'{prefix}{node.getName()}'

    def _getRealNetName(self, net: Network):
        (netscope, _, _) = net.getRegistryInfo()
        net_prefix = self._contextToPrefix(netscope, 'net')
        if net.getType() == NetworkType.Bridge:
            net_prefix = ''
        return f'{net_prefix}{net.getName()}'

    def _getComposeServicePortList(self, node: Node) -> str:
        _ports = node.getPorts()
        ports = ''
        if len(_ports) > 0:
            lst = ''
            for (h, n, p) in _ports:
                lst += DockerCompilerFileTemplates['compose_port'].format(
                    hostPort=h,
                    nodePort=n,
                    proto=p
                )
            ports = DockerCompilerFileTemplates['compose_ports'].format(portList=lst)
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

                self._log(
                    'using self-managed network: using dummy address {}/{} for {}/{} on as{}/{}'.format(
                        d_address, d_prefix.prefixlen, iface.getAddress(), iface.getNet().getPrefix().prefixlen,
                        node.getAsn(), node.getName()
                    )
                )

            if address is None:
                address = ""
            else:
                address = DockerCompilerFileTemplates['compose_service_network_address'].format(address=address)

            node_nets += DockerCompilerFileTemplates['compose_service_network'].format(
                netId=real_netname,
                address=address
            )

        return node_nets, dummy_addr_map

    def _getComposeNodeVolumes(self, node: Node) -> str:
        volumes = ''
        svcvols = list(set(node.getDockerVolumes()))
        for v in svcvols:
            v.mode = 'service'
        yamlvols = '\n'.join(map(lambda line: '        ' + line, dump(svcvols).split('\n')))
        volumes += '        volumes:\n' + yamlvols if len(node.getDockerVolumes()) > 0 else ''

        for v in node.getDockerVolumes():
            self._addVolume(v)
        return volumes

    def _computeDockerfile(self, node: Node) -> str:
        dockerfile = DockerCompilerFileTemplates['dockerfile']

        (image, soft) = self._selectImageFor(node)

        if not node.hasAttribute('__soft_install_tiers') and len(soft) > 0:
            dockerfile += 'RUN apt-get update && apt-get install -y --no-install-recommends {}\n'.format(
                ' '.join(sorted(soft))
            )

        if node.hasAttribute('__soft_install_tiers'):
            softLists: List[List[str]] = node.getAttribute('__soft_install_tiers')
            for softList in softLists:
                softList = set(softList) & soft
                if len(softList) == 0:
                    continue
                dockerfile += 'RUN apt-get update && apt-get install -y --no-install-recommends {}\n'.format(
                    ' '.join(sorted(softList))
                )

        dockerfile = 'FROM {}\n'.format(md5(image.getName().encode('utf-8')).hexdigest()) + dockerfile
        self._used_images.add(image.getName())

        for cmd in node.getDockerCommands():
            dockerfile += f'{cmd}\n'
        for cmd in node.getBuildCommands():
            dockerfile += f'RUN {cmd}\n'

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
            startCommands=start_commands,
            buildtime_sysctl=self._getNodeBuildtimeSysctl(node)
        ))

        dockerfile += self._addFile('/seedemu_sniffer', DockerCompilerFileTemplates['seedemu_sniffer'])
        dockerfile += self._addFile('/seedemu_worker', DockerCompilerFileTemplates['seedemu_worker'])

        dockerfile += 'RUN chmod +x /start.sh\n'
        dockerfile += 'RUN set -e; for f in /start.sh /interface_setup; do ' \
              'if [ -f "$f" ]; then tr -d "\\r" < "$f" > "$f.tmp"; mv "$f.tmp" "$f"; chmod +x "$f"; fi; ' \
              'done\n'


        dockerfile += 'RUN chmod +x /seedemu_sniffer\n'
        dockerfile += 'RUN chmod +x /seedemu_worker\n'

        for file in node.getFiles():
            (path, content) = file.get()
            dockerfile += self._addFile(path, content)

        for (cpath, hpath) in node.getImportedFiles().items():
            dockerfile += self._importFile(cpath, hpath)

        for cmd in node.getBuildCommandsAtEnd():
            dockerfile += f'RUN {cmd}\n'

        dockerfile += 'CMD ["/start.sh"]\n'
        return dockerfile

    def _getNodeBuildtimeSysctl(self, node: Node) -> str:
        set_flags = []
        rp_opt = node.getOption('sysctl_netipv4_conf_rp_filter')
        for k, v in rp_opt.value.items():
            if k not in ['all', 'default']:
                rp_filter = f'echo {int(v)} > /proc/sys/net/ipv4/conf/{k}/rp_filter'
                set_flags.append(rp_filter)
            elif rp_opt.mode == OptionMode.BUILD_TIME:
                rp_filter = f'echo {int(v)} > /proc/sys/net/ipv4/conf/{k}/rp_filter'
                set_flags.append(rp_filter)

        if opts := node.getScopedOptions(prefix='sysctl'):
            for o, _ in opts:
                if o.mode != OptionMode.BUILD_TIME:
                    continue
                if o.fullname() == 'sysctl_netipv4_conf_rp_filter':
                    continue
                for s in repr(o).split('\n'):
                    set_flags.append(f'sysctl -w {s.strip()} > /dev/null 2>&1')

        return '\n'.join(set_flags)

    def _compileNode(self, node: Node) -> str:
        real_nodename = self._getRealNodeName(node)
        node_nets, dummy_addr_map = self._getComposeNodeNets(node)
        if self.__self_managed_network:
            node.setFile('/dummy_addr_map.txt', dummy_addr_map)

        mkdir(real_nodename)
        chdir(real_nodename)

        image, _ = self._selectImageFor(node)
        dockerfile = self._computeDockerfile(node)
        print(dockerfile, file=open('Dockerfile', 'w'))

        chdir('..')

        name = self._getComposeNodeName(node)
        return DockerCompilerFileTemplates['compose_service'].format(
            nodeId=real_nodename,
            nodeName=name,
            dependsOn=md5(image.getName().encode('utf-8')).hexdigest(),
            networks=node_nets,
            sysctls=self._getNodeSysctls(node),
            ports=self._getComposeServicePortList(node),
            labelList=self._getNodeMeta(node),
            volumes=self._getComposeNodeVolumes(node),
            environment="    - CONTAINER_NAME={}\n            ".format(name) + self._computeNodeEnvironment(node)
        )

    def _getNodeSysctls(self, node: Node) -> str:
        opt_keyvals = []
        if opts := node.getScopedOptions(prefix='sysctl'):
            for o, _ in opts:
                if o.mode == OptionMode.RUN_TIME:
                    if (val := o.repr_runtime()) is not None:
                        for s in val.split('\n'):
                            opt_keyvals.append(f'- {s.strip()}')
                    else:
                        opt_keyvals.append(repr(o))
        if len(opt_keyvals) > 0:
            return DockerCompilerFileTemplates['compose_sysctl'] + '           ' + '\n           '.join(opt_keyvals)
        else:
            return ''

    def _computeNodeEnvironment(self, node: Node) -> str:
        def unique_partial_order_snd(elements):
            unique_list = []
            for elem in elements:
                if not any((elem[1] == existing[1]) and (elem[0].name == existing[0].name) for existing in unique_list):
                    unique_list.append(elem)
            return unique_list

        def cmp_snd(a, b):
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
            keyval_list = map(lambda x: f'- {x.name.upper()}={x.value}', [o for o, s in scopts])
            return '\n            '.join(keyval_list)

        elif self.__option_handling == OptionHandling.CREATE_SEPARATE_ENV_FILE:
            self.__config.extend(scopts)
            res = sorted(self.__config, key=cmp_to_key(cmp_snd))
            self.__config = unique_partial_order_snd(res)
            keyval_list = map(lambda x: f'- {x[0].name.upper()}=${{{self._sndary_key(x[0], x[1])}}}', scopts)
            return '\n            '.join(keyval_list)

        return ""

    def _sndary_key(self, o: BaseOption, s: Scope) -> str:
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
                        raise NotImplementedError
            case ScopeTier.Node:
                return f'{base}_{s.asn}_{s.node.upper()}'

    def _compileNet(self, net: Network) -> str:
        if self.__self_managed_network and net.getType() != NetworkType.Bridge:
            pfx = next(self.__dummy_network_pool)
            net.setAttribute('dummy_prefix', pfx)
            net.setAttribute('dummy_prefix_index', 2)
            self._log(f'self-managed network: using dummy prefix {pfx}')

        return DockerCompilerFileTemplates['compose_network'].format(
            netId=self._getRealNetName(net),
            prefix=net.getAttribute('dummy_prefix') if self.__self_managed_network and net.getType() != NetworkType.Bridge else net.getPrefix(),
            mtu=net.getMtu(),
            labelList=self._getNetMeta(net)
        )

    def generateEnvFile(self, scope: Scope, dir_prefix: str = '/'):
        prefix = dir_prefix
        if dir_prefix != '' and not dir_prefix.endswith('/'):
            prefix += '/'

        vars = []
        for o, s in self.__config:
            try:
                if s < scope or s == scope:
                    sndkey = self._sndary_key(o, s)
                    val = o.value
                    vars.append(f'{sndkey}={val}')
            except:
                pass
        assert len(vars) == len(self.__config), 'implementation error'
        print('\n'.join(vars), file=open(f'{prefix}.env', 'w'))

    def _makeDummies(self) -> str:
        mkdir('dummies')
        chdir('dummies')

        dummies = ''
        for image in self._used_images:
            self._log(f'adding dummy service for image {image}...')

            imageDigest = md5(image.encode('utf-8')).hexdigest()
            dockerImage, _ = self.__images[image]
            if dockerImage.isLocal():
                dummies += DockerCompilerFileTemplates['compose_dummy'].format(
                    imageDigest=imageDigest,
                    dependsOn=DockerCompilerFileTemplates['depends_on'].format(dependsOn=image)
                )
            else:
                dummies += DockerCompilerFileTemplates['compose_dummy'].format(
                    imageDigest=imageDigest,
                    dependsOn=""
                )

            dockerfile = f'FROM {image}\n'
            print(dockerfile, file=open(imageDigest, 'w'))

        chdir('..')
        return dummies

    def _writeExternalBundles(self, output_dir: str, externals: dict) -> None:
        """
        Create a uniquely identifiable folder per external component and write:
          - external_components/<id>/externals.json  (single external only)
          - external_components/<id>/README.md       (how to connect)
          - external_components/<id>/attach_linux.sh (IP/MAC bring-up)
          - external_components/<id>/scion/*         (topology.json + keys if discoverable)
        """
        out = Path(output_dir).resolve()
        base = out / "external_components"
        base.mkdir(parents=True, exist_ok=True)

        all_topologies = list(out.rglob("topology.json"))
        all_keys_dirs = [p for p in out.rglob("keys") if p.is_dir()]

        for ext_name, ext in externals.items():
            name = getattr(ext, "name", ext_name)
            role = getattr(ext, "role", "unknown")
            asn = getattr(ext, "asn", -1)
            impl_type = getattr(ext, "impl_type", "generic")
            interfaces = getattr(ext, "interfaces", [])

            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            folder_name = f"{name}__asn{asn}__{ts}"
            comp_dir = base / folder_name
            comp_dir.mkdir(parents=True, exist_ok=True)

            ext_dict = {
                "name": name,
                "role": role,
                "asn": asn,
                "impl_type": impl_type,
                "interfaces": [
                    {
                        "name": getattr(i, "name", ""),
                        "network": getattr(i, "network", ""),
                        "ip": getattr(i, "ip", ""),
                        "mac": getattr(i, "mac", ""),
                    }
                    for i in interfaces
                ],
                "scion": getattr(ext, "scion", {}) or {},
            }
            with open(comp_dir / "externals.json", "w", encoding="utf-8") as f:
                json.dump({name: ext_dict}, f, indent=2)

            lines = [
                "#!/bin/bash",
                "set -euo pipefail",
                "",
                f"# External component: {name} (role={role}, asn={asn}, impl={impl_type})",
                "# Usage:",
                "#   sudo IFACE=<your-physical-or-tap-interface> ./attach_linux.sh",
                "",
                'IFACE="${IFACE:-}"',
                'if [ -z "$IFACE" ]; then',
                '  echo "ERROR: Set IFACE, e.g.: sudo IFACE=eth1 ./attach_linux.sh" >&2',
                "  exit 1",
                "fi",
                "",
                "echo \"Bringing up $IFACE for external component...\"",
                "ip link set \"$IFACE\" up",
                "",
            ]

            for i in interfaces:
                iname = getattr(i, "name", "")
                ip = getattr(i, "ip", "")
                mac = getattr(i, "mac", "")
                net = getattr(i, "network", "")

                lines += [f"# Interface {iname} -> SEED network '{net}'"]
                if mac:
                    lines += [f"ip link set dev \"$IFACE\" address {mac}"]
                if ip:
                    lines += [
                        f"ip addr flush dev \"$IFACE\" || true",
                        f"ip addr add {ip} dev \"$IFACE\"",
                    ]
                lines += [""]

            lines += [
                "ip addr show dev \"$IFACE\"",
                "echo \"OK. Now connect this interface into your hardware/standalone emulation fabric (bridge/tap).\"",
                "",
            ]

            attach_path = comp_dir / "attach_linux.sh"
            attach_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            try:
                attach_path.chmod(0o755)
            except Exception:
                pass

            readme = [
                f"# External Component Bundle: {name}",
                "",
                f"- role: `{role}`",
                f"- asn: `{asn}`",
                f"- impl_type: `{impl_type}`",
                "",
                "## What this bundle is",
                "This folder is generated by SEED to prepare connecting an external hardware/standalone emulation node",
                "(e.g., NetFPGA/P4 switch environment) to a SEED topology.",
                "",
                "## How to use (operator steps)",
                "1) Identify the host interface (or TAP) that connects to your hardware/standalone emulation.",
                "2) Run the provided Linux script to set MAC/IP and bring the interface up:",
                "",
                "```bash",
                "sudo IFACE=<iface> ./attach_linux.sh",
                "```",
                "",
                "3) Connect that interface into your testbed fabric (Linux bridge / switch port / tap).",
                "",
                "## Files",
                "- `externals.json`: machine-readable definition of this external component",
                "- `attach_linux.sh`: prepared interface config commands",
                "- `scion/`: if SCION artifacts are discoverable in SEED output, they are copied here",
                "",
            ]
            (comp_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

            scion_dir = comp_dir / "scion"
            scion_dir.mkdir(parents=True, exist_ok=True)
            copied = False

            scion_obj = getattr(ext, "scion", {}) or {}
            if isinstance(scion_obj, dict) and scion_obj:
                topo = scion_obj.get("topology_json")
                if isinstance(topo, dict):
                    (scion_dir / "topology.json").write_text(json.dumps(topo, indent=2) + "\n", encoding="utf-8")
                    copied = True

            for topo_path in all_topologies:
                p = str(topo_path).lower()
                if (f"as{asn}" in p) or (name.lower() in p):
                    try:
                        data = topo_path.read_text(encoding="utf-8")
                        (scion_dir / "topology.json").write_text(data, encoding="utf-8")
                        copied = True
                        break
                    except Exception:
                        pass

            for keys_dir in all_keys_dirs:
                p = str(keys_dir).lower()
                if (f"as{asn}" in p) or (name.lower() in p):
                    try:
                        target = scion_dir / "keys"
                        target.mkdir(parents=True, exist_ok=True)
                        for fp in keys_dir.rglob("*"):
                            if fp.is_file():
                                rel = fp.relative_to(keys_dir)
                                dest = target / rel
                                dest.parent.mkdir(parents=True, exist_ok=True)
                                dest.write_bytes(fp.read_bytes())
                        copied = True
                        break
                    except Exception:
                        pass

            if not copied:
                (scion_dir / "README.txt").write_text(
                    "SCION artifacts not found in this output. When compiling a SCION topology, "
                    "SEED will copy topology.json and keys here (best-effort discovery).\n",
                    encoding="utf-8",
                )

        self._log(f"Wrote external component bundles to: {base}")

    def _doCompile(self, emulator: Emulator):
        registry = emulator.getRegistry()
        outdir = str(Path(".").resolve())

        # Task 2 bundles
        externals = getattr(emulator, "getExternalComponents", lambda: {})()
        self._log(f"External components detected: {list(externals.keys())}")
        self._writeExternalBundles(outdir, externals)

        # Task 3 (External Emulations)
        ext_specs = list(getattr(emulator, "getExternalEmulations", lambda: [])() or [])
        if ext_specs:
            self._log(f"External emulations detected: {[s.name for s in ext_specs]}")
            self._writeExternalEmuBundles(outdir, ext_specs)
            for s in ext_specs:
                self.__services += self._compileExternalEmuService(emulator, s)

        self._groupSoftware(emulator)

        for ((scope, type, name), obj) in registry.getAll().items():
            if type == 'net':
                self._log(f'creating network: {scope}/{name}...')
                self.__networks += self._compileNet(obj)

        for ((scope, type, name), obj) in registry.getAll().items():
            if type == 'rnode':
                self._log(f'compiling router node {name} for as{scope}...')
                self.__services += self._compileNode(obj)
            elif type == 'csnode':
                self._log(f'compiling control service node {name} for as{scope}...')
                self.__services += self._compileNode(obj)
            elif type == 'hnode':
                self._log(f'compiling host node {name} for as{scope}...')
                self.__services += self._compileNode(obj)
            elif type == 'rs':
                self._log(f'compiling rs node for {name}...')
                self.__services += self._compileNode(obj)
            elif type == 'snode':
                self._log(f'compiling service node {name}...')
                self.__services += self._compileNode(obj)

        if self.__internet_map_enabled:
            self._log('enabling seedemu-internet-map...')
            self.attachInternetMap(port_forwarding="{}:8080/tcp".format(self.__internet_map_port))

        if self.__ether_view_enabled:
            self._log('enabling seedemu-ether-view...')
            self.__services += DockerCompilerFileTemplates['seedemu_ether_view'].format(
                clientImage=SEEDEMU_ETHER_VIEW_IMAGE,
                clientPort=self.__ether_view_port
            )
            self.__services += '\n'

        self.__services += self.__custom_services

        local_images = ''
        for (image, _) in self.__images.values():
            if image.getName() not in self._used_images or not image.isLocal():
                continue
            local_images += DockerCompilerFileTemplates['local_image'].format(
                imageName=image.getName(),
                dirName=image.getDirName()
            )

        toplevelvolumes = self._computeComposeTopLvlVolumes()

        self._log('creating docker-compose.yml...')
        print(
            DockerCompilerFileTemplates['compose'].format(
                services=self.__services,
                networks=self.__networks,
                volumes=toplevelvolumes,
                dummies=local_images + self._makeDummies(),
            ),
            file=open('docker-compose.yml', 'w')
        )

        self.generateEnvFile(Scope(ScopeTier.Global), '')

    def _computeComposeTopLvlVolumes(self) -> str:
        toplevelvolumes = ''
        if len(topvols := self._getVolumes()) > 0:
            hit = False
            for v in topvols:
                v.mode = 'toplevel'

            for v in [vv for vv in topvols if vv.asDict()['type'] == 'volume']:
                hit = True
                toplevelvolumes += '  {}:\n'.format(v.asDict()['source'])
                lines = dump(v).rstrip('\n').split('\n')
                toplevelvolumes += '\n'.join(
                    map(lambda x: '        ' if x[0] != 0 else '        ' + x[1] if x[1] != '' else '', enumerate(lines))
                )
                toplevelvolumes += '\n'

            if hit:
                toplevelvolumes = 'volumes:\n' + toplevelvolumes
        return toplevelvolumes

    def attachInternetMap(self, asn: int = -1, net: str = '', ip_address: str = '',
                          port_forwarding: str = '', env: list = [],
                          show_on_map=False, node_name='seedemu_internet_map') -> "Docker":
        self._log(f'attaching the Internet Map container to {asn}:{net}')
        self.__internet_map_enabled = False
        self.attachCustomContainer(
            DockerCompilerFileTemplates['seedemu_internet_map'].format(
                serviceName=node_name,
                clientImage=SEEDEMU_INTERNET_MAP_IMAGE,
                containerName=node_name,
            ),
            asn=asn, net=net, ip_address=ip_address, port_forwarding=port_forwarding,
            env=env, show_on_map=show_on_map, node_name=node_name
        )
        return self

    def attachCustomContainer(self, compose_entry: str, asn: int = -1, net: str = '',
                              ip_address: str = '', port_forwarding: str = '', env: list = [],
                              show_on_map=False, node_name: str = 'unnamed') -> "Docker":
        self._log(f'attaching an existing container to {asn}:{net}')
        self.__custom_services += compose_entry

        if port_forwarding != '':
            self.__custom_services += DockerCompilerFileTemplates['port_forwarding_entry'].format(
                port_forwarding_field=port_forwarding
            )

        if env:
            self.__custom_services += DockerCompilerFileTemplates['environment_variable_entry']
            field_name = DockerCompilerFileTemplates['environment_variable_entry']
            leading_spaces = len(field_name) - len(field_name.lstrip())
            for e in env:
                self.__custom_services += '{}- {}\n'.format(' ' * (leading_spaces + 4), e)

        if asn < 0:
            self.__custom_services += '\n'
        else:
            net_prefix = self._contextToPrefix(asn, 'net')
            real_netname = '{}{}'.format(net_prefix, net)

            ipv4_address_entry = '' if ip_address == '' else 'ipv4_address: {}'.format(ip_address)

            self.__custom_services += DockerCompilerFileTemplates['network_entry'].format(
                network_name_field=real_netname,
                ipv4_address_field=ipv4_address_entry
            )
            self.__custom_services += '\n'

        if show_on_map:
            self.__custom_services += DockerCompilerFileTemplates['custom_compose_label_meta'].format(
                labelList=self._getCustomNodeMeta(asn, node_name, net, ip_address)
            )
            self.__custom_services += '\n'

        return self

    def _getCustomNodeMeta(self, asn: int = -1, node_name: str = '', net: str = '', ip_address: str = '') -> str:
        labels = ''

        if asn > -1:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='asn', value=asn)
        if node_name:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='nodename', value=node_name)

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='role', value='Host')

        if net:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='net.0.name', value=net)
        if ip_address:
            labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='net.0.address', value=ip_address)

        labels += DockerCompilerFileTemplates['compose_label_meta'].format(key='custom', value='custom')
        return labels

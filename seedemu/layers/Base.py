from __future__ import annotations
from seedemu.core import AutonomousSystem, InternetExchange, AddressAssignmentConstraint, DEFAULT_IPV6_ROOT_PREFIX, Ipv6Addressing, Node, Graphable, Emulator, Layer, normalizeAddressList, normalizePrefix
from ipaddress import IPv6Network
from typing import Dict, List
from seedemu.options.Sysctl import SysctlOpts
BaseFileTemplates: Dict[str, str] = {}

BaseFileTemplates["interface_setup_script"] = r"""\
#!/bin/bash
cidr_to_net() {
    case "$1" in
        *:*) return ;;
        *) ipcalc -n "$1" | sed -E -n 's/^Network: +([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2}) +.*/\1/p' ;;
    esac
}

lookup_ifinfo() {
    local cidr="$1"
    local line net
    line="`awk -F'|' -v cidr="$cidr" '$2 == cidr { print; exit }' /ifinfo.txt`"
    if [ ! -z "$line" ]; then
        echo "$line"
        return
    fi
    net="`cidr_to_net "$cidr"`"
    if [ ! -z "$net" ]; then
        line="`awk -F'|' -v cidr="$net" '$2 == cidr { print; exit }' /ifinfo.txt`"
        if [ ! -z "$line" ]; then
            echo "$line"
            return
        fi
        grep -F "$net" /ifinfo.txt | head -n1
    fi
}

parse_ifinfo() {
    local line="$1"
    if [[ "$line" == *"|"* ]]; then
        new_ifname="`cut -d'|' -f1 <<< "$line"`"
        latency="`cut -d'|' -f3 <<< "$line"`"
        bw="`cut -d'|' -f4 <<< "$line"`"
        loss="`cut -d'|' -f5 <<< "$line"`"
    else
        new_ifname="`cut -d: -f1 <<< "$line"`"
        latency="`cut -d: -f3 <<< "$line"`"
        bw="`cut -d: -f4 <<< "$line"`"
        loss="`cut -d: -f5 <<< "$line"`"
    fi
}

ip -j addr | jq -cr '.[]' | while read -r iface; do
    ifname="`jq -cr '.ifname' <<< "$iface"`"
    line=""
    while read -r iaddr; do
        addr="`jq -cr '"\(.local)/\(.prefixlen)"' <<< "$iaddr"`"
        line="`lookup_ifinfo "$addr"`"
        [ ! -z "$line" ] && break
    done < <(jq -cr '.addr_info[]?' <<< "$iface")
    [ -z "$line" ] && continue
    parse_ifinfo "$line"
    [ -z "$new_ifname" ] && continue
    [ "$bw" = 0 ] && bw=1000000000000
    if [ "$ifname" != "$new_ifname" ]; then
        sysctl -w net.ipv6.conf.all.keep_addr_on_down=1 > /dev/null 2>&1
        sysctl -w net.ipv6.conf.default.keep_addr_on_down=1 > /dev/null 2>&1
        sysctl -w "net.ipv6.conf.${ifname}.keep_addr_on_down=1" > /dev/null 2>&1
        ip li set "$ifname" down
        ip li set "$ifname" name "$new_ifname"
        ip li set "$new_ifname" up
    fi
    tc qdisc add dev "$new_ifname" root handle 1:0 tbf rate "${bw}bit" buffer 1000000 limit 1000
    tc qdisc add dev "$new_ifname" parent 1:0 handle 10: netem delay "${latency}ms" loss "${loss}%"
done
"""


class Base(Layer, Graphable):
    """!
    @brief The base layer.
    """

    __ases: Dict[int, AutonomousSystem]
    __ixes: Dict[int, InternetExchange]
    __ipv6_addressing: Ipv6Addressing

    __name_servers: List[str]

    def getAvailableOptions(self):
        from seedemu.core.OptionRegistry import OptionRegistry
        opt_keys = [ o.fullname() for o in SysctlOpts().components_recursive()]
        return [OptionRegistry().getOption(o) for o in opt_keys]

    def __init__(self, enableIpv6: bool = False, ipv6RootPrefix: str = DEFAULT_IPV6_ROOT_PREFIX):
        """!
        @brief Base layer constructor.
        """
        super().__init__()
        self.__ases = {}
        self.__ixes = {}
        self.__ipv6_addressing = Ipv6Addressing(ipv6RootPrefix) if enableIpv6 else None
        self.__name_servers = []

    def getName(self) -> str:
        return "Base"
    
    # the base layer is the wrong place for this, since subsequent layers
    # might add further features to ASes
    '''
    def applyFeaturesToNodes(self, _as: AutonomousSystem, emulator: Emulator):
        """!
        """
        #@note 'use_envsubst' is a special feature which can be set, to turn all the variables that are set at AS scope
        #   into runtime variables(the default is false -> hardcoded buildtime only variables ).
        #useenvsubst='use_envsubst' in _as.getFeatures()
        reg = emulator.getRegistry()
        all_nodes = [ obj for (scope,typ,name),obj  in reg.getAll( ) if scope==str(_as.getAsn()) and typ in ['rnode','hnode','csnode','rsnode'] ]

        for k,v in self.getFeatures():
           for node in all_nodes:
                node.setCustomEnv2(k,v,scope=ScopeTier.AS,
                                    use_envsubst=_as.useEnvsubst(k) or node.getCustomEnv('use_envsubst')=='true')
        pass
    '''

    def configure(self, emulator: Emulator):
        
        self._log('registering nodes...')
        for asobj in self.__ases.values():
            if len(asobj.getNameServers()) == 0:
                asobj.setNameServers(self.__name_servers)

            asobj.registerNodes(emulator)
            asobj.inheritOptions(emulator)
            

        self._log('setting up internet exchanges...')
        for ix in self.__ixes.values(): ix.configure(emulator)

        self._log('setting up autonomous systems...')
        for asobj in self.__ases.values(): asobj.configure(emulator)
        super().configure(emulator)

    def render(self, emulator: Emulator) -> None:
        for ((scope, type, name), obj) in emulator.getRegistry().getAll().items():

            if type not in ['rs', 'rnode', 'hnode', 'csnode']:
                continue

            node: Node = obj
            # Note: service network interface might be added later ... 
            ifinfo = ''
            for iface in node.getInterfaces():
                net = iface.getNet()
                [l, b, d] = iface.getLinkProperties()
                if iface.getAddress() is not None:
                    ifinfo += '{}|{}/{}|{}|{}|{}\n'.format(net.getName(), iface.getAddress(), net.getPrefix().prefixlen, l, b, d)
                ifinfo += '{}|{}|{}|{}|{}\n'.format(net.getName(), net.getPrefix(), l, b, d)
                if iface.hasIpv6Address():
                    ifinfo += '{}|{}/{}|{}|{}|{}\n'.format(net.getName(), iface.getIpv6Address(), net.getIpv6Prefix().prefixlen, l, b, d)

            node.setFile('/ifinfo.txt', ifinfo)
            node.setFile('/interface_setup', BaseFileTemplates['interface_setup_script'])
            node.insertStartCommand(0, '/interface_setup')
            node.insertStartCommand(0, 'chmod +x /interface_setup')

    def setNameServers(self, servers: List[str]) -> Base:
        """!
        @brief set recursive name servers to use on all nodes. Can be override
        by calling setNameServers at AS level or node level.

        @param servers list of IP addresses of recursive name servers.

        @returns self, for chaining API calls.
        """
        self.__name_servers = normalizeAddressList(servers)

        return self

    def getNameServers(self) -> List[str]:
        """!
        @brief get configured recursive name servers for all nodes.

        @returns list of IP addresses of recursive name servers
        """
        return self.__name_servers

    def enableIpv6(self, rootPrefix: str = DEFAULT_IPV6_ROOT_PREFIX) -> Base:
        """!
        @brief Enable optional IPv6 addressing for new ASes and IXes.

        @param rootPrefix root IPv6 prefix. Defaults to 2000::/12.

        @returns self, for chaining API calls.
        """
        if self.__ipv6_addressing is not None:
            assert self.__ipv6_addressing.getRootPrefix() == IPv6Network(normalizePrefix(rootPrefix)), (
                "IPv6 is already enabled with root prefix {}".format(self.__ipv6_addressing.getRootPrefix())
            )
            return self

        self.__ipv6_addressing = Ipv6Addressing(rootPrefix)
        for ix in self.__ixes.values():
            net = ix.getPeeringLan()
            if net.hasIpv6Prefix() and net.getIpv6PrefixIntent() != "auto":
                self.__ipv6_addressing.claimPrefix(net.getIpv6Prefix())
        for asobj in self.__ases.values():
            asobj.setIpv6Addressing(self.__ipv6_addressing)
        for ixid, ix in self.__ixes.items():
            net = ix.getPeeringLan()
            if net.getIpv6PrefixIntent() == "auto" and not net.hasIpv6Prefix():
                net.setIpv6Prefix(self.__ipv6_addressing.assignIxPrefix(ixid))
        return self

    def isIpv6Enabled(self) -> bool:
        """!
        @brief Check if optional IPv6 addressing is enabled.

        @returns true if IPv6 is enabled.
        """
        return self.__ipv6_addressing is not None

    def getIpv6Addressing(self) -> Ipv6Addressing:
        """!
        @brief Get the optional IPv6 addressing allocator.

        @returns allocator, or None when IPv6 is disabled.
        """
        return self.__ipv6_addressing

    def getIpv6RootPrefix(self):
        """!
        @brief Get the IPv6 root prefix, if optional IPv6 is enabled.

        @returns IPv6 root prefix, or None when IPv6 is disabled.
        """
        return self.__ipv6_addressing.getRootPrefix() if self.__ipv6_addressing is not None else None

    def getIpv6ReservedPrefixes(self) -> List:
        """!
        @brief Get IPv6 prefixes reserved by the automatic allocator.

        @returns list of IPv6 prefixes, or an empty list when IPv6 is disabled.
        """
        return self.__ipv6_addressing.getReservedPrefixes() if self.__ipv6_addressing is not None else []

    def createAutonomousSystem(self, asn: int) -> AutonomousSystem:
        """!
        @brief Create a new AutonomousSystem.

        @param asn ASN of the new AS.
        @returns created AS.
        @throws AssertionError if asn exists.
        """
        assert asn not in self.__ases, "as{} already exist.".format(asn)
        self.__ases[asn] = AutonomousSystem(asn, ipv6Addressing=self.__ipv6_addressing)
        return self.__ases[asn]

    def getAutonomousSystem(self, asn: int) -> AutonomousSystem:
        """!
        @brief Create an existing AutonomousSystem.

        @param asn ASN of the AS.
        @returns AS.
        @throws AssertionError if asn does not exist.
        """
        assert asn in self.__ases, "as{} does not exist.".format(asn)
        return self.__ases[asn]

    def setAutonomousSystem(self, asObject: AutonomousSystem):
        """!
        @brief Set AS to an existing AS object.

        @param asObject AS object.
        """
        asn = asObject.getAsn()
        if self.__ipv6_addressing is not None:
            asObject.setIpv6Addressing(self.__ipv6_addressing)
        self.__ases[asn] = asObject

    def createInternetExchange(self, asn: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None, create_rs=True, rsAddress = None, ipv6Prefix = "auto", rsIpv6Address = "auto") -> InternetExchange:
        """!
        @brief Create a new InternetExchange.

        @param asn ASN of the new IX.
        @param prefix (optional) prefix of the IX peering LAN.
        @param aac (optional) Address assignment constraint.
        @param create_rs (optional) create route server node for the IX or not.
        @param rsAddress (optional) specific address for the route server.
        @returns created IX.
        @throws AssertionError if IX exists.
        """
        assert asn not in self.__ixes, "ix{} already exist.".format(asn)
        ix_ipv6_prefix = None
        if ipv6Prefix is not None:
            if ipv6Prefix == "auto":
                ix_ipv6_prefix = self.__ipv6_addressing.assignIxPrefix(asn) if self.__ipv6_addressing is not None else None
                ix_ipv6_intent = "auto"
            else:
                ix_ipv6_prefix = normalizePrefix(ipv6Prefix)
                ix_ipv6_intent = "explicit"
                if self.__ipv6_addressing is not None:
                    self.__ipv6_addressing.claimPrefix(ix_ipv6_prefix)
        else:
            ix_ipv6_intent = None
        self.__ixes[asn] = InternetExchange(asn, prefix, aac, create_rs, rsAddress, ix_ipv6_prefix, rsIpv6Address, ix_ipv6_intent)
        return self.__ixes[asn]

    def getInternetExchange(self, asn: int) -> InternetExchange:
        """!
        @brief Get an existing InternetExchange.

        @param asn ASN of the IX.
        @returns InternetExchange.
        @throws AssertionError if ix does not exist.
        """
        assert asn in self.__ixes, "ix{} does not exist.".format(asn)
        return self.__ixes[asn]

    def setInternetExchange(self, ixObject: InternetExchange):
        """!
        @brief Set IX to an existing IX object.

        @param ixObject IX object.
        """
        asn = ixObject.getId()
        if self.__ipv6_addressing is not None:
            net = ixObject.getPeeringLan()
            if net.hasIpv6Prefix() and net.getIpv6PrefixIntent() != "auto":
                self.__ipv6_addressing.claimPrefix(net.getIpv6Prefix())
            if net.getIpv6PrefixIntent() == "auto" and not net.hasIpv6Prefix():
                net.setIpv6Prefix(self.__ipv6_addressing.assignIxPrefix(asn))
        self.__ixes[asn] = ixObject

    def getAsns(self) -> List[int]:
        """!
        @brief Get list of ASNs.

        @returns List of ASNs.
        """
        return list(self.__ases.keys())

    def getInternetExchangeIds(self) -> List[int]:
        """!
        @brief Get list of IX IDs.

        @returns List of IX IDs.
        """
        return list(self.__ixes.keys())

    def getNodesByName(self, name:str) -> List[Node]:
        """!
        @brief Get list of Nodes by name.

        @returns List of Nodes whose name is start with input_name.
        """
        nodes = []
        for _as in self.__ases.values():
            for host_name in _as.getHosts():
                if host_name.startswith(name):
                    nodes.append(_as.getHost(host_name))
        return nodes

    def getNodeByAsnAndName(self, asn:id, name:str) -> Node:
        _as = self.__ases[asn]
        node = _as.getHost(name)
        return node

    def _doCreateGraphs(self, emulator: Emulator):
        graph = self._addGraph('Layer 2 Connections', False)
        for asobj in self.__ases.values():
            asobj.createGraphs(emulator)
            asgraph = asobj.getGraph('AS{}: Layer 2 Connections'.format(asobj.getAsn()))
            graph.copy(asgraph)

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'BaseLayer:\n'

        indent += 4
        out += ' ' * indent
        out += 'AutonomousSystems:\n'
        for _as in self.__ases.values():
            out += _as.print(indent + 4)

        out += ' ' * indent
        out += 'InternetExchanges:\n'
        for _as in self.__ixes.values():
            out += _as.print(indent + 4)

        return out

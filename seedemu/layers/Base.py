from __future__ import annotations
from seedemu.core import AutonomousSystem, InternetExchange, AddressAssignmentConstraint, Node, Graphable, Emulator, Layer
from typing import Dict, List

BaseFileTemplates: Dict[str, str] = {}

BaseFileTemplates["interface_setup_script"] = """\
#!/bin/bash
cidr_to_net() {
    ipcalc -n "$1" | sed -E -n 's/^Network: +([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\/[0-9]{1,2}) +.*/\\1/p'
}

ip -j addr | jq -cr '.[]' | while read -r iface; do {
    ifname="`jq -cr '.ifname' <<< "$iface"`"
    jq -cr '.addr_info[]' <<< "$iface" | while read -r iaddr; do {
        addr="`jq -cr '"\(.local)/\(.prefixlen)"' <<< "$iaddr"`"
        net="`cidr_to_net "$addr"`"
        [ -z "$net" ] && continue
        line="`grep "$net" < ifinfo.txt`"
        new_ifname="`cut -d: -f1 <<< "$line"`"
        latency="`cut -d: -f3 <<< "$line"`"
        bw="`cut -d: -f4 <<< "$line"`"
        [ "$bw" = 0 ] && bw=1000000000000
        loss="`cut -d: -f5 <<< "$line"`"
        [ ! -z "$new_ifname" ] && {
            ip li set "$ifname" down
            ip li set "$ifname" name "$new_ifname"
            ip li set "$new_ifname" up
            tc qdisc add dev "$new_ifname" root handle 1:0 tbf rate "${bw}bit" buffer 1000000 limit 1000
            tc qdisc add dev "$new_ifname" parent 1:0 handle 10: netem delay "${latency}ms" loss "${loss}%"
        }
    }; done
}; done
"""

class Base(Layer, Graphable):
    """!
    @brief The base layer.
    """

    __ases: Dict[int, AutonomousSystem]
    __ixes: Dict[int, InternetExchange]

    __name_servers: List[str]

    def __init__(self):
        """!
        @brief Base layer constructor.
        """
        super().__init__()
        self.__ases = {}
        self.__ixes = {}
        self.__name_servers = []

    def getName(self) -> str:
        return "Base"

    def configure(self, emulator: Emulator):
        self._log('registering nodes...')
        for asobj in self.__ases.values():
            if len(asobj.getNameServers()) == 0:
                asobj.setNameServers(self.__name_servers)

            asobj.registerNodes(emulator)

        self._log('setting up internet exchanges...')
        for ix in self.__ixes.values(): ix.configure(emulator)

        self._log('setting up autonomous systems...')
        for asobj in self.__ases.values(): asobj.configure(emulator)

    def render(self, emulator: Emulator) -> None:
        for ((scope, type, name), obj) in emulator.getRegistry().getAll().items():

            if not (type == 'rs' or type == 'rnode' or type == 'hnode'):
                continue
            
            node: Node = obj

            ifinfo = ''
            for iface in node.getInterfaces():
                net = iface.getNet()
                [l, b, d] = iface.getLinkProperties()
                ifinfo += '{}:{}:{}:{}:{}\n'.format(net.getName(), net.getPrefix(), l, b, d)

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
        self.__name_servers = servers

        return self

    def getNameServers(self) -> List[str]:
        """!
        @brief get configured recursive name servers for all nodes.

        @returns list of IP addresses of recursive name servers
        """
        return self.__name_servers

    def createAutonomousSystem(self, asn: int) -> AutonomousSystem:
        """!
        @brief Create a new AutonomousSystem.

        @param asn ASN of the new AS.
        @returns created AS.
        @throws AssertionError if asn exists.
        """
        assert asn not in self.__ases, "as{} already exist.".format(asn)
        self.__ases[asn] = AutonomousSystem(asn)
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
        self.__ases[asn] = asObject

    def createInternetExchange(self, asn: int, prefix: str = "auto", aac: AddressAssignmentConstraint = None) -> InternetExchange:
        """!
        @brief Create a new InternetExchange.

        @param asn ASN of the new IX.
        @param prefix (optional) prefix of the IX peering LAN.
        @param aac (optional) Address assigment constraint.
        @returns created IX.
        @throws AssertionError if IX exists.
        """
        assert asn not in self.__ixes, "ix{} already exist.".format(asn)
        self.__ixes[asn] = InternetExchange(asn, prefix, aac)
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
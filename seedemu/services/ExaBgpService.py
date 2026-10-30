from __future__ import annotations

from ipaddress import ip_network
from typing import Dict, List, Optional, Tuple

from seedemu.core import Emulator, Network, Node, Router, ScopedRegistry, Server, Service
from seedemu.layers._bgp_metadata import (
    BGP_COMMUNITY_CUSTOMER,
    BGP_COMMUNITY_PEER,
    BGP_COMMUNITY_PROVIDER,
    install_router_bgp_session,
)


ExaBgpFileTemplates: Dict[str, str] = {}

ExaBgpFileTemplates["config"] = """\
process manual-control {{
  run /bin/sh -c "mkdir -p /run/exabgp; mkfifo /run/exabgp/manual.in 2>/dev/null || true; chmod 666 /run/exabgp/manual.in; tail -f /run/exabgp/manual.in";
  encoder text;
}}

{neighbor_blocks}
"""

ExaBgpFileTemplates["static_block"] = """\
  static {{
{routes}
  }}
"""


class ExaBgpServer(Server):
    """!
    @brief ExaBGP external BGP speaker installed through Service + Binding.
    """

    __emulator: Optional[Emulator]
    __local_asn: int
    __announce_prefixes: List[str]
    __peers: List[Dict[str, object]]
    __resolved_peers: List[Tuple[Dict[str, object], Router, str, str]]

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.__local_asn = 65010
        self.__announce_prefixes = []
        self.__peers = []
        self.__resolved_peers = []
        self.setDisplayName("ExaBGP Control Plane Speaker")

    def bind(self, emulator: Emulator):
        self.__emulator = emulator

    def setLocalAsn(self, asn: int) -> "ExaBgpServer":
        self.__local_asn = int(asn)
        return self

    def addAnnouncement(self, prefix: str) -> "ExaBgpServer":
        network = ip_network(prefix, strict=False)
        assert network.version == 4, "ExaBgpService foundation currently supports IPv4 announcements only"
        self.__announce_prefixes.append(str(network))
        return self

    def attachToRouter(self, router_name: str, router_asn: Optional[int] = None) -> "ExaBgpServer":
        self.__peers = []
        self.addPeerByRouter(router_name, router_asn=router_asn)
        return self

    def addPeer(
        self,
        ix: int,
        peer_asn: Optional[int] = None,
        session_name: Optional[str] = None,
        router_relationship: str = "customer",
        router_asn: Optional[int] = None,
    ) -> "ExaBgpServer":
        if isinstance(ix, str):
            return self.addPeerByRouter(
                ix,
                router_asn=router_asn if router_asn is not None else peer_asn,
                session_name=session_name,
                router_relationship=router_relationship,
            )

        assert peer_asn is not None, "peer_asn is required for IX-based ExaBGP peering"
        relationship = self._normalize_relationship(router_relationship)
        self.__peers.append(
            {
                "type": "ix",
                "ix": int(ix),
                "peer_asn": int(peer_asn),
                "session_name": str(session_name).strip() if session_name is not None else None,
                "router_relationship": relationship,
            }
        )
        return self

    def addPeerByRouter(
        self,
        router_name: str,
        router_asn: Optional[int] = None,
        session_name: Optional[str] = None,
        router_relationship: str = "customer",
    ) -> "ExaBgpServer":
        relationship = self._normalize_relationship(router_relationship)
        self.__peers.append(
            {
                "type": "router",
                "router_name": str(router_name),
                "router_asn": int(router_asn) if router_asn is not None else None,
                "session_name": str(session_name).strip() if session_name is not None else None,
                "router_relationship": relationship,
            }
        )
        return self

    def _normalize_relationship(self, router_relationship: str) -> str:
        relationship = str(router_relationship or "customer").strip().lower() or "customer"
        if relationship not in {"customer", "peer", "provider", "unfiltered"}:
            raise ValueError("unsupported router relationship: {}".format(router_relationship))
        return relationship

    def _relationship_params(self, relationship: str) -> Tuple[Optional[str], Optional[int], str]:
        if relationship == "customer":
            return BGP_COMMUNITY_CUSTOMER, 30, "all"
        if relationship == "peer":
            return BGP_COMMUNITY_PEER, 20, "local_and_customer"
        if relationship == "provider":
            return BGP_COMMUNITY_PROVIDER, 10, "local_and_customer"
        return None, None, "all"

    def _resolve_ix_net(self, ix: int) -> Network:
        assert self.__emulator is not None, "ExaBgpServer not bound to emulator"
        ix_scope = ScopedRegistry("ix", self.__emulator.getRegistry())
        ix_name = "ix{}".format(ix)
        assert ix_scope.has("net", ix_name), "IX{} not found for ExaBGP peer".format(ix)
        return ix_scope.get("net", ix_name)

    def _resolve_ix_peer(self, node: Node, peer: Dict[str, object]) -> Tuple[Router, str, str]:
        assert self.__emulator is not None, "ExaBgpServer not bound to emulator"
        ix = int(peer["ix"])
        peer_asn = int(peer["peer_asn"])
        ix_net = self._resolve_ix_net(ix)

        local_address: Optional[str] = None
        for iface in node.getInterfaces():
            if iface.getNet() == ix_net:
                local_address = str(iface.getAddress())
                break

        assert local_address is not None, (
            "ExaBGP node as{}/{} is not connected to IX{}".format(node.getAsn(), node.getName(), ix)
        )

        scope = ScopedRegistry(str(peer_asn), self.__emulator.getRegistry())
        candidates: List[Tuple[Router, str]] = []
        for router in scope.getByType("rnode"):
            assert isinstance(router, Router)
            for iface in router.getInterfaces():
                if iface.getNet() == ix_net:
                    candidates.append((router, str(iface.getAddress())))
                    break

        assert candidates, "cannot resolve ExaBGP peer: AS{} is not connected to IX{}".format(peer_asn, ix)
        assert len(candidates) == 1, (
            "cannot resolve ExaBGP peer: AS{} has multiple routers on IX{}: {}. "
            "Use addPeerByRouter(...) to choose one explicitly."
        ).format(peer_asn, ix, ", ".join(router.getName() for router, _addr in candidates))

        router, peer_address = candidates[0]
        return router, local_address, peer_address

    def _resolve_router_peer(self, node: Node, peer: Dict[str, object]) -> Tuple[Router, str, str]:
        assert self.__emulator is not None, "ExaBgpServer not bound to emulator"
        router_asn = int(peer["router_asn"]) if peer.get("router_asn") is not None else node.getAsn()
        scope = ScopedRegistry(str(router_asn), self.__emulator.getRegistry())
        router_name = str(peer["router_name"])
        assert scope.has("rnode", router_name), "router as{}/{} not found for ExaBGP peer".format(router_asn, router_name)
        router = scope.get("rnode", router_name)
        assert isinstance(router, Router)

        for node_iface in node.getInterfaces():
            for router_iface in router.getInterfaces():
                if node_iface.getNet() != router_iface.getNet():
                    continue
                return router, str(node_iface.getAddress()), str(router_iface.getAddress())

        raise AssertionError(
            "ExaBGP node as{}/{} does not share a network with as{}/{}".format(
                node.getAsn(), node.getName(), router.getAsn(), router.getName()
            )
        )

    def _resolve_peer(self, node: Node, peer: Dict[str, object]) -> Tuple[Router, str, str]:
        if peer.get("type") == "ix":
            return self._resolve_ix_peer(node, peer)
        return self._resolve_router_peer(node, peer)

    def configureOnNode(self, node: Node):
        assert self.__peers, "ExaBgpServer requires at least one peer"
        if self.__resolved_peers:
            return

        for index, peer in enumerate(self.__peers):
            router, local_address, peer_address = self._resolve_peer(node, peer)
            session_name = str(peer.get("session_name") or "")
            if not session_name:
                session_name = "exabgp_{}".format(self.__local_asn)
                if len(self.__peers) > 1:
                    session_name = "{}_{}_{}".format(session_name, router.getName(), index)

            import_community, local_pref, export_policy = self._relationship_params(
                str(peer.get("router_relationship") or "customer")
            )
            install_router_bgp_session(
                router,
                {
                    "name": session_name,
                    "kind": "ebgp",
                    "local_address": peer_address,
                    "local_asn": router.getAsn(),
                    "peer_address": local_address,
                    "peer_asn": self.__local_asn,
                    "import_community": import_community,
                    "local_pref": local_pref,
                    "export_policy": export_policy,
                    "next_hop_self": True,
                    "route_server_client": False,
                },
            )
            self.__resolved_peers.append((peer, router, local_address, peer_address))

    def install(self, node: Node):
        self.configureOnNode(node)
        node.addSoftware("exabgp")

        routes = "\n".join("    route {} next-hop self;".format(prefix) for prefix in self.__announce_prefixes)
        static_block = ExaBgpFileTemplates["static_block"].format(routes=routes) if routes else ""
        neighbor_blocks: List[str] = []
        for _peer, router, local_address, peer_address in self.__resolved_peers:
            neighbor_blocks.append(
                (
                    "neighbor {peer_address} {{\n"
                    "  router-id {router_id};\n"
                    "  local-address {local_address};\n"
                    "  local-as {local_asn};\n"
                    "  peer-as {peer_asn};\n"
                    "  family {{\n"
                    "    ipv4 unicast;\n"
                    "  }}\n"
                    "  api {{\n"
                    "    processes [ manual-control ];\n"
                    "  }}\n"
                    "{static_block}"
                    "}}\n"
                ).format(
                    peer_address=peer_address,
                    router_id=local_address,
                    local_address=local_address,
                    local_asn=self.__local_asn,
                    peer_asn=router.getAsn(),
                    static_block=static_block,
                )
            )

        node.setFile(
            "/etc/exabgp/exabgp.conf",
            ExaBgpFileTemplates["config"].format(neighbor_blocks="\n".join(neighbor_blocks)),
        )
        node.appendStartCommand("mkdir -p /var/log/exabgp")
        node.appendStartCommand(
            "env exabgp.daemon.drop=false exabgp.daemon.user=root "
            "exabgp /etc/exabgp/exabgp.conf >/var/log/exabgp/exabgp.log 2>&1",
            True,
        )


class ExaBgpService(Service):
    """!
    @brief ExaBGP service layer.
    """

    __emulator: Optional[Emulator]

    def __init__(self):
        super().__init__()
        self.__emulator = None
        self.addDependency("Routing", False, False)
        self.addDependency("Ebgp", False, True)

    def _createServer(self) -> Server:
        return ExaBgpServer()

    def _doConfigure(self, node: Node, server: ExaBgpServer):
        assert self.__emulator is not None
        server.bind(self.__emulator)
        server.configureOnNode(node)
        super()._doConfigure(node, server)

    def configure(self, emulator: Emulator):
        self.__emulator = emulator
        return super().configure(emulator)

    def getName(self) -> str:
        return "ExaBgpService"

    def print(self, indent: int) -> str:
        out = ' ' * indent
        out += 'ExaBgpServiceLayer\n'
        return out

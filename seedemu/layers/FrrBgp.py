from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from seedemu.core import Emulator, Hook, Layer, Router, ScopedRegistry
from seedemu.core.enums import NetworkType

from ._bgp_metadata import (
    get_bgp_backend,
    get_bgp_sessions,
    get_ospf_interface_intents,
    has_bgp_connected_export,
    set_bgp_backend,
)


FrrBgpFileTemplates: Dict[str, str] = {}

FrrBgpFileTemplates["managed_block"] = """\
! ===== seedemu-frr-bgp begin =====
frr defaults traditional
service integrated-vtysh-config
hostname {hostname}
!
{body}
! ===== seedemu-frr-bgp end =====
"""

FrrBgpFileTemplates["start_script"] = """\
#!/bin/bash
set -e
sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons
sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons
sed -i 's/staticd=no/staticd=yes/' /etc/frr/daemons
sed -i 's/ospfd=no/ospfd=yes/' /etc/frr/daemons
service frr start
"""

FrrBgpFileTemplates["route_map_connected"] = """\
route-map RM_CONNECTED_TO_BGP permit 10
 set large-community {local_comm} additive
 set local-preference 40
!
"""

FrrBgpFileTemplates["community_lists"] = """\
bgp large-community-list standard LC_LOCAL permit {local_comm}
bgp large-community-list standard LC_CUSTOMER permit {customer_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {local_comm}
bgp large-community-list standard LC_LOCAL_OR_CUSTOMER permit {customer_comm}
!
"""

FrrBgpFileTemplates["import_route_map"] = """\
route-map {name} permit 10
 set large-community {community} additive
 set local-preference {local_pref}
!
"""

FrrBgpFileTemplates["export_route_map_local_customer"] = """\
route-map {name} permit 10
 match large-community LC_LOCAL_OR_CUSTOMER
!
route-map {name} deny 100
!
"""

FrrBgpFileTemplates["export_route_map_all"] = """\
route-map {name} permit 10
!
"""

FrrBgpFileTemplates["ospf_interface_active"] = """\
interface {interface}
 ip ospf area 0
 ip ospf hello-interval 1
 ip ospf dead-interval 2
!
"""

FrrBgpFileTemplates["ospf_interface_passive"] = """\
interface {interface}
 ip ospf area 0
 ip ospf passive
!
"""

FrrBgpFileTemplates["ospf_router"] = """\
router ospf
 ospf router-id {router_id}
!
"""


def _session_route_map_name(prefix: str, session_name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in str(session_name or "session"))
    return f"{prefix}_{safe}"[:64]


def _render_session_route_maps(local_asn: int, sessions: list[dict[str, Any]]) -> tuple[str, dict[str, dict[str, str]]]:
    body: list[str] = []
    map_names: dict[str, dict[str, str]] = {}
    community_map = {
        "LOCAL_COMM": f"{local_asn}:0:0",
        "CUSTOMER_COMM": f"{local_asn}:1:0",
        "PEER_COMM": f"{local_asn}:2:0",
        "PROVIDER_COMM": f"{local_asn}:3:0",
    }

    for session in sessions:
        name = str(session.get("name") or "session")
        import_name = ""
        export_name = ""
        import_community = str(session.get("import_community") or "").strip()
        local_pref = session.get("local_pref")
        export_policy = str(session.get("export_policy") or "all").strip()

        if import_community and local_pref is not None:
            import_name = _session_route_map_name("RM_IMPORT", name)
            body.append(
                FrrBgpFileTemplates["import_route_map"].format(
                    name=import_name,
                    community=community_map.get(import_community, import_community),
                    local_pref=int(local_pref),
                )
            )

        export_name = _session_route_map_name("RM_EXPORT", name)
        if export_policy == "local_and_customer":
            body.append(FrrBgpFileTemplates["export_route_map_local_customer"].format(name=export_name))
        else:
            body.append(FrrBgpFileTemplates["export_route_map_all"].format(name=export_name))

        map_names[name] = {"import": import_name, "export": export_name}

    return "".join(body), map_names


def _render_bgp_block(router: Router, sessions: list[dict[str, Any]]) -> str:
    local_asn = int(router.getAsn())
    loopback = str(router.getLoopbackAddress() or "")
    route_maps, map_names = _render_session_route_maps(local_asn, sessions)
    body: list[str] = [
        FrrBgpFileTemplates["community_lists"].format(
            local_comm=f"{local_asn}:0:0",
            customer_comm=f"{local_asn}:1:0",
        ),
        route_maps,
        f"router bgp {local_asn}\n",
        f" bgp router-id {loopback}\n",
        " no bgp default ipv4-unicast\n",
        " no bgp ebgp-requires-policy\n",
    ]

    seen_neighbors: set[str] = set()
    for session in sessions:
        peer_address = str(session.get("peer_address") or "").strip()
        peer_asn = int(session.get("peer_asn") or 0)
        if not peer_address or peer_asn <= 0:
            continue
        if peer_address in seen_neighbors:
            continue
        seen_neighbors.add(peer_address)
        session_name = str(session.get("name") or f"peer_{peer_asn}")
        body.append(f" neighbor {peer_address} remote-as {peer_asn}\n")
        body.append(f" neighbor {peer_address} description {session_name}\n")

    body.append(" !\n")
    body.append(" address-family ipv4 unicast\n")
    if has_bgp_connected_export(router):
        body.append("  redistribute connected route-map RM_CONNECTED_TO_BGP\n")
        body.insert(1, FrrBgpFileTemplates["route_map_connected"].format(local_comm=f"{local_asn}:0:0"))

    for session in sessions:
        peer_address = str(session.get("peer_address") or "").strip()
        if not peer_address:
            continue
        session_name = str(session.get("name") or "")
        names = map_names.get(session_name, {})
        body.append(f"  neighbor {peer_address} activate\n")
        if bool(session.get("next_hop_self")):
            body.append(f"  neighbor {peer_address} next-hop-self\n")
        import_name = str(names.get("import") or "")
        export_name = str(names.get("export") or "")
        if import_name:
            body.append(f"  neighbor {peer_address} route-map {import_name} in\n")
        if export_name:
            body.append(f"  neighbor {peer_address} route-map {export_name} out\n")
    body.append(" exit-address-family\n!\n")
    return "".join(body)


def _render_ospf_block(router: Router) -> str:
    body: list[str] = []
    intents = get_ospf_interface_intents(router)
    active_ifaces: list[str] = list(intents.get("active", []) or [])
    passive_ifaces: list[str] = list(intents.get("passive", []) or ["dummy0"])
    if not active_ifaces and not passive_ifaces:
        for iface in router.getInterfaces():
            net = iface.getNet()
            name = str(net.getName())
            if net.getType() == NetworkType.Local:
                active_ifaces.append(name)
            else:
                passive_ifaces.append(name)

    seen: set[str] = set()
    for name in active_ifaces:
        if name in seen:
            continue
        seen.add(name)
        body.append(FrrBgpFileTemplates["ospf_interface_active"].format(interface=name))
    for name in passive_ifaces:
        if name in seen:
            continue
        seen.add(name)
        body.append(FrrBgpFileTemplates["ospf_interface_passive"].format(interface=name))

    body.append(FrrBgpFileTemplates["ospf_router"].format(router_id=str(router.getLoopbackAddress() or "")))
    return "".join(body)


class FrrBgp(Layer):
    """Enable FRRouting as the BGP daemon on selected routers.

    This layer does not replace the existing Routing/Ebgp/Ibgp intent model.
    Instead it marks selected routers early, lets the regular BIRD-oriented
    layers record BGP session intent, and then renders equivalent FRR BGP
    configuration for those nodes after the BGP layers finished rendering.
    """

    __enabled: Set[Tuple[int, str]]

    def __init__(self):
        super().__init__()
        self.__enabled = set()
        self.addDependency("Routing", True, False)

    def getName(self) -> str:
        return "FrrBgp"

    def enableOn(self, asn: int, router_name: str) -> "FrrBgp":
        self.__enabled.add((int(asn), str(router_name)))
        return self

    def getEnabled(self) -> Set[Tuple[int, str]]:
        return set(self.__enabled)

    def configure(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for target in ("Ospf", "Ebgp", "Ibgp", "Mpls", "Evpn", "ExaBgpService"):
            hook_name = f"FrrBgpFinalizeOn{target}"
            if not reg.has("seedemu", "hook", hook_name):
                emulator.addHook(FrrBgpFinalizeHook(hook_name, target, self))
        for asn, router_name in self.__enabled:
            scope = ScopedRegistry(str(asn), reg)
            assert scope.has("rnode", router_name), f"Router as{asn}/{router_name} not found for FrrBgp"
            router = scope.get("rnode", router_name)
            assert isinstance(router, Router)
            set_bgp_backend(router, "frr")

    def _merge_frr_config(self, router: Router, body: str) -> None:
        managed = FrrBgpFileTemplates["managed_block"].format(
            hostname=f"as{router.getAsn()}-{router.getName()}",
            body=body,
        )
        existing = ""
        if any(path == "/etc/frr/frr.conf" for path, _ in (f.get() for f in router.getFiles())):
            existing = router.getFile("/etc/frr/frr.conf").get()[1]
        start_marker = "! ===== seedemu-frr-bgp begin ====="
        end_marker = "! ===== seedemu-frr-bgp end ====="
        if start_marker in existing and end_marker in existing:
            prefix = existing.split(start_marker, 1)[0].rstrip()
            suffix = existing.split(end_marker, 1)[1].lstrip()
            parts = [part for part in [prefix, managed.strip(), suffix] if part]
            router.setFile("/etc/frr/frr.conf", "\n\n".join(parts) + "\n")
            return
        if existing.strip():
            router.setFile("/etc/frr/frr.conf", existing.rstrip() + "\n\n" + managed)
            return
        router.setFile("/etc/frr/frr.conf", managed)

    def _ensure_start_script(self, router: Router) -> None:
        router.addSoftware("frr")
        has_start = any(path == "/frr_start" for path, _ in (f.get() for f in router.getFiles()))
        if has_start:
            _, content = router.getFile("/frr_start").get()
            additions = []
            for daemon in ("bgpd", "zebra", "staticd"):
                needle = f"sed -i 's/{daemon}=no/{daemon}=yes/' /etc/frr/daemons"
                if needle not in content:
                    additions.append(needle)
            if additions:
                if "service frr start" in content:
                    content = content.replace("service frr start", "\n".join(additions) + "\nservice frr start", 1)
                else:
                    content = content.rstrip() + "\n" + "\n".join(additions) + "\n"
                router.setFile("/frr_start", content)
            return

        router.setFile("/frr_start", FrrBgpFileTemplates["start_script"])
        router.appendStartCommand("chmod +x /frr_start")
        router.appendStartCommand("/frr_start")

    def render(self, emulator: Emulator):
        self.finalize(emulator)

    def finalize(self, emulator: Emulator):
        reg = emulator.getRegistry()
        for asn, router_name in self.__enabled:
            scope = ScopedRegistry(str(asn), reg)
            router = scope.get("rnode", router_name)
            assert isinstance(router, Router)
            if get_bgp_backend(router) != "frr":
                continue
            sessions = get_bgp_sessions(router)
            self._ensure_start_script(router)
            ospf_body = _render_ospf_block(router)
            bgp_body = _render_bgp_block(router, sessions) if sessions else ""
            if not ospf_body.strip() and not bgp_body.strip():
                self._log(f"as{asn}/{router_name} marked for FRR but no routing intents were recorded; skipping config generation.")
                continue
            frr_body = ospf_body + bgp_body
            self._merge_frr_config(router, frr_body)


class FrrBgpFinalizeHook(Hook):
    __hook_name: str
    __target: str
    __layer: FrrBgp

    def __init__(self, hook_name: str, target: str, layer: FrrBgp):
        self.__hook_name = hook_name
        self.__target = target
        self.__layer = layer

    def getName(self) -> str:
        return self.__hook_name

    def getTargetLayer(self) -> str:
        return self.__target

    def postrender(self, emulator: Emulator):
        self.__layer.finalize(emulator)

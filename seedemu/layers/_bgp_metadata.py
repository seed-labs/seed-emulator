from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple

from seedemu.core import Router
from seedemu.core.enums import NetworkType


BGP_BACKEND_ATTR = "__bgp_backend"
BGP_SESSION_INTENTS_ATTR = "__bgp_session_intents"
BGP_CONNECTED_EXPORT_ATTR = "__bgp_connected_export"
OSPF_INTERFACE_INTENTS_ATTR = "__ospf_interface_intents"

BGP_BACKEND_BIRD = "bird"
BGP_BACKEND_FRR = "frr"
BGP_BACKEND_LABEL = "seedemu_bgp_backend"

BGP_KIND_EBGP = "ebgp"
BGP_KIND_IBGP = "ibgp"
BGP_EXPORT_ALL = "all"
BGP_EXPORT_LOCAL_AND_CUSTOMER = "local_and_customer"


def get_bgp_backend(node: Router) -> str:
    backend = None
    try:
        backend = node.getRoutingBackend()
    except AttributeError:
        try:
            backend = node.getAttribute(BGP_BACKEND_ATTR)
        except AttributeError:
            backend = None
    if backend in {None, ""}:
        backend = node.getLabel().get(BGP_BACKEND_LABEL, BGP_BACKEND_BIRD)
    backend = str(backend or BGP_BACKEND_BIRD).strip().lower()
    if backend not in {BGP_BACKEND_BIRD, BGP_BACKEND_FRR}:
        raise ValueError(f"unsupported BGP backend: {backend}")
    return backend


def set_bgp_backend(node: Router, backend: str) -> None:
    value = str(backend or BGP_BACKEND_BIRD).strip().lower() or BGP_BACKEND_BIRD
    if value not in {BGP_BACKEND_BIRD, BGP_BACKEND_FRR}:
        raise ValueError(f"unsupported BGP backend: {backend}")
    node.setLabel(BGP_BACKEND_LABEL, value)
    try:
        node.setRoutingBackend(value)
    except AttributeError:
        pass
    try:
        node.setAttribute(BGP_BACKEND_ATTR, value)
    except AttributeError:
        pass


def _normalize_export_policy(policy: Any) -> str:
    value = str(policy or BGP_EXPORT_ALL).strip().lower()
    if value not in {BGP_EXPORT_ALL, BGP_EXPORT_LOCAL_AND_CUSTOMER}:
        raise ValueError(f"unsupported export policy: {policy}")
    return value


def normalize_bgp_session(session: Dict[str, Any]) -> Dict[str, Any]:
    name = str(session.get("name") or "session").strip() or "session"
    kind = str(session.get("kind") or BGP_KIND_EBGP).strip().lower() or BGP_KIND_EBGP
    if kind not in {BGP_KIND_EBGP, BGP_KIND_IBGP}:
        raise ValueError(f"unsupported BGP session kind: {kind}")

    local_address = str(session.get("local_address") or "").strip()
    peer_address = str(session.get("peer_address") or "").strip()
    local_asn = int(session.get("local_asn") or 0)
    peer_asn = int(session.get("peer_asn") or 0)
    if not local_address or not peer_address:
        raise ValueError("BGP session must include local_address and peer_address")
    if local_asn <= 0 or peer_asn <= 0:
        raise ValueError("BGP session must include positive local_asn and peer_asn")

    route_server_client = bool(session.get("route_server_client", False))
    import_community = session.get("import_community")
    import_community = str(import_community).strip() if import_community not in {None, ""} else None
    local_pref_value = session.get("local_pref")
    local_pref = int(local_pref_value) if local_pref_value not in {None, ""} else None

    normalized = {
        "name": name,
        "kind": kind,
        "local_address": local_address,
        "local_asn": local_asn,
        "peer_address": peer_address,
        "peer_asn": peer_asn,
        "import_community": import_community,
        "local_pref": local_pref,
        "export_policy": _normalize_export_policy(session.get("export_policy")),
        "next_hop_self": bool(session.get("next_hop_self", False)),
        "route_server_client": route_server_client,
        "igp_table": str(session.get("igp_table") or "t_ospf").strip() or "t_ospf",
    }

    if kind == BGP_KIND_IBGP and normalized["local_asn"] != normalized["peer_asn"]:
        raise ValueError("iBGP session must use the same local_asn and peer_asn")
    if route_server_client and kind != BGP_KIND_EBGP:
        raise ValueError("route_server_client is only valid for eBGP sessions")

    return normalized


def record_bgp_session(node: Router, session: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_bgp_session(session)
    sessions = [dict(item) for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or []) if isinstance(item, dict)]
    sessions = [item for item in sessions if str(item.get("name") or "") != normalized["name"]]
    sessions.append(normalized)
    node.setAttribute(BGP_SESSION_INTENTS_ATTR, sessions)
    return dict(normalized)


def get_bgp_sessions(node: Router) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or []):
        if not isinstance(item, dict):
            continue
        out.append(normalize_bgp_session(item))
    return out


def mark_bgp_connected_export(node: Router) -> None:
    node.setAttribute(BGP_CONNECTED_EXPORT_ATTR, True)


def has_bgp_connected_export(node: Router) -> bool:
    return bool(node.getAttribute(BGP_CONNECTED_EXPORT_ATTR, False))


def install_router_bgp_session(node: Router, session: Dict[str, Any]) -> Dict[str, Any]:
    normalized = record_bgp_session(node, session)
    if not normalized["route_server_client"]:
        mark_bgp_connected_export(node)
    return normalized


def classify_ospf_interfaces(
    node: Router,
    *,
    stubs: Iterable[str] = (),
    masked: Iterable[str] = (),
) -> Tuple[List[str], List[str]]:
    stub_names = {str(name) for name in stubs}
    masked_names = {str(name) for name in masked}
    active: List[str] = []
    passive: List[str] = ["dummy0"]
    for iface in node.getInterfaces():
        net = iface.getNet()
        name = str(net.getName())
        if name in masked_names:
            continue
        if name in stub_names or net.getType() != NetworkType.Local:
            passive.append(name)
            continue
        active.append(name)
    return active, passive


def set_ospf_interface_intents(node: Router, active: Iterable[str], passive: Iterable[str]) -> None:
    node.setAttribute(
        OSPF_INTERFACE_INTENTS_ATTR,
        {
            "active": sorted({str(name) for name in active}),
            "passive": sorted({str(name) for name in passive}),
        },
    )


def get_ospf_interface_intents(node: Router) -> Dict[str, List[str]]:
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    active = [str(name) for name in list(raw.get("active", []) or [])]
    passive = [str(name) for name in list(raw.get("passive", []) or [])]
    return {"active": active, "passive": passive}

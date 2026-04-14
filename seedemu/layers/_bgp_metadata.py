from __future__ import annotations

from typing import Any, Iterable

from seedemu.core import Router
from seedemu.core.enums import NetworkType


BGP_BACKEND_ATTR = "__bgp_backend"
BGP_SESSION_INTENTS_ATTR = "__bgp_session_intents"
BGP_CONNECTED_EXPORT_ATTR = "__bgp_connected_export"
BGP_BOOTSTRAPPED_ATTR = "__bgp_bootstrapped"
OSPF_INTERFACE_INTENTS_ATTR = "__ospf_interface_intents"

BGP_KIND_EBGP = "ebgp"
BGP_KIND_IBGP = "ibgp"
BGP_EXPORT_ALL = "all"
BGP_EXPORT_LOCAL_AND_CUSTOMER = "local_and_customer"

COMMUNITY_ALIAS_BY_NAME = {
    "LOCAL_COMM": lambda asn: f"{asn}:0:0",
    "CUSTOMER_COMM": lambda asn: f"{asn}:1:0",
    "PEER_COMM": lambda asn: f"{asn}:2:0",
    "PROVIDER_COMM": lambda asn: f"{asn}:3:0",
}

BIRD_BGP_COMMONS_TEMPLATE = """\
define LOCAL_COMM = ({localAsn}, 0, 0);
define CUSTOMER_COMM = ({localAsn}, 1, 0);
define PEER_COMM = ({localAsn}, 2, 0);
define PROVIDER_COMM = ({localAsn}, 3, 0);
"""

BIRD_RS_PEER_TEMPLATE = """\
    ipv4 {{
        import all;
        export all;
    }};
    rs client;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BIRD_ROUTER_PEER_TEMPLATE = """\
    ipv4 {{
        table t_bgp;
        import {importClause};
        export {exportClause};
{nextHopSelfClause}    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BIRD_IBGP_PEER_TEMPLATE = """\
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table {igpTable};
    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

CONNECTED_EXPORT_FILTER = "filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }"


def get_bgp_backend(node: Router) -> str:
    backend = str(node.getAttribute(BGP_BACKEND_ATTR, "bird") or "bird").strip().lower()
    return backend if backend in {"bird", "frr"} else "bird"


def set_bgp_backend(node: Router, backend: str) -> None:
    value = str(backend or "bird").strip().lower() or "bird"
    if value not in {"bird", "frr"}:
        raise ValueError(f"unsupported BGP backend: {backend}")
    node.setAttribute(BGP_BACKEND_ATTR, value)


def _normalize_export_policy(policy: Any) -> str:
    value = str(policy or BGP_EXPORT_ALL).strip().lower()
    if value not in {BGP_EXPORT_ALL, BGP_EXPORT_LOCAL_AND_CUSTOMER}:
        raise ValueError(f"unsupported export policy: {policy}")
    return value


def normalize_bgp_session(session: dict[str, Any]) -> dict[str, Any]:
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


def record_bgp_session(node: Router, session: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_bgp_session(session)
    sessions = [dict(item) for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or []) if isinstance(item, dict)]
    sessions = [item for item in sessions if str(item.get("name") or "") != normalized["name"]]
    sessions.append(normalized)
    node.setAttribute(BGP_SESSION_INTENTS_ATTR, sessions)
    return dict(normalized)


def get_bgp_sessions(node: Router) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or []):
        if not isinstance(item, dict):
            continue
        out.append(normalize_bgp_session(item))
    return out


def mark_bgp_connected_export(node: Router) -> None:
    node.setAttribute(BGP_CONNECTED_EXPORT_ATTR, True)


def has_bgp_connected_export(node: Router) -> bool:
    return bool(node.getAttribute(BGP_CONNECTED_EXPORT_ATTR, False))


def ensure_bird_bgp_base(node: Router) -> None:
    if get_bgp_backend(node) != "bird":
        return
    if not node.getAttribute(BGP_BOOTSTRAPPED_ATTR, False):
        node.setAttribute(BGP_BOOTSTRAPPED_ATTR, True)
        node.appendFile("/etc/bird/bird.conf", BIRD_BGP_COMMONS_TEMPLATE.format(localAsn=node.getAsn()))
    node.addTable("t_bgp")
    node.addTablePipe("t_bgp")
    if not has_bgp_connected_export(node):
        node.addTablePipe("t_direct", "t_bgp", exportFilter=CONNECTED_EXPORT_FILTER)
        mark_bgp_connected_export(node)


def _bird_import_clause(session: dict[str, Any]) -> str:
    if session["import_community"] and session["local_pref"] is not None:
        return (
            "filter {\n"
            f"            bgp_large_community.add({session['import_community']});\n"
            f"            bgp_local_pref = {int(session['local_pref'])};\n"
            "            accept;\n"
            "        }"
        )
    return "all"


def _bird_export_clause(session: dict[str, Any]) -> str:
    if session["export_policy"] == BGP_EXPORT_LOCAL_AND_CUSTOMER:
        return "where bgp_large_community ~ [LOCAL_COMM, CUSTOMER_COMM]"
    return "all"


def render_bird_protocol_body(session: dict[str, Any]) -> str:
    normalized = normalize_bgp_session(session)
    if normalized["route_server_client"]:
        return BIRD_RS_PEER_TEMPLATE.format(
            localAddress=normalized["local_address"],
            localAsn=normalized["local_asn"],
            peerAddress=normalized["peer_address"],
            peerAsn=normalized["peer_asn"],
        )
    if normalized["kind"] == BGP_KIND_IBGP:
        return BIRD_IBGP_PEER_TEMPLATE.format(
            localAddress=normalized["local_address"],
            localAsn=normalized["local_asn"],
            peerAddress=normalized["peer_address"],
            peerAsn=normalized["peer_asn"],
            igpTable=normalized["igp_table"],
        )
    next_hop_self_clause = "        next hop self;\n" if normalized["next_hop_self"] else ""
    return BIRD_ROUTER_PEER_TEMPLATE.format(
        importClause=_bird_import_clause(normalized),
        exportClause=_bird_export_clause(normalized),
        nextHopSelfClause=next_hop_self_clause,
        localAddress=normalized["local_address"],
        localAsn=normalized["local_asn"],
        peerAddress=normalized["peer_address"],
        peerAsn=normalized["peer_asn"],
    )


def install_router_bgp_session(node: Router, session: dict[str, Any]) -> dict[str, Any]:
    normalized = record_bgp_session(node, session)
    if get_bgp_backend(node) != "bird":
        mark_bgp_connected_export(node)
        return normalized
    ensure_bird_bgp_base(node)
    node.addProtocol("bgp", normalized["name"], render_bird_protocol_body(normalized))
    return normalized


def classify_ospf_interfaces(
    node: Router,
    *,
    stubs: Iterable[str] = (),
    masked: Iterable[str] = (),
) -> tuple[list[str], list[str]]:
    stub_names = {str(name) for name in stubs}
    masked_names = {str(name) for name in masked}
    active: list[str] = []
    passive: list[str] = ["dummy0"]
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


def get_ospf_interface_intents(node: Router) -> dict[str, list[str]]:
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    active = [str(name) for name in list(raw.get("active", []) or [])]
    passive = [str(name) for name in list(raw.get("passive", []) or [])]
    return {"active": active, "passive": passive}

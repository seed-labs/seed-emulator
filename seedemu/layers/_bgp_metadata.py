from __future__ import annotations

from hashlib import sha1
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from seedemu.core import Router
from seedemu.core.enums import NetworkType


BGP_SESSION_INTENTS_ATTR = "__bgp_session_intents"
BGP_CONNECTED_EXPORT_ATTR = "__bgp_connected_export"
BGP_CONNECTED_EXPORT_RENDERED_ATTR = "__bgp_connected_export_rendered"
BGP_BOOTSTRAPPED_ATTR = "__bgp_bootstrapped"
OSPF_INTERFACE_INTENTS_ATTR = "__ospf_interface_intents"
MPLS_LDP_INTENT_ATTR = "__mpls_ldp_intent"

DEFAULT_OSPF_TICK = 1
DEFAULT_OSPF_HELLO = 1
DEFAULT_OSPF_DEAD = 4
DEFAULT_BGP_HOLD_TIME = 36000
DEFAULT_BGP_KEEPALIVE_TIME = 60

BGP_BACKEND_BIRD = "bird"
BGP_BACKEND_FRR = "frr"

BGP_KIND_EBGP = "ebgp"
BGP_KIND_IBGP = "ibgp"
BGP_EXPORT_ALL = "all"
BGP_EXPORT_LOCAL_AND_CUSTOMER = "local_and_customer"

BGP_COMMUNITY_LOCAL = "local"
BGP_COMMUNITY_CUSTOMER = "customer"
BGP_COMMUNITY_PEER = "peer"
BGP_COMMUNITY_PROVIDER = "provider"

BGP_COMMUNITY_ALIASES = {
    "LOCAL_COMM": BGP_COMMUNITY_LOCAL,
    "CUSTOMER_COMM": BGP_COMMUNITY_CUSTOMER,
    "PEER_COMM": BGP_COMMUNITY_PEER,
    "PROVIDER_COMM": BGP_COMMUNITY_PROVIDER,
    "local": BGP_COMMUNITY_LOCAL,
    "customer": BGP_COMMUNITY_CUSTOMER,
    "peer": BGP_COMMUNITY_PEER,
    "provider": BGP_COMMUNITY_PROVIDER,
}

BIRD_COMMUNITY_NAMES = {
    BGP_COMMUNITY_LOCAL: "LOCAL_COMM",
    BGP_COMMUNITY_CUSTOMER: "CUSTOMER_COMM",
    BGP_COMMUNITY_PEER: "PEER_COMM",
    BGP_COMMUNITY_PROVIDER: "PROVIDER_COMM",
}

FRR_COMMUNITY_VALUES = {
    BGP_COMMUNITY_LOCAL: "0:0",
    BGP_COMMUNITY_CUSTOMER: "1:0",
    BGP_COMMUNITY_PEER: "2:0",
    BGP_COMMUNITY_PROVIDER: "3:0",
}

BIRD_BGP_COMMONS_TEMPLATE = """\
define LOCAL_COMM = ({localAsn}, 0, 0);
define CUSTOMER_COMM = ({localAsn}, 1, 0);
define PEER_COMM = ({localAsn}, 2, 0);
define PROVIDER_COMM = ({localAsn}, 3, 0);
"""

BIRD_RS_PEER_TEMPLATE = """\
    hold time {holdTime};
    keepalive time {keepaliveTime};
    ipv4 {{
        import all;
        export all;
    }};
    rs client;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BIRD_ROUTER_PEER_TEMPLATE = """\
    hold time {holdTime};
    keepalive time {keepaliveTime};
    ipv4 {{
        table t_bgp;
        import {importClause};
        export {exportClause};
{nextHopSelf}    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
"""

BIRD_IBGP_PEER_TEMPLATE = """\
{passive}\
    hold time {holdTime};
    keepalive time {keepaliveTime};
    ipv4 {{
        table t_bgp;
        import all;
        export all;
        igp table {igpTable};
{nextHopSelf}\
    }};
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
{routeReflector}\
"""

CONNECTED_EXPORT_FILTER = "filter { bgp_large_community.add(LOCAL_COMM); bgp_local_pref = 40; accept; }"


def get_bgp_backend(node: Router) -> str:
    """Return the router daemon backend used for BGP rendering."""
    backend = node.getRoutingBackend()
    value = str(backend or BGP_BACKEND_BIRD).strip().lower()
    if value not in {BGP_BACKEND_BIRD, BGP_BACKEND_FRR}:
        raise ValueError("unsupported routing backend: {}".format(backend))
    return value


def _normalize_export_policy(policy: Any) -> str:
    # This v1 intent model intentionally keeps export policy narrow. Richer
    # policy controls such as prepend, MED, and AS-path filters should become a
    # structured policy object instead of overloading these string tokens.
    value = str(policy or BGP_EXPORT_ALL).strip().lower()
    if value not in {BGP_EXPORT_ALL, BGP_EXPORT_LOCAL_AND_CUSTOMER}:
        raise ValueError("unsupported export policy: {}".format(policy))
    return value


def _normalize_community(community: Any) -> Optional[str]:
    if community in {None, ""}:
        return None
    value = str(community).strip()
    if value == "":
        return None
    if value not in BGP_COMMUNITY_ALIASES:
        raise ValueError("unsupported BGP community intent: {}".format(community))
    return BGP_COMMUNITY_ALIASES[value]


def _positive_int(value: Any, field: str) -> int:
    normalized = int(value)
    if normalized <= 0:
        raise ValueError("{} must be a positive integer".format(field))
    return normalized


def normalize_bgp_timers(
    hold_time: Any = DEFAULT_BGP_HOLD_TIME,
    keepalive_time: Any = DEFAULT_BGP_KEEPALIVE_TIME,
) -> Dict[str, int]:
    hold = _positive_int(hold_time, "BGP hold_time")
    keepalive = _positive_int(keepalive_time, "BGP keepalive_time")
    if keepalive >= hold:
        raise ValueError("BGP keepalive_time must be smaller than hold_time")
    return {
        "hold_time": hold,
        "keepalive_time": keepalive,
    }


def normalize_ospf_timers(
    tick: Any = DEFAULT_OSPF_TICK,
    hello: Any = DEFAULT_OSPF_HELLO,
    dead: Any = DEFAULT_OSPF_DEAD,
) -> Dict[str, int]:
    normalized_tick = _positive_int(tick, "OSPF tick")
    normalized_hello = _positive_int(hello, "OSPF hello")
    normalized_dead = _positive_int(dead, "OSPF dead")
    if normalized_dead <= normalized_hello:
        raise ValueError("OSPF dead must be larger than hello")
    return {
        "tick": normalized_tick,
        "hello": normalized_hello,
        "dead": normalized_dead,
    }


def render_bird_community(community: str) -> str:
    normalized = _normalize_community(community)
    if normalized is None:
        raise ValueError("BIRD community rendering requires a community intent")
    return BIRD_COMMUNITY_NAMES[normalized]


def render_frr_community(local_asn: int, community: str) -> str:
    normalized = _normalize_community(community)
    if normalized is None:
        raise ValueError("FRR community rendering requires a community intent")
    return "{}:{}".format(local_asn, FRR_COMMUNITY_VALUES[normalized])


def _safe_identifier(value: str) -> str:
    ident = "".join(ch if ch.isalnum() else "_" for ch in str(value or "session"))
    ident = ident.strip("_") or "session"
    if ident[0].isdigit():
        ident = "s_{}".format(ident)
    return ident


def _session_identity(session: Dict[str, Any]) -> Tuple[str, str, str, int, int, bool]:
    return (
        str(session["kind"]),
        str(session["local_address"]),
        str(session["peer_address"]),
        int(session["local_asn"]),
        int(session["peer_asn"]),
        bool(session["route_server_client"]),
    )


def _assign_render_names(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    used: Set[str] = set()
    named: List[Dict[str, Any]] = []
    for session in sessions:
        normalized = normalize_bgp_session(session)
        base = _safe_identifier(normalized["name"])
        render_name = base
        if render_name in used:
            digest = sha1("|".join(str(part) for part in _session_identity(normalized)).encode()).hexdigest()[:8]
            render_name = "{}_{}".format(base[:54], digest)
            counter = 2
            while render_name in used:
                suffix = "_{}".format(counter)
                render_name = "{}{}{}".format(base[:54 - len(suffix)], digest, suffix)
                counter += 1
        used.add(render_name)
        normalized["render_name"] = render_name
        named.append(normalized)
    return named


def normalize_bgp_session(session: Dict[str, Any]) -> Dict[str, Any]:
    name = str(session.get("name") or "session").strip() or "session"
    kind = str(session.get("kind") or BGP_KIND_EBGP).strip().lower() or BGP_KIND_EBGP
    if kind not in {BGP_KIND_EBGP, BGP_KIND_IBGP}:
        raise ValueError("unsupported BGP session kind: {}".format(kind))

    local_address = str(session.get("local_address") or "").strip()
    peer_address = str(session.get("peer_address") or "").strip()
    local_asn = int(session.get("local_asn") or 0)
    peer_asn = int(session.get("peer_asn") or 0)
    if not local_address or not peer_address:
        raise ValueError("BGP session must include local_address and peer_address")
    if local_asn <= 0 or peer_asn <= 0:
        raise ValueError("BGP session must include positive local_asn and peer_asn")

    route_server_client = bool(session.get("route_server_client", False))
    route_reflector_client = bool(session.get("route_reflector_client", False))
    if kind == BGP_KIND_IBGP and local_asn != peer_asn:
        raise ValueError("iBGP session must use the same local_asn and peer_asn")
    if route_server_client and kind != BGP_KIND_EBGP:
        raise ValueError("route_server_client is only valid for eBGP sessions")
    if route_reflector_client and kind != BGP_KIND_IBGP:
        raise ValueError("route_reflector_client is only valid for iBGP sessions")

    route_reflector_cluster_id = session.get("route_reflector_cluster_id")
    route_reflector_cluster_id = (
        str(route_reflector_cluster_id).strip()
        if route_reflector_cluster_id not in {None, ""}
        else None
    )
    if route_reflector_client and route_reflector_cluster_id is None:
        raise ValueError("route_reflector_client requires route_reflector_cluster_id")

    import_community = _normalize_community(session.get("import_community"))
    local_pref_value = session.get("local_pref")
    local_pref = int(local_pref_value) if local_pref_value not in {None, ""} else None
    timers = normalize_bgp_timers(
        session.get("hold_time", DEFAULT_BGP_HOLD_TIME),
        session.get("keepalive_time", DEFAULT_BGP_KEEPALIVE_TIME),
    )

    return {
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
        "route_reflector_client": route_reflector_client,
        "route_reflector_cluster_id": route_reflector_cluster_id,
        "passive": bool(session.get("passive", False)),
        "igp_table": str(session.get("igp_table") or "t_ospf").strip() or "t_ospf",
        "hold_time": timers["hold_time"],
        "keepalive_time": timers["keepalive_time"],
    }


def record_bgp_session(node: Router, session: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_bgp_session(session)
    sessions = [
        normalize_bgp_session(item)
        for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or [])
        if isinstance(item, dict)
    ]
    replaced = False
    updated: List[Dict[str, Any]] = []
    for item in sessions:
        if _session_identity(item) == _session_identity(normalized):
            updated.append(normalized)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(normalized)
    updated = _assign_render_names(updated)
    node.setAttribute(BGP_SESSION_INTENTS_ATTR, updated)
    for item in updated:
        if _session_identity(item) == _session_identity(normalized):
            return dict(item)
    return dict(updated[-1])


def get_bgp_sessions(node: Router) -> List[Dict[str, Any]]:
    sessions: List[Dict[str, Any]] = []
    for item in list(node.getAttribute(BGP_SESSION_INTENTS_ATTR, []) or []):
        if isinstance(item, dict):
            sessions.append(normalize_bgp_session(item))
    return _assign_render_names(sessions)


def mark_bgp_connected_export(node: Router) -> None:
    node.setAttribute(BGP_CONNECTED_EXPORT_ATTR, True)


def has_bgp_connected_export(node: Router) -> bool:
    return bool(node.getAttribute(BGP_CONNECTED_EXPORT_ATTR, False))


def ensure_bird_bgp_base(node: Router, include_tables: bool = True) -> None:
    """Install BIRD's shared BGP scaffolding for routers that still use BIRD."""
    if get_bgp_backend(node) != BGP_BACKEND_BIRD:
        return
    if not node.getAttribute(BGP_BOOTSTRAPPED_ATTR, False):
        node.setAttribute(BGP_BOOTSTRAPPED_ATTR, True)
        node.appendFile("/etc/bird/bird.conf", BIRD_BGP_COMMONS_TEMPLATE.format(localAsn=node.getAsn()))
    if not include_tables:
        return
    node.addTable("t_bgp")
    node.addTablePipe("t_bgp")
    if has_bgp_connected_export(node) and not node.getAttribute(BGP_CONNECTED_EXPORT_RENDERED_ATTR, False):
        node.addTablePipe("t_direct", "t_bgp", exportFilter=CONNECTED_EXPORT_FILTER)
        node.setAttribute(BGP_CONNECTED_EXPORT_RENDERED_ATTR, True)


def _bird_import_clause(session: Dict[str, Any]) -> str:
    if session["import_community"] and session["local_pref"] is not None:
        return (
            "filter {{\n"
            "            bgp_large_community.add({});\n"
            "            bgp_local_pref = {};\n"
            "            accept;\n"
            "        }}"
        ).format(render_bird_community(session["import_community"]), int(session["local_pref"]))
    return "all"


def _bird_export_clause(session: Dict[str, Any]) -> str:
    if session["export_policy"] == BGP_EXPORT_LOCAL_AND_CUSTOMER:
        return "where bgp_large_community ~ [LOCAL_COMM, CUSTOMER_COMM]"
    return "all"


def render_bird_protocol_body(session: Dict[str, Any]) -> str:
    normalized = normalize_bgp_session(session)
    if normalized["route_server_client"]:
        return BIRD_RS_PEER_TEMPLATE.format(
            localAddress=normalized["local_address"],
            localAsn=normalized["local_asn"],
            peerAddress=normalized["peer_address"],
            peerAsn=normalized["peer_asn"],
            holdTime=normalized["hold_time"],
            keepaliveTime=normalized["keepalive_time"],
        )
    if normalized["kind"] == BGP_KIND_IBGP:
        return BIRD_IBGP_PEER_TEMPLATE.format(
            localAddress=normalized["local_address"],
            localAsn=normalized["local_asn"],
            peerAddress=normalized["peer_address"],
            peerAsn=normalized["peer_asn"],
            holdTime=normalized["hold_time"],
            keepaliveTime=normalized["keepalive_time"],
            igpTable=normalized["igp_table"],
            nextHopSelf="        next hop self;\n" if normalized["next_hop_self"] else "",
            passive="    passive yes;\n" if normalized["passive"] else "",
            routeReflector=(
                "    rr client;\n"
                "    rr cluster id {};\n".format(normalized["route_reflector_cluster_id"])
                if normalized["route_reflector_client"]
                else ""
            ),
        )
    return BIRD_ROUTER_PEER_TEMPLATE.format(
        localAddress=normalized["local_address"],
        localAsn=normalized["local_asn"],
        peerAddress=normalized["peer_address"],
        peerAsn=normalized["peer_asn"],
        holdTime=normalized["hold_time"],
        keepaliveTime=normalized["keepalive_time"],
        importClause=_bird_import_clause(normalized),
        exportClause=_bird_export_clause(normalized),
        nextHopSelf="        next hop self;\n" if normalized["next_hop_self"] else "",
    )


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


def set_ospf_interface_intents(
    node: Router,
    active: Iterable[str],
    passive: Iterable[str],
    *,
    tick: int = DEFAULT_OSPF_TICK,
    hello: int = DEFAULT_OSPF_HELLO,
    dead: int = DEFAULT_OSPF_DEAD,
) -> None:
    timers = normalize_ospf_timers(tick, hello, dead)
    node.setAttribute(
        OSPF_INTERFACE_INTENTS_ATTR,
        {
            "active": sorted({str(name) for name in active}),
            "passive": sorted({str(name) for name in passive}),
            "timers": timers,
        },
    )


def get_ospf_interface_intents(node: Router) -> Dict[str, List[str]]:
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    return {
        "active": [str(name) for name in list(raw.get("active", []) or [])],
        "passive": [str(name) for name in list(raw.get("passive", []) or [])],
    }


def set_mpls_ldp_intent(
    node: Router,
    interfaces: Iterable[str],
    *,
    platform_labels: int = 1048575,
) -> None:
    node.setAttribute(
        MPLS_LDP_INTENT_ATTR,
        {
            "interfaces": sorted({str(name) for name in interfaces}),
            "platform_labels": int(platform_labels),
        },
    )


def get_mpls_ldp_intent(node: Router) -> Dict[str, Any]:
    raw = node.getAttribute(MPLS_LDP_INTENT_ATTR, {}) or {}
    return {
        "interfaces": [str(name) for name in list(raw.get("interfaces", []) or [])],
        "platform_labels": int(raw.get("platform_labels", 1048575)),
    }


def has_mpls_ldp_intent(node: Router) -> bool:
    return bool(get_mpls_ldp_intent(node)["interfaces"])
def get_ospf_timers(node: Router) -> Dict[str, int]:
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    timers = raw.get("timers", {}) if isinstance(raw, dict) else {}
    return normalize_ospf_timers(
        timers.get("tick", DEFAULT_OSPF_TICK),
        timers.get("hello", DEFAULT_OSPF_HELLO),
        timers.get("dead", DEFAULT_OSPF_DEAD),
    )


def set_mpls_ldp_intent(
    node: Router,
    interfaces: Iterable[str],
    *,
    platform_labels: int = 1048575,
) -> None:
    node.setAttribute(
        MPLS_LDP_INTENT_ATTR,
        {
            "interfaces": sorted({str(name) for name in interfaces}),
            "platform_labels": int(platform_labels),
        },
    )


def get_mpls_ldp_intent(node: Router) -> Dict[str, Any]:
    raw = node.getAttribute(MPLS_LDP_INTENT_ATTR, {}) or {}
    return {
        "interfaces": [str(name) for name in list(raw.get("interfaces", []) or [])],
        "platform_labels": int(raw.get("platform_labels", 1048575)),
    }


def has_mpls_ldp_intent(node: Router) -> bool:
    return bool(get_mpls_ldp_intent(node)["interfaces"])

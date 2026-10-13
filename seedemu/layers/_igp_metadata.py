"""Software-independent OSPF/RIP intents, options and shared IGP policies."""

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple

from seedemu.core import Emulator, Network, Router
from seedemu.core.AutonomousSystem import IGP_INTERFACE_POLICIES, IGP_INTERFACE_POLICY_ALL_LOCAL
from seedemu.core.enums import NetworkType, NodeRole


IGP_PROTOCOL_ATTR = "__igp_protocol_intent"
OSPF_INTERFACE_INTENTS_ATTR = "__ospf_interface_intents"
# Keep the serialized attribute key used by existing RIP components.
RIP_INTERFACE_INTENTS_ATTR = "__rip_intent"

DEFAULT_OSPF_TICK = 1
DEFAULT_OSPF_HELLO = 1
DEFAULT_OSPF_DEAD = 4
DEFAULT_RIP_UPDATE = 30
DEFAULT_RIP_TIMEOUT = 180
DEFAULT_RIP_GARBAGE = 120

RIP_TIMER_KEYS = {"update", "timeout", "garbage"}
RIP_INTERFACE_KEYS = RIP_TIMER_KEYS | {
    "enabled", "passive", "metric", "version", "split_horizon", "poison_reverse",
}
RIP_ROUTER_KEYS = RIP_INTERFACE_KEYS | {"advertise_loopback"}
RIP_DEFAULTS = {
    "enabled": True,
    "advertise_loopback": True,
    "metric": 1,
    "version": 2,
    "update": DEFAULT_RIP_UPDATE,
    "timeout": DEFAULT_RIP_TIMEOUT,
    "garbage": DEFAULT_RIP_GARBAGE,
    "split_horizon": True,
    "poison_reverse": True,
}


def normalize_ospf_timers(
    tick: Any = DEFAULT_OSPF_TICK,
    hello: Any = DEFAULT_OSPF_HELLO,
    dead: Any = DEFAULT_OSPF_DEAD,
) -> Dict[str, int]:
    """Normalize OSPF timers, retaining the existing integer conversion API."""
    timers = {}
    for key, value in (("tick", tick), ("hello", hello), ("dead", dead)):
        normalized = int(value)
        if normalized <= 0:
            raise ValueError("OSPF {} must be a positive integer".format(key))
        timers[key] = normalized
    if timers["dead"] <= timers["hello"]:
        raise ValueError("OSPF dead must be larger than hello")
    return timers


def normalize_rip_options(options: Dict[str, Any], *, router: bool = False) -> Dict[str, Any]:
    """Validate partial RIP options; router also permits loopback advertisement."""
    allowed = RIP_ROUTER_KEYS if router else RIP_INTERFACE_KEYS
    unknown = set(options) - allowed
    if unknown:
        raise ValueError("unsupported RIP options: {}".format(", ".join(sorted(unknown))))
    normalized = dict(options)
    for key, value in normalized.items():
        if key in {"enabled", "passive", "advertise_loopback", "split_horizon", "poison_reverse"}:
            if not isinstance(value, bool):
                raise ValueError("RIP {} must be a boolean".format(key))
        else:
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("RIP {} must be an integer".format(key))
            if key in RIP_TIMER_KEYS and not 1 <= value <= 65535:
                raise ValueError("RIP {} must be between 1 and 65535 seconds".format(key))
            if key == "metric" and not 1 <= value <= 15:
                raise ValueError("RIP metric must be between 1 and 15 (16 means unreachable)")
            if key == "version" and value not in {1, 2}:
                raise ValueError("RIP version must be 1 or 2")
    if "update" in normalized and "timeout" in normalized:
        if normalized["timeout"] <= normalized["update"]:
            raise ValueError("RIP timeout must be larger than update")
    return normalized


def normalize_rip_timers(
    update: int = DEFAULT_RIP_UPDATE,
    timeout: int = DEFAULT_RIP_TIMEOUT,
    garbage: int = DEFAULT_RIP_GARBAGE,
) -> Dict[str, int]:
    """Validate RIP timers in seconds, including timeout > update."""
    return normalize_rip_options({"update": update, "timeout": timeout, "garbage": garbage})


def validate_rip_options(options: Dict[str, Any]) -> None:
    """Validate resolved RIP options after all policy scopes have been combined."""
    normalize_rip_options(options, router=True)
    normalize_rip_timers(options["update"], options["timeout"], options["garbage"])


def set_ospf_interface_intents(
    node: Router,
    active: Iterable[str],
    passive: Iterable[str],
    *,
    tick: int = DEFAULT_OSPF_TICK,
    hello: int = DEFAULT_OSPF_HELLO,
    dead: int = DEFAULT_OSPF_DEAD,
) -> None:
    """Store OSPF interface roles and timers without writing daemon configuration."""
    timers = normalize_ospf_timers(tick, hello, dead)
    node.setAttribute(OSPF_INTERFACE_INTENTS_ATTR, {
        "active": sorted({str(name) for name in active}),
        "passive": sorted({str(name) for name in passive}),
        "timers": timers,
    })


def get_ospf_interface_intents(node: Router) -> Dict[str, List[str]]:
    """Return independent lists of OSPF active and passive interface names."""
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    return {
        "active": [str(name) for name in list(raw.get("active", []) or [])],
        "passive": [str(name) for name in list(raw.get("passive", []) or [])],
    }


def get_ospf_timers(node: Router) -> Dict[str, int]:
    """Read node's OSPF timers, supplying defaults for older saved intents."""
    raw = node.getAttribute(OSPF_INTERFACE_INTENTS_ATTR, {}) or {}
    timers = raw.get("timers", {}) if isinstance(raw, dict) else {}
    return normalize_ospf_timers(
        timers.get("tick", DEFAULT_OSPF_TICK),
        timers.get("hello", DEFAULT_OSPF_HELLO),
        timers.get("dead", DEFAULT_OSPF_DEAD),
    )


def set_rip_interface_intents(
    node: Router,
    interfaces: Iterable[Dict[str, Any]],
    *,
    defaults: Optional[Dict[str, Any]] = None,
) -> None:
    """Store resolved RIP interfaces and router defaults as independent copies."""
    resolved_defaults = {**RIP_DEFAULTS, **(defaults or {})}
    validate_rip_options(resolved_defaults)
    intent = {"defaults": resolved_defaults, "interfaces": list(interfaces)}
    node.setAttribute(RIP_INTERFACE_INTENTS_ATTR, deepcopy(intent))


def get_rip_interface_intents(node: Router) -> Dict[str, Any]:
    """Return copied RIP defaults/interfaces, or {} when RIP is not configured."""
    return deepcopy(node.getAttribute(RIP_INTERFACE_INTENTS_ATTR, {}) or {})


def get_rip_timers(node: Router) -> Dict[str, int]:
    """Read node's RIP default timers; interface overrides remain in its intent."""
    defaults = get_rip_interface_intents(node).get("defaults", {})
    return normalize_rip_timers(
        defaults.get("update", DEFAULT_RIP_UPDATE),
        defaults.get("timeout", DEFAULT_RIP_TIMEOUT),
        defaults.get("garbage", DEFAULT_RIP_GARBAGE),
    )


def is_igp_active_network(network: Network, policy: str) -> bool:
    """Apply a software-independent AS policy to a real network attachment."""
    if policy not in IGP_INTERFACE_POLICIES:
        raise ValueError("unsupported IGP interface policy: {}".format(policy))
    if network.getType() != NetworkType.Local:
        return False
    if policy == IGP_INTERFACE_POLICY_ALL_LOCAL:
        return True
    return sum(
        node.getRole() in {NodeRole.Router, NodeRole.BorderRouter, NodeRole.OpenVpnRouter}
        for node in network.getAssociations()
    ) >= 2


def classify_igp_interfaces(
    node: Router,
    *,
    policy: str,
    stubs: Iterable[str] = (),
    masked: Iterable[str] = (),
) -> Tuple[List[str], List[str]]:
    """Partition interfaces for IGP exchange; passive prefixes remain advertised."""
    stub_names = {str(name) for name in stubs}
    masked_names = {str(name) for name in masked}
    active: List[str] = []
    passive: List[str] = ["dummy0"]
    for interface in node.getInterfaces():
        network = interface.getNet()
        name = str(network.getName())
        if name in masked_names:
            continue
        target = passive if name in stub_names or not is_igp_active_network(network, policy) else active
        target.append(name)
    return active, passive


def prepare_as_igp_modes(emulator: Emulator) -> None:
    """Validate AS-selected IGPs without changing their declared/default mode.

    Unset ASes remain OSPF even when only Rip is installed. A selected protocol
    requires its layer; MPLS can supply the existing OSPF path. Routing-only
    emulations with no IGP layers or explicit IGP declaration remain valid.
    """
    registry = emulator.getRegistry()
    base = registry.get("seedemu", "layer", "Base")
    layers = {
        protocol: registry.get("seedemu", "layer", name)
        for protocol, name in (("ospf", "Ospf"), ("rip", "Rip"))
        if registry.has("seedemu", "layer", name)
    }
    mpls = registry.get("seedemu", "layer", "Mpls") if registry.has("seedemu", "layer", "Mpls") else None
    for asn in base.getAsns():
        autonomous_system = base.getAutonomousSystem(asn)
        mpls_enabled = mpls is not None and (
            autonomous_system.getCoreForwarding() == "mpls" or asn in mpls.getEnabled()
        )
        mode = autonomous_system.getIgpMode()
        if mpls_enabled:
            if mode != "ospf":
                raise ValueError("AS{} selects {}, but the current MPLS/LDP implementation requires OSPF".format(asn, mode))
            continue
        if mode not in layers and (layers or autonomous_system.hasIgpMode()):
            raise ValueError("AS{} selects {} but its IGP layer is missing; add {}()".format(
                asn, mode, "Ospf" if mode == "ospf" else "Rip"))


def set_igp_protocol(node: Router, protocol: str) -> None:
    """Record node's IGP; reject competing providers on the same router."""
    previous = get_igp_protocol(node)
    if previous and previous != protocol:
        raise ValueError(
            "AS{}/{} has conflicting IGP layers: {} and {}; select one AS IGP with setIgpMode()"
            .format(node.getAsn(), node.getName(), previous, protocol)
        )
    node.setAttribute(IGP_PROTOCOL_ATTR, protocol)
    node.setLabel("seedemu_igp", protocol)


def get_igp_protocol(node: Router) -> str:
    """Return node's declared IGP, or an empty string for no provider."""
    return str(node.getAttribute(IGP_PROTOCOL_ATTR, "") or "")

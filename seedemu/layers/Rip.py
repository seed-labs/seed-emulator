"""RIP policy layer: derive protocol intents from Base topology and user options."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional, Set, Tuple

from seedemu.core import Emulator, Layer, Router
from seedemu.core.enums import NetworkType

from ._igp_metadata import (
    RIP_DEFAULTS,
    is_igp_active_network,
    normalize_rip_options,
    set_igp_protocol,
    set_rip_interface_intents,
    validate_rip_options,
)


class Rip(Layer):
    """Compose RIP requirements independently of BIRD/FRR and the compiler.

    Options resolve as layer defaults < network < router < interface. The AS's
    IGP interface policy defaults to all-local, activating all internal Local
    networks. Selecting router-links makes host-facing and single-router
    Local networks passive while retaining prefix advertisement.
    External links contribute connected prefixes for BGP
    next-hop resolution, but never receive or transmit RIP messages.
    ASes explicitly select this protocol through setIgpMode("rip").
    Installing this layer never changes the default OSPF choice of an AS.
    """

    def __init__(self):
        super().__init__()
        self.__defaults = dict(RIP_DEFAULTS)
        self.__networks: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.__routers: Dict[Tuple[int, str], Dict[str, Any]] = {}
        self.__interfaces: Dict[Tuple[int, str, str], Dict[str, Any]] = {}
        self.__stubs: Set[Tuple[int, str]] = set()
        self.__masked: Set[Tuple[int, str]] = set()
        self.__masked_asns: Set[int] = set()
        self.addDependency("Routing", False, False)

    def getName(self) -> str:
        return "Rip"

    def setDefaults(self, **options) -> Rip:
        """Set layer-wide options; options use the keys documented in B51_rip."""
        defaults = dict(self.__defaults)
        defaults.update(normalize_rip_options(options, router=True))
        validate_rip_options(defaults)
        self.__defaults = defaults
        return self

    def getDefaults(self) -> Dict[str, Any]:
        """Return a copy of layer-wide defaults."""
        return deepcopy(self.__defaults)

    def setTimers(
        self, update: Optional[int] = None, timeout: Optional[int] = None,
        garbage: Optional[int] = None,
    ) -> Rip:
        """Set default update, route timeout and garbage intervals, in seconds."""
        return self.setDefaults(**{
            key: value for key, value in
            {"update": update, "timeout": timeout, "garbage": garbage}.items()
            if value is not None
        })

    def getTimers(self) -> Dict[str, int]:
        """Return the three default RIP timer intervals, in seconds."""
        return {key: self.__defaults[key] for key in ("update", "timeout", "garbage")}

    def setNetworkOptions(self, asn: int, netname: str, **options) -> Rip:
        """Set shared options for netname's interfaces in asn; options are partial."""
        key = (int(asn), str(netname))
        combined = dict(self.__networks.get(key, {}))
        combined.update(normalize_rip_options(options))
        normalize_rip_options(combined)
        self.__networks[key] = combined
        return self

    def getNetworkOptions(self, asn: int, netname: str) -> Dict[str, Any]:
        """Return declared options for network netname in asn."""
        return deepcopy(self.__networks.get((int(asn), str(netname)), {}))

    def setRouterOptions(self, asn: int, router: str, **options) -> Rip:
        """Set partial options for router in asn, including advertise_loopback."""
        key = (int(asn), str(router))
        combined = dict(self.__routers.get(key, {}))
        combined.update(normalize_rip_options(options, router=True))
        normalize_rip_options(combined, router=True)
        self.__routers[key] = combined
        return self

    def getRouterOptions(self, asn: int, router: str) -> Dict[str, Any]:
        """Return declared options for router in asn."""
        return deepcopy(self.__routers.get((int(asn), str(router)), {}))

    def setInterfaceOptions(self, asn: int, router: str, netname: str, **options) -> Rip:
        """Set options on router's netname interface in asn; dummy0 is its loopback."""
        key = (int(asn), str(router), str(netname))
        combined = dict(self.__interfaces.get(key, {}))
        combined.update(normalize_rip_options(options))
        normalize_rip_options(combined)
        self.__interfaces[key] = combined
        return self

    def getInterfaceOptions(self, asn: int, router: str, netname: str) -> Dict[str, Any]:
        """Return declared options for router's netname interface in asn."""
        return deepcopy(self.__interfaces.get((int(asn), str(router), str(netname)), {}))

    def markAsStub(self, asn: int, netname: str) -> Rip:
        """Advertise netname in asn while suppressing outgoing updates on it."""
        self.__stubs.add((int(asn), str(netname)))
        return self

    def getStubs(self) -> Set[Tuple[int, str]]:
        return set(self.__stubs)

    def maskNetwork(self, asn: int, netname: str) -> Rip:
        """Exclude netname in asn from RIP participation and prefix advertisement."""
        self.__masked.add((int(asn), str(netname)))
        return self

    def getMaskedNetworks(self) -> Set[Tuple[int, str]]:
        return set(self.__masked)

    def maskAsn(self, asn: int) -> Rip:
        """Disable RIP on every router in asn."""
        self.__masked_asns.add(int(asn))
        return self

    def getMaskedAsns(self) -> Set[int]:
        return set(self.__masked_asns)

    def isMasked(self, asn: int, netname: str) -> bool:
        """Test whether netname or its containing asn is explicitly masked."""
        return int(asn) in self.__masked_asns or (int(asn), str(netname)) in self.__masked

    def getConfiguration(self) -> Dict[str, Any]:
        """Return copied declarations for component merging and inspection."""
        return deepcopy({
            "defaults": self.__defaults, "networks": self.__networks,
            "routers": self.__routers, "interfaces": self.__interfaces,
            "stubs": self.__stubs, "masked": self.__masked,
            "masked_asns": self.__masked_asns,
        })

    def _validateTargets(self, base, routers: Dict[Tuple[int, str], Router]) -> None:
        """Check policy references against base and its configured router interfaces."""
        asns = set(base.getAsns())
        referenced = set(self.__masked_asns)
        for declarations in (self.__networks, self.__routers, self.__interfaces, self.__stubs, self.__masked):
            referenced.update(key[0] for key in declarations)
        if referenced - asns:
            raise ValueError("RIP references unknown ASNs: {}".format(sorted(referenced - asns)))
        for asn, name in self.__routers:
            if (asn, name) not in routers:
                raise ValueError("RIP references unknown router AS{}/{}".format(asn, name))
        for asn, name, network in self.__interfaces:
            node = routers.get((asn, name))
            attached = {iface.getNet().getName() for iface in node.getInterfaces()} if node else set()
            if node is None or network not in attached | {"dummy0"}:
                raise ValueError("RIP references unknown interface AS{}/{}/{}".format(asn, name, network))
        for asn, network in set(self.__networks) | self.__stubs | self.__masked:
            available = set(base.getAutonomousSystem(asn).getNetworks()) | {"dummy0"}
            for (router_asn, _), node in routers.items():
                if router_asn == asn:
                    available.update(iface.getNet().getName() for iface in node.getInterfaces())
            if network not in available:
                raise ValueError("RIP references unknown network AS{}/{}".format(asn, network))

    def _resolveOptions(self, router: Router, network: str, passive: bool) -> Dict[str, Any]:
        """Resolve all option scopes for router's network, with topology passive default."""
        asn, name = router.getAsn(), router.getName()
        options = {"passive": passive, **self.__defaults}
        options.update(self.__networks.get((asn, network), {}))
        options.update(self.__routers.get((asn, name), {}))
        options.update(self.__interfaces.get((asn, name, network), {}))
        if (asn, network) in self.__stubs:
            options["passive"] = True
        validate_rip_options(options)
        return options

    def configure(self, emulator: Emulator):
        """Derive per-node RIP intents from emulator's fully configured Base layer."""
        registry = emulator.getRegistry()
        base = registry.get("seedemu", "layer", "Base")
        routers = {
            (node.getAsn(), node.getName()): node
            for (_, kind, _), node in registry.getAll().items() if kind == "rnode"
        }
        self._validateTargets(base, routers)
        for (asn, name), router in routers.items():
            autonomous_system = base.getAutonomousSystem(asn)
            if autonomous_system.getIgpMode() != "rip":
                continue
            interface_policy = autonomous_system.getIgpInterfacePolicy()
            defaults = {**self.__defaults, **self.__routers.get((asn, name), {})}
            validate_rip_options(defaults)
            if asn in self.__masked_asns or self.__routers.get((asn, name), {}).get("enabled") is False:
                continue
            interfaces = []
            for iface in router.getInterfaces():
                network = iface.getNet()
                netname = network.getName()
                if self.isMasked(asn, netname):
                    continue
                external = network.getType() != NetworkType.Local
                options = self._resolveOptions(router, netname, not is_igp_active_network(network, interface_policy))
                if not options["enabled"]:
                    continue
                # AS isolation overrides an explicit active option on external links.
                if external:
                    options["passive"] = True
                interfaces.append({
                    "name": netname, "prefix": str(network.getPrefix()),
                    "exchange": not external, "options": options,
                })
            if defaults["advertise_loopback"] and not self.isMasked(asn, "dummy0"):
                options = self._resolveOptions(router, "dummy0", True)
                if options["enabled"]:
                    options["passive"] = True
                    interfaces.append({
                        "name": "dummy0", "prefix": "{}/32".format(router.getLoopbackAddress()),
                        "exchange": False, "options": options,
                    })
            if not interfaces:
                continue
            set_igp_protocol(router, "rip")
            set_rip_interface_intents(
                router, sorted(interfaces, key=lambda item: item["name"]), defaults=defaults,
            )
            self._log("configured RIP intent for AS{}/{}".format(asn, name))

    def print(self, indent: int) -> str:
        return "{}RipLayer:\n{}{}\n".format(" " * indent, " " * (indent + 4), self.getConfiguration())

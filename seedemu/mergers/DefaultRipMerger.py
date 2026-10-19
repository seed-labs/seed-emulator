"""Merge RIP components without losing policy declarations or timer settings."""

from seedemu.core import Merger
from seedemu.layers import Rip
from seedemu.layers._igp_metadata import RIP_DEFAULTS


class DefaultRipMerger(Merger):
    """Combine scoped policies and nondefault defaults; reject conflicting values."""

    def getName(self) -> str:
        return "DefaultRipMerger"

    def getTargetType(self) -> str:
        return "RipLayer"

    def doMerge(self, objectA: Rip, objectB: Rip) -> Rip:
        """Merge objectA and objectB, preserving inputs and rejecting conflicts."""
        first, second = objectA.getConfiguration(), objectB.getConfiguration()
        merged = Rip()
        defaults = {}
        for key in set(first["defaults"]) | set(second["defaults"]):
            a = first["defaults"].get(key, RIP_DEFAULTS.get(key))
            b = second["defaults"].get(key, RIP_DEFAULTS.get(key))
            default = RIP_DEFAULTS.get(key)
            if a != b and a != default and b != default:
                raise ValueError("conflicting RIP defaults for {}: {} and {}".format(key, a, b))
            defaults[key] = b if a == default else a
        merged.setDefaults(**defaults)
        for scope, setter in (
            ("networks", merged.setNetworkOptions), ("routers", merged.setRouterOptions),
            ("interfaces", merged.setInterfaceOptions),
        ):
            for target in sorted(set(first[scope]) | set(second[scope])):
                a, b = first[scope].get(target, {}), second[scope].get(target, {})
                for key in set(a) & set(b):
                    if a[key] != b[key]:
                        raise ValueError("conflicting RIP {} options for {}: {}".format(scope, target, key))
                setter(*target, **{**a, **b})
        for asn, network in first["stubs"] | second["stubs"]:
            merged.markAsStub(asn, network)
        for asn, network in first["masked"] | second["masked"]:
            merged.maskNetwork(asn, network)
        for asn in first["masked_asns"] | second["masked_asns"]:
            merged.maskAsn(asn)
        return merged

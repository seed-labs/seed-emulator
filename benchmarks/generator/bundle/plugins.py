"""Versioned plugin registry shared by all bundle-producing agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class PluginDescriptor:
    plugin_id: str
    kind: str
    version: str
    platforms: Tuple[str, ...]
    capabilities_required: Tuple[str, ...] = ()
    mutates: Tuple[str, ...] = ()
    blind_safe: bool = True
    supports_sampling: bool = False

    def to_dict(self):
        return asdict(self)


class PluginRegistry:
    """Fail-closed registry: duplicate IDs and unknown plugins are errors."""

    def __init__(self):
        self._plugins: Dict[str, PluginDescriptor] = {}

    def register(self, descriptor: PluginDescriptor) -> None:
        if descriptor.plugin_id in self._plugins:
            raise ValueError(f"duplicate plugin={descriptor.plugin_id}")
        if descriptor.kind not in {
            "topology", "software", "service", "workload", "fault",
            "probe", "oracle", "scoring",
        }:
            raise ValueError("invalid plugin kind")
        if not descriptor.platforms:
            raise ValueError("plugin must declare a platform")
        self._plugins[descriptor.plugin_id] = descriptor

    def require(self, plugin_id: str, *, kind: str) -> PluginDescriptor:
        try:
            descriptor = self._plugins[plugin_id]
        except KeyError as exc:
            raise ValueError(f"unregistered {kind} plugin={plugin_id}") from exc
        if descriptor.kind != kind:
            raise ValueError(
                f"plugin {plugin_id} is {descriptor.kind}, expected {kind}"
            )
        return descriptor

    def inventory(self) -> Tuple[PluginDescriptor, ...]:
        return tuple(self._plugins[key] for key in sorted(self._plugins))


def builtin_registry(fault_drivers: Iterable[str] = ()) -> PluginRegistry:
    registry = PluginRegistry()
    for descriptor in (
        PluginDescriptor("service.process", "service", "1.0.0", ("docker",), mutates=("process",)),
        PluginDescriptor("service.systemd", "service", "1.0.0", ("docker",), mutates=("process",)),
        PluginDescriptor("workload.http", "workload", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("workload.dns", "workload", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("workload.tcp", "workload", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("workload.udp", "workload", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("workload.icmp", "workload", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("probe.http", "probe", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("probe.dns", "probe", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("probe.tcp", "probe", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("probe.container", "probe", "1.0.0", ("docker",)),
        PluginDescriptor("probe.file", "probe", "1.0.0", ("docker",)),
        PluginDescriptor("probe.metric", "probe", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("probe.routing", "probe", "1.0.0", ("docker",), supports_sampling=True),
        PluginDescriptor("oracle.assertion", "oracle", "1.0.0", ("portable",)),
        PluginDescriptor("scoring.weighted", "scoring", "1.0.0", ("portable",)),
    ):
        registry.register(descriptor)
    for driver in sorted(set(fault_drivers)):
        registry.register(
            PluginDescriptor(
                driver, "fault", "1.0.0", ("docker",),
                mutates=("declared-resource-lock",),
            )
        )
    return registry

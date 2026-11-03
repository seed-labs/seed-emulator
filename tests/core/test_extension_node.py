from pathlib import Path

import pytest
import yaml

from seedemu.compiler import Docker
from seedemu.core import (
    AutonomousSystem,
    Binding,
    Emulator,
    ExtensionNode,
    Node,
    Router,
    ScopeType,
)
from seedemu.core.enums import NodeRole
from seedemu.layers import Base


class RecordingExtensionNode(ExtensionNode):
    def __init__(self, name: str, asn: int):
        super().__init__(name, asn)
        self.configure_calls = 0

    def configure(self, emulator: Emulator):
        self.configure_calls += 1
        super().configure(emulator)


def _file_map(node: Node) -> dict[str, str]:
    return dict(file.get() for file in node.getFiles())


def _render_with_base(
    *autonomous_systems: AutonomousSystem,
    explicitly_configured_nodes: tuple[ExtensionNode, ...] = (),
) -> tuple[Emulator, Base]:
    emulator = Emulator()
    base = Base()
    for autonomous_system in autonomous_systems:
        base.setAutonomousSystem(autonomous_system)
    for node in explicitly_configured_nodes:
        for option in base.getAvailableOptions():
            node.setOption(option)
    emulator.addLayer(base)
    emulator.render()
    return emulator, base


def test_extension_node_identity_scope_and_public_import():
    node = ExtensionNode("extension-0", 150)

    assert isinstance(node, Node)
    assert not isinstance(node, Router)
    assert node.getRole() is NodeRole.ExtensionNode
    assert node.scope().type is ScopeType.EXTNODE


def test_extension_scope_does_not_change_legacy_any_scope():
    legacy_any = (
        ScopeType.RNODE
        | ScopeType.HNODE
        | ScopeType.CSNODE
        | ScopeType.BRDNODE
    )

    assert ScopeType.ANY == legacy_any
    assert not ScopeType.ANY & ScopeType.EXTNODE
    assert not ScopeType.ANY & ScopeType.RSNODE


def test_as_inventory_and_lifecycle_without_name_server_inheritance():
    autonomous_system = AutonomousSystem(150)
    extension = RecordingExtensionNode("extension-0", 150)
    autonomous_system.addExtensionNode(extension)
    autonomous_system.setNameServers(["1.1.1.1"])
    emulator, _ = _render_with_base(autonomous_system)

    registry = emulator.getRegistry()
    assert autonomous_system.getExtensionNodes() == ["extension-0"]
    assert autonomous_system.getExtensionNode("extension-0") is extension
    assert registry.get("150", "extnode", "extension-0") is extension
    assert extension.configure_calls == 1
    assert extension.getNameServers() == []
    assert _file_map(extension)["/ifinfo.txt"] == ""
    assert "/interface_setup" in _file_map(extension)
    assert Binding("^service$").getCandidate("service", emulator) is None


def test_extension_node_does_not_inherit_legacy_generic_options():
    first_as = AutonomousSystem(150)
    first = RecordingExtensionNode("extension-0", 150)
    first_as.addExtensionNode(first)

    second_as = AutonomousSystem(151)
    second = RecordingExtensionNode("extension-1", 151)
    second_as.addExtensionNode(second)

    emulator = Emulator()
    base = Base()
    base.setAutonomousSystem(first_as)
    base.setAutonomousSystem(second_as)
    first_as.setOption(base.getAvailableOptions()[0])
    emulator.addLayer(base)
    emulator.render()

    assert first.getScopedOptions() == []
    assert second.getScopedOptions() == []


def test_as_inventory_validates_type_asn_and_type_group_collisions():
    autonomous_system = AutonomousSystem(150)
    extension = ExtensionNode("shared-name", 150)

    assert autonomous_system.addExtensionNode(extension) is extension
    autonomous_system.createHost("shared-name")
    autonomous_system.createRouter("shared-name")

    with pytest.raises(AssertionError, match="already exists"):
        autonomous_system.addExtensionNode(
            ExtensionNode("shared-name", 150)
        )
    with pytest.raises(AssertionError, match="different AS"):
        autonomous_system.addExtensionNode(ExtensionNode("foreign", 151))
    with pytest.raises(AssertionError, match="must be an ExtensionNode"):
        autonomous_system.addExtensionNode(
            Node("host-like", NodeRole.Host, 150)
        )


def test_docker_compiles_zero_interface_extension_node(tmp_path: Path):
    autonomous_system = AutonomousSystem(150)
    isolated = ExtensionNode("isolated", 150)
    isolated.setLabel("example.identity", "isolated")
    autonomous_system.addExtensionNode(isolated)
    emulator, _ = _render_with_base(
        autonomous_system,
        explicitly_configured_nodes=(isolated,),
    )
    output = tmp_path / "output"

    emulator.compile(
        Docker(
            internetMapEnabled=False,
            namingScheme="as{asn}{role}-{name}-{primaryIp}",
        ),
        str(output),
    )

    compose_text = (output / "docker-compose.yml").read_text()
    compose = yaml.safe_load(compose_text)
    service = compose["services"]["extnode_150_isolated"]
    assert service["network_mode"] == "none"
    assert "networks" not in service
    assert compose["networks"] == {}
    assert service["container_name"] == "as150ext-isolated-"
    assert (
        service["labels"]["org.seedsecuritylabs.seedemu.meta.role"]
        == "ExtensionNode"
    )
    assert (
        service["labels"][
            "org.seedsecuritylabs.seedemu.meta.example.identity"
        ]
        == "isolated"
    )
    assert isinstance(service["build"], str)


def test_docker_compiles_connected_extnode_without_changing_legacy_nodes(
    tmp_path: Path,
):
    autonomous_system = AutonomousSystem(150)
    autonomous_system.createNetwork("net0", "10.150.0.0/24")

    extension = ExtensionNode("connected", 150)
    extension.joinNetwork("net0", "10.150.0.10")
    autonomous_system.addExtensionNode(extension)

    host = autonomous_system.createHost("host-0")
    host.joinNetwork("net0")
    router = autonomous_system.createRouter("router-0")
    router.joinNetwork("net0")
    router.joinNetwork("ix100")

    emulator = Emulator()
    base = Base()
    base.createInternetExchange(100)
    base.setAutonomousSystem(autonomous_system)
    for option in base.getAvailableOptions():
        extension.setOption(option)
    emulator.addLayer(base)
    emulator.render()
    output = tmp_path / "output"
    emulator.compile(Docker(internetMapEnabled=False), str(output))

    compose = yaml.safe_load((output / "docker-compose.yml").read_text())
    services = compose["services"]
    extension_service = services["extnode_150_connected"]
    assert extension_service["networks"]["net_150_net0"][
        "ipv4_address"
    ] == "10.150.0.10"
    assert "network_mode" not in extension_service

    legacy_services = {
        service["labels"]["org.seedsecuritylabs.seedemu.meta.nodename"]: service
        for service in services.values()
        if "org.seedsecuritylabs.seedemu.meta.nodename"
        in service.get("labels", {})
    }
    for node_name in ("host-0", "router-0"):
        service = legacy_services[node_name]
        assert service["networks"]
        assert "network_mode" not in service
        assert isinstance(service["build"], str)
    assert "net_ix_ix100" in legacy_services["router-0"]["networks"]

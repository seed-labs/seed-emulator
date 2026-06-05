from __future__ import annotations

import importlib.util
import subprocess
import socket
import sys
import textwrap
import types
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent
CORE = ROOT / "seedemu" / "core"
LAYERS = ROOT / "seedemu" / "layers"


def _load_core_module(name: str, filename: str):
    """Load a core module without importing top-level seedemu optional deps."""

    package_name = "seedemu"
    core_name = "seedemu.core"
    if package_name not in sys.modules:
        package_spec = importlib.util.spec_from_loader(package_name, loader=None, is_package=True)
        package = importlib.util.module_from_spec(package_spec)
        package.__path__ = [str(ROOT / "seedemu")]
        sys.modules[package_name] = package

    if core_name not in sys.modules:
        core_spec = importlib.util.spec_from_loader(core_name, loader=None, is_package=True)
        core = importlib.util.module_from_spec(core_spec)
        core.__path__ = [str(CORE)]
        sys.modules[core_name] = core

    module_name = "{}.{}".format(core_name, name)
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, CORE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _ensure_core_exports_for_layer_imports():
    """Expose core symbols needed by direct layer module loading."""

    core = sys.modules["seedemu.core"]
    exports = {
        "AddressAssignmentConstraint": ("AddressAssignmentConstraint", "AddressAssignmentConstraint"),
        "AutonomousSystem": ("AutonomousSystem", "AutonomousSystem"),
        "DEFAULT_IPV6_ROOT_PREFIX": ("Ipv6Addressing", "DEFAULT_IPV6_ROOT_PREFIX"),
        "Emulator": ("Emulator", "Emulator"),
        "Graphable": ("Graphable", "Graphable"),
        "InternetExchange": ("InternetExchange", "InternetExchange"),
        "Ipv6Addressing": ("Ipv6Addressing", "Ipv6Addressing"),
        "Layer": ("Layer", "Layer"),
        "Node": ("Node", "Node"),
        "normalizeAddressList": ("Addressing", "normalizeAddressList"),
        "normalizePrefix": ("Addressing", "normalizePrefix"),
    }
    for export_name, (module_name, attr_name) in exports.items():
        module = _load_core_module(module_name, "{}.py".format(module_name))
        setattr(core, export_name, getattr(module, attr_name))


def _load_layer_module(name: str, filename: str):
    _ensure_core_exports_for_layer_imports()
    if "seedemu.options.Sysctl" not in sys.modules:
        options = types.ModuleType("seedemu.options")
        options.__path__ = [str(ROOT / "seedemu" / "options")]
        sys.modules.setdefault("seedemu.options", options)
        sysctl = types.ModuleType("seedemu.options.Sysctl")

        class SysctlOpts:
            def components_recursive(self):
                return []

        sysctl.SysctlOpts = SysctlOpts
        sys.modules["seedemu.options.Sysctl"] = sysctl

    layers_name = "seedemu.layers"
    if layers_name not in sys.modules:
        layers_spec = importlib.util.spec_from_loader(layers_name, loader=None, is_package=True)
        layers = importlib.util.module_from_spec(layers_spec)
        layers.__path__ = [str(LAYERS)]
        sys.modules[layers_name] = layers

    module_name = "{}.{}".format(layers_name, name)
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(module_name, LAYERS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


Addressing = _load_core_module("Addressing", "Addressing.py")
Ipv6AddressingModule = _load_core_module("Ipv6Addressing", "Ipv6Addressing.py")

AddressFamily = Addressing.AddressFamily
Ipv6Addressing = Ipv6AddressingModule.Ipv6Addressing


def _run_real_docker_compile(tmp_path, setup_code: str):
    """Compile through the real Docker module in a clean Python process."""

    output = tmp_path / "output_{}".format(len(list(tmp_path.glob("output_*"))))
    setup_code = textwrap.dedent(setup_code).strip()
    script = textwrap.dedent(
        """
        from pathlib import Path
        import importlib.util
        import sys
        import types

        ROOT = Path({root!r})
        OUTPUT = Path({output!r})

        seedemu = types.ModuleType("seedemu")
        seedemu.__path__ = [str(ROOT / "seedemu")]
        sys.modules["seedemu"] = seedemu
        for name in ["core", "layers", "compiler"]:
            module = types.ModuleType("seedemu." + name)
            module.__path__ = [str(ROOT / "seedemu" / name)]
            sys.modules["seedemu." + name] = module

        spec = importlib.util.spec_from_file_location(
            "seedemu.core",
            ROOT / "seedemu" / "core" / "__init__.py",
            submodule_search_locations=[str(ROOT / "seedemu" / "core")],
        )
        core = importlib.util.module_from_spec(spec)
        sys.modules["seedemu.core"] = core
        spec.loader.exec_module(core)

        from seedemu.core.Emulator import Emulator
        from seedemu.layers.Base import Base
        from seedemu.compiler.Docker import Docker

        {setup_code}
        """
    ).format(root=str(ROOT), output=str(output), setup_code=setup_code)
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=str(ROOT),
        check=True,
        text=True,
        capture_output=True,
    )
    compose_text = (output / "docker-compose.yml").read_text()
    return compose_text, yaml.safe_load(compose_text)


def _load_seedemu_class(module_name: str, class_name: str):
    if module_name == "Base":
        module = _load_layer_module(module_name, "{}.py".format(module_name))
        return getattr(module, class_name)
    module = _load_core_module(module_name, "{}.py".format(module_name))
    return getattr(module, class_name)


def test_endpoint_helpers_preserve_ipv4_and_bracket_ipv6():
    assert Addressing.formatHost(" 10.0.0.1 ") == "10.0.0.1"
    assert Addressing.formatHost(" example.test ") == "example.test"
    assert Addressing.formatHost(" 2000:0:0::1 ") == "[2000::1]"
    assert Addressing.formatHost(" [2000:0:0::1]:8443 ") == "[2000::1]:8443"

    assert Addressing.formatHostPort("10.0.0.1", 80) == "10.0.0.1:80"
    assert Addressing.formatHostPort("2000::1", " 80 ") == "[2000::1]:80"
    assert Addressing.formatHostPort("[2000:0:0::1]:8443", 9443) == "[2000::1]:9443"

    assert Addressing.formatUrl("http", "10.0.0.1", 8080, "api") == "http://10.0.0.1:8080/api"
    assert Addressing.formatUrl("http", "2000::1", 8080, "?ready=1") == "http://[2000::1]:8080?ready=1"

    assert Addressing.formatMultiaddr("10.0.0.1", 4001) == "/ip4/10.0.0.1/tcp/4001"
    assert Addressing.formatMultiaddr("2000::1", " 4001 ", "peer") == "/ip6/2000::1/tcp/4001/p2p/peer"


def test_endpoint_helpers_reject_ambiguous_ports_and_authorities():
    with pytest.raises(ValueError):
        Addressing.formatHost("[2000::1]:bad")
    with pytest.raises(ValueError):
        Addressing.formatHostPort("2000::1", "")
    with pytest.raises(ValueError):
        Addressing.formatHostPort("2000::1", "http")
    with pytest.raises(ValueError):
        Addressing.formatMultiaddr("example.test", 4001)


def test_address_normalization_contracts():
    assert Addressing.normalizeAddressFamily(" ipv4 ") == AddressFamily.IPv4
    assert Addressing.normalizeAddressFamily(" IP6 ") == AddressFamily.IPv6
    assert Addressing.normalizeAddressFamily("inet") == AddressFamily.IPv4
    assert Addressing.normalizeAddressFamily("AF_INET6") == AddressFamily.IPv6
    assert Addressing.normalizeAddressFamily(socket.AF_INET) == AddressFamily.IPv4
    assert Addressing.normalizeAddressFamily(socket.AF_INET6) == AddressFamily.IPv6

    assert Addressing.normalizeAddressList([" 10.2.0.71 ", " [2000:0:2:0:0:0:0:71] "]) == [
        "10.2.0.71",
        "2000:0:2::71",
    ]
    assert Addressing.normalizePrefix(" [2000:0:2:0:0:0:0:0] / 64 ") == "2000:0:2::/64"
    assert Addressing.normalizePrefix(" 10.2.0.71/24 ", strict=False) == "10.2.0.0/24"

    assert Addressing.normalizeAddressRecord(" web a 10.2.0.71 ") == "web A 10.2.0.71"
    assert Addressing.normalizeAddressRecord(" web6 aaaa [2000:0:2:0:0:0:0:71] ") == "web6 AAAA 2000:0:2::71"
    assert Addressing.normalizeAddressRecord(" ns1. NS a.root.example. ", trimNonAddressRecord=True) == "ns1. NS a.root.example."
    with pytest.raises(ValueError):
        Addressing.normalizeAddressRecord("web A 2000:0:2::71")
    with pytest.raises(ValueError):
        Addressing.normalizeAddressRecord("web AAAA 10.2.0.71")


def test_ipv6_allocator_is_deterministic_and_avoids_claimed_prefixes():
    allocator = Ipv6Addressing(rootPrefix="2000::/12")

    assert str(allocator.getRootPrefix()) == "2000::/12"
    assert "2000:ffff::/48" in [str(prefix) for prefix in allocator.getReservedPrefixes()]
    assert str(allocator.assignAsPrefix(150)) == "2000:0:96::/48"
    assert str(allocator.nextAsNetworkPrefix(150)) == "2000:0:96::/64"
    assert str(allocator.assignIxPrefix(100)) == "2000:8:0:64::/64"

    claimed = Ipv6Addressing(rootPrefix="2000::/12")
    claimed.claimPrefix("2000:0:97::/48")
    assert str(claimed.assignAsPrefix(151)) != "2000:0:97::/48"


def test_ipv6_allocator_rejects_root_overlap_but_allows_disjoint_user_prefixes():
    allocator = Ipv6Addressing(rootPrefix="2000::/12")
    allocator.claimPrefix("fd00:1::/64")

    with pytest.raises(AssertionError):
        allocator.claimPrefix("2000::/11")

    with pytest.raises(AssertionError):
        allocator.claimPrefix("2000:ffff::/64")


def test_topology_ipv6_is_opt_in_and_preserves_ipv4_accessors():
    Base = _load_seedemu_class("Base", "Base")

    base = Base()
    as150 = base.createAutonomousSystem(150)
    net = as150.createNetwork("net0")
    host = as150.createHost("host").joinNetwork("net0", address="10.150.0.71")

    assert not base.isIpv6Enabled()
    assert str(net.getPrefix()) == "10.150.0.0/24"
    assert not net.hasIpv6Prefix()

    class _Registry:
        def has(self, scope, type, name):
            return scope == "150" and type == "net" and name == "net0"

        def get(self, scope, type, name):
            return net

    class _Emulator:
        def getRegistry(self):
            return _Registry()

    host.configure(_Emulator())
    iface = host.getInterfaces()[0]

    assert str(iface.getAddress()) == "10.150.0.71"
    assert not iface.hasIpv6Address()
    assert iface.getIpv6Address() is None


def test_base_enable_ipv6_backfills_networks_and_interfaces():
    Base = _load_seedemu_class("Base", "Base")

    base = Base()
    as150 = base.createAutonomousSystem(150)
    net = as150.createNetwork("net0")
    host = as150.createHost("host").joinNetwork("net0")

    base.enableIpv6()

    assert base.isIpv6Enabled()
    assert str(base.getIpv6RootPrefix()) == "2000::/12"
    assert str(net.getIpv6Prefix()) == "2000:0:96::/64"

    class _Registry:
        def has(self, scope, type, name):
            return scope == "150" and type == "net" and name == "net0"

        def get(self, scope, type, name):
            return net

    class _Emulator:
        def getRegistry(self):
            return _Registry()

    host.configure(_Emulator())
    iface = host.getInterfaces()[0]

    assert str(iface.getAddress()) == "10.150.0.71"
    assert str(iface.getIpv6Address()) == "2000:0:96::47"


def test_explicit_ipv6_prefix_address_and_opt_out():
    Base = _load_seedemu_class("Base", "Base")

    base = Base(enableIpv6=True)
    as151 = base.createAutonomousSystem(151)
    net = as151.createNetwork("net0", ipv6Prefix=" [2000:0:151::] / 64 ")
    fixed = as151.createHost("fixed").joinNetwork(
        "net0",
        address="10.151.0.10",
        ipv6Address=" [2000:0:151::10] ",
    )
    v4_only = as151.createHost("v4only").joinNetwork(
        "net0",
        address="10.151.0.11",
        ipv6Address=None,
    )

    assert str(net.getIpv6Prefix()) == "2000:0:151::/64"

    class _Registry:
        def has(self, scope, type, name):
            return scope == "151" and type == "net" and name == "net0"

        def get(self, scope, type, name):
            return net

    class _Emulator:
        def getRegistry(self):
            return _Registry()

    fixed.configure(_Emulator())
    v4_only.configure(_Emulator())

    assert str(fixed.getInterfaces()[0].getAddress()) == "10.151.0.10"
    assert str(fixed.getInterfaces()[0].getIpv6Address()) == "2000:0:151::10"
    assert str(v4_only.getInterfaces()[0].getAddress()) == "10.151.0.11"
    assert not v4_only.getInterfaces()[0].hasIpv6Address()

    with pytest.raises(AssertionError):
        as151.createHost("bad").joinNetwork("net0", ipv6Address="2000:0:152::1").configure(_Emulator())


def test_ix_ipv6_prefix_and_route_server_address_are_explicit():
    Base = _load_seedemu_class("Base", "Base")

    base = Base(enableIpv6=True)
    ix = base.createInternetExchange(
        100,
        ipv6Prefix="2000:8:0:100::/64",
        rsIpv6Address="2000:8:0:100::100",
    )
    net = ix.getPeeringLan()

    assert str(net.getIpv6Prefix()) == "2000:8:0:100::/64"

    rs = ix.getRouteServerNode()

    class _Registry:
        def has(self, scope, type, name):
            return scope == "ix" and type == "net" and name == "ix100"

        def get(self, scope, type, name):
            return net

    class _Emulator:
        def getRegistry(self):
            return _Registry()

    rs.configure(_Emulator())
    iface = rs.getInterfaces()[0]

    assert str(iface.getAddress()) == "10.100.0.100"
    assert str(iface.getIpv6Address()) == "2000:8:0:100::100"


def test_router_backend_legacy_values_stay_rejected():
    Router = _load_seedemu_class("Node", "Router")
    NodeRole = _load_core_module("enums", "enums.py").NodeRole

    router = Router("r1", NodeRole.Router, 150)
    assert router.getRoutingBackend() == "bird"
    router.setRoutingBackend("frr")
    assert router.getRoutingBackend() == "frr"

    with pytest.raises(AssertionError):
        router.setRoutingBackend("exabgp")
    with pytest.raises(AssertionError):
        router.setRoutingBackend("external")


def test_docker_compiler_keeps_ipv4_default_compose_ipv4_only(tmp_path):
    compose_text, compose = _run_real_docker_compile(
        tmp_path,
        """
        emu = Emulator()
        base = Base()
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        emu.addLayer(base)
        emu.render()
        emu.compile(Docker(internetMapEnabled=False), str(OUTPUT), override=True)
        """,
    )

    assert "enable_ipv6" not in compose_text
    assert "ipv6_address" not in compose_text

    net = compose["networks"]["net_150_net0"]
    assert "enable_ipv6" not in net
    assert net["ipam"]["config"] == [{"subnet": "10.150.0.0/24"}]

    service_net = compose["services"]["hnode_150_h1"]["networks"]["net_150_net0"]
    assert service_net == {"ipv4_address": "10.150.0.71"}


def test_docker_compiler_emits_ipv6_only_for_ipv6_interfaces(tmp_path):
    _, compose = _run_real_docker_compile(
        tmp_path,
        """
        emu = Emulator()
        base = Base(enableIpv6=True)
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        as150.createHost("v4only").joinNetwork("net0", ipv6Address=None)
        emu.addLayer(base)
        emu.render()
        emu.compile(Docker(internetMapEnabled=False), str(OUTPUT), override=True)
        """,
    )

    net = compose["networks"]["net_150_net0"]
    assert net["enable_ipv6"] is True
    assert net["ipam"]["config"] == [
        {"subnet": "10.150.0.0/24"},
        {"subnet": "2000:0:96::/64"},
    ]
    assert net["labels"]["org.seedsecuritylabs.seedemu.meta.ipv6_prefix"] == "2000:0:96::/64"

    h1_net = compose["services"]["hnode_150_h1"]["networks"]["net_150_net0"]
    assert h1_net["ipv4_address"] == "10.150.0.71"
    assert h1_net["ipv6_address"] == "2000:0:96::47"

    v4only_net = compose["services"]["hnode_150_v4only"]["networks"]["net_150_net0"]
    assert v4only_net == {"ipv4_address": "10.150.0.72"}


def test_service_network_ipv6_is_explicit(tmp_path):
    _, default_compose = _run_real_docker_compile(
        tmp_path,
        """
        emu = Emulator()
        base = Base()
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        emu.addLayer(base)
        emu.getServiceNetwork()
        emu.render()
        emu.compile(Docker(internetMapEnabled=False), str(OUTPUT), override=True)
        """,
    )

    default_service_net = default_compose["networks"]["000_svc"]
    assert "enable_ipv6" not in default_service_net
    assert default_service_net["ipam"]["config"] == [{"subnet": "192.168.66.0/24"}]

    _, ipv6_compose = _run_real_docker_compile(
        tmp_path,
        """
        emu = Emulator(serviceNetworkIpv6Prefix=" fd00:66:: / 64 ")
        base = Base()
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        emu.addLayer(base)
        emu.getServiceNetwork()
        emu.render()
        emu.compile(Docker(internetMapEnabled=False), str(OUTPUT), override=True)
        """,
    )

    ipv6_service_net = ipv6_compose["networks"]["000_svc"]
    assert ipv6_service_net["enable_ipv6"] is True
    assert ipv6_service_net["ipam"]["config"] == [
        {"subnet": "192.168.66.0/24"},
        {"subnet": "fd00:66::/64"},
    ]


def test_custom_container_and_internet_map_ipv6_attachment_is_explicit(tmp_path):
    _, compose = _run_real_docker_compile(
        tmp_path,
        """
        emu = Emulator()
        base = Base(enableIpv6=True)
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        emu.addLayer(base)
        emu.render()

        docker = Docker(internetMapEnabled=False)
        docker.attachCustomContainer(
            "    probe_v4:\\n        image: alpine:latest\\n",
            asn=150,
            net="net0",
            ip_address="10.150.0.200",
            show_on_map=True,
            node_name="probe_v4",
        )
        docker.attachInternetMap(
            asn=150,
            net="net0",
            ip_address=" 10.150.0.201 ",
            ipv6_address=" [2000:0:96::201] ",
            node_name="seedemu_internet_map",
        )
        emu.compile(docker, str(OUTPUT), override=True)
        """,
    )

    probe_net = compose["services"]["probe_v4"]["networks"]["net_150_net0"]
    assert probe_net == {"ipv4_address": "10.150.0.200"}
    assert "org.seedsecuritylabs.seedemu.meta.net.0.ipv6_address" not in compose["services"]["probe_v4"]["labels"]

    map_net = compose["services"]["seedemu_internet_map"]["networks"]["net_150_net0"]
    assert map_net["ipv4_address"] == "10.150.0.201"
    assert map_net["ipv6_address"] == "2000:0:96::201"


def test_custom_container_attachment_rejects_mismatched_address_families(tmp_path):
    _run_real_docker_compile(
        tmp_path,
        """
        docker = Docker(internetMapEnabled=False)
        try:
            docker.attachCustomContainer(
                "    bad_v4:\\n        image: alpine:latest\\n",
                asn=150,
                net="net0",
                ip_address="2000:0:96::202",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("IPv6 literal was accepted in ip_address")

        try:
            docker.attachInternetMap(
                asn=150,
                net="net0",
                ipv6_address="10.150.0.202",
            )
        except ValueError:
            pass
        else:
            raise AssertionError("IPv4 literal was accepted in ipv6_address")

        emu = Emulator()
        base = Base()
        as150 = base.createAutonomousSystem(150)
        as150.createNetwork("net0")
        as150.createHost("h1").joinNetwork("net0")
        emu.addLayer(base)
        emu.render()
        emu.compile(docker, str(OUTPUT), override=True)
        """,
    )

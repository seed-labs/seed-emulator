from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys

import pytest

from seedemu.compiler import Docker, Platform
from seedemu.core import Binding, Emulator, Filter
from seedemu.core.Node import DEFAULT_SOFTWARE
from seedemu.layers import Base, Ebgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.layers._bgp_metadata import set_bgp_backend
from seedemu.services import BgpLookingGlassService, ExaBgpService


def _file_content(node, path: str) -> str:
    for file in node.getFiles():
        file_path, content = file.get()
        if file_path == path:
            return content
    return ""


def _attach_exabgp_peer(server, router_name: str, *, router_asn: int):
    for method_name in ("addPeer", "addRouterPeer", "attachToRouter"):
        if not hasattr(server, method_name):
            continue
        method = getattr(server, method_name)
        try:
            return method(router_name, router_asn=router_asn)
        except TypeError:
            return method(router_name, router_asn)
    raise AssertionError("ExaBGP server does not expose a router peer attachment API")


def _compiled_output_text(output_dir: Path) -> str:
    chunks = []
    for path in output_dir.rglob("*"):
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def test_default_node_software_uses_installable_netcat_package():
    assert "netcat-openbsd" in DEFAULT_SOFTWARE
    assert "netcat" not in DEFAULT_SOFTWARE


def test_legacy_frr_bgp_layer_is_removed():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("seedemu.layers.FrrBgp")
    assert not hasattr(importlib.import_module("seedemu.layers"), "FrrBgp")


def test_router_rejects_legacy_exabgp_backends():
    as2 = Base().createAutonomousSystem(2)
    with pytest.raises(AssertionError, match="unsupported routing backend"):
        as2.createRouter("exabgp", routingBackend="exabgp")
    with pytest.raises(AssertionError, match="unsupported routing backend"):
        as2.createRouter("external", routingBackend="external")


def test_route_server_peering_renders_from_intent_in_routing_layer():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    base.createInternetExchange(100)
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork("net0")
    as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    ebgp.addRsPeer(100, 150)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.render()

    reg = emu.getRegistry()
    route_server = reg.get("ix", "rs", "ix100")
    router = reg.get("150", "rnode", "router0")

    rs_conf = _file_content(route_server, "/etc/bird/bird.conf")
    router_conf = _file_content(router, "/etc/bird/bird.conf")

    assert "protocol bgp p_as150" in rs_conf
    assert "rs client" in rs_conf
    assert "neighbor 10.100.0.150 as 150" in rs_conf
    assert "protocol bgp p_rs100" in router_conf
    assert "neighbor 10.100.0.100 as 100" in router_conf
    assert "bgp_large_community.add(PEER_COMM)" in router_conf


def test_frr_route_server_backend_is_explicitly_rejected():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    ix = base.createInternetExchange(100)
    set_bgp_backend(ix.getRouteServerNode(), "frr")
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork("net0")
    as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    ebgp.addRsPeer(100, 150)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)

    with pytest.raises(NotImplementedError, match="FRR route-server nodes are not supported yet"):
        emu.render()


def test_frr_backend_renders_frr_config_for_selected_router():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    ebgp = Ebgp()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix100")
    as2.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("ix101")

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork("net0")
    as152.createRouter("router0").joinNetwork("net0").joinNetwork("ix101")

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(ebgp)
    emu.render()

    reg = emu.getRegistry()
    r1 = reg.get("2", "rnode", "r1")
    r2 = reg.get("2", "rnode", "r2")

    assert any(cmd == "bird -d" for cmd, _ in r1.getStartCommands())
    assert not any(cmd == "bird -d" for cmd, _ in r2.getStartCommands())
    assert _file_content(r2, "/etc/bird/bird.conf") == ""

    frr_conf = _file_content(r2, "/etc/frr/frr.conf")
    assert "router bgp 2" in frr_conf
    assert "neighbor" in frr_conf
    assert "RM_CONNECTED_TO_BGP" in frr_conf
    assert "LC_LOCAL_OR_CUSTOMER" in frr_conf
    assert "router ospf" in frr_conf
    assert "interface net0" in frr_conf


def test_exabgp_service_renders_dashboard_and_router_peer():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as151.createHost("observer").joinNetwork("net0")

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)

    exabgp.install("observer_tool").attachToRouter("router0").setLocalAsn(65010).addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("observer_tool", filter=Filter(nodeName="observer", asn=151)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(exabgp)
    emu.render()

    reg = emu.getRegistry()
    observer = reg.get("151", "hnode", "observer")
    router = reg.get("151", "rnode", "router0")

    exabgp_conf = _file_content(observer, "/etc/exabgp/exabgp.conf")
    assert "198.51.100.0/24" in exabgp_conf
    assert "process exabgp_json_sink" in exabgp_conf
    assert "peer-as 151" in exabgp_conf

    dashboard = _file_content(observer, "/opt/exabgp/dashboard.py")
    assert "/api/events" in dashboard

    bird_conf = _file_content(router, "/etc/bird/bird.conf")
    assert "exabgp_65010" in bird_conf
    assert "peer table t_bgp" in bird_conf
    assert "bgp_large_community.add(CUSTOMER_COMM)" in bird_conf
    assert "bgp_local_pref = 30" in bird_conf


def test_exabgp_service_renders_frr_peer_without_bird_config():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    ebgp = Ebgp()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0", routingBackend="frr").joinNetwork("net0").joinNetwork("ix100")
    as2.createHost("observer").joinNetwork("net0")

    exabgp.install("observer_tool").attachToRouter("router0").setLocalAsn(65010).addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("observer_tool", filter=Filter(nodeName="observer", asn=2)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(ebgp)
    emu.addLayer(exabgp)
    emu.render()

    reg = emu.getRegistry()
    router = reg.get("2", "rnode", "router0")
    observer = reg.get("2", "hnode", "observer")

    assert _file_content(router, "/etc/bird/bird.conf") == ""
    frr_conf = _file_content(router, "/etc/frr/frr.conf")
    assert "neighbor 10.2.0.71 remote-as 65010" in frr_conf
    assert "description exabgp_65010" in frr_conf
    assert "address-family ipv4 unicast" in frr_conf

    exabgp_conf = _file_content(observer, "/etc/exabgp/exabgp.conf")
    assert "198.51.100.0/24" in exabgp_conf
    assert "peer-as 2" in exabgp_conf


def test_exabgp_service_renders_multi_peer_ix_speaker_config():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)
    as2 = base.createAutonomousSystem(2)
    as2.createRouter("r100").joinNetwork("ix100")
    as3 = base.createAutonomousSystem(3)
    as3.createRouter("r100").joinNetwork("ix100")
    speaker_as = base.createAutonomousSystem(65030)
    speaker_as.createHost("route_speaker").joinNetwork("ix100", address="10.100.0.230")

    speaker = exabgp.install("external_route_speaker")
    speaker.setLocalAsn(65030).addAnnouncement("203.0.113.0/24").enableDashboard(5000)
    _attach_exabgp_peer(speaker, "r100", router_asn=2)
    _attach_exabgp_peer(speaker, "r100", router_asn=3)
    emu.addBinding(Binding("external_route_speaker", filter=Filter(nodeName="route_speaker", asn=65030)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(exabgp)
    emu.render()

    reg = emu.getRegistry()
    route_speaker = reg.get("65030", "hnode", "route_speaker")
    as2_router = reg.get("2", "rnode", "r100")
    as3_router = reg.get("3", "rnode", "r100")

    exabgp_conf = _file_content(route_speaker, "/etc/exabgp/exabgp.conf")
    assert exabgp_conf.count("neighbor ") == 2
    assert "peer-as 2" in exabgp_conf
    assert "peer-as 3" in exabgp_conf
    assert "203.0.113.0/24" in exabgp_conf
    assert "process exabgp_json_sink" in exabgp_conf
    assert _file_content(route_speaker, "/etc/bird/bird.conf") == ""
    assert not any(cmd == "bird -d" for cmd, _ in route_speaker.getStartCommands())

    as2_conf = _file_content(as2_router, "/etc/bird/bird.conf")
    as3_conf = _file_content(as3_router, "/etc/bird/bird.conf")
    assert "exabgp_65030" in as2_conf
    assert "exabgp_65030" in as3_conf
    assert "neighbor 10.100.0.230 as 65030" in as2_conf
    assert "neighbor 10.100.0.230 as 65030" in as3_conf
    assert "bgp_large_community.add(CUSTOMER_COMM)" in as2_conf
    assert "bgp_large_community.add(CUSTOMER_COMM)" in as3_conf
    assert "bgp_local_pref = 30" in as2_conf
    assert "bgp_local_pref = 30" in as3_conf


def test_exabgp_service_renders_ix_speaker_peer():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)
    as2 = base.createAutonomousSystem(2)
    as2.createRouter("r100").joinNetwork("ix100")
    speaker_as = base.createAutonomousSystem(65030)
    speaker_as.createHost("external_speaker").joinNetwork("ix100", address="10.100.0.230")

    speaker = exabgp.install("external_route_speaker")
    speaker.setLocalAsn(65030).addAnnouncement("203.0.113.0/24")
    _attach_exabgp_peer(speaker, "r100", router_asn=2)
    emu.addBinding(Binding("external_route_speaker", filter=Filter(nodeName="external_speaker", asn=65030)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(exabgp)
    emu.render()

    reg = emu.getRegistry()
    external_speaker = reg.get("65030", "hnode", "external_speaker")
    as2_router = reg.get("2", "rnode", "r100")

    exabgp_conf = _file_content(external_speaker, "/etc/exabgp/exabgp.conf")
    assert "local-as 65030" in exabgp_conf
    assert "peer-as 2" in exabgp_conf
    assert "203.0.113.0/24" in exabgp_conf
    assert _file_content(external_speaker, "/etc/bird/bird.conf") == ""
    assert not any(cmd == "bird -d" for cmd, _ in external_speaker.getStartCommands())

    bird_conf = _file_content(as2_router, "/etc/bird/bird.conf")
    assert "exabgp_65030" in bird_conf
    assert "neighbor 10.100.0.230 as 65030" in bird_conf


def test_frr_bgp_respects_ospf_stub_intent():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createRouter("r1", routingBackend="frr").joinNetwork("net0").joinNetwork("net1")

    ospf.markAsStub(2, "net1")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.render()

    reg = emu.getRegistry()
    r1 = reg.get("2", "rnode", "r1")
    frr_conf = _file_content(r1, "/etc/frr/frr.conf")
    assert "interface net0" in frr_conf
    assert "interface net1" in frr_conf
    assert "ip ospf passive" in frr_conf


def test_bgp_looking_glass_supports_frr_router_route_state():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    looking_glass = BgpLookingGlassService()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0", routingBackend="frr").joinNetwork("net0")
    as2.createHost("lg").joinNetwork("net0")

    looking_glass.install("bgp_lg").attach("router0")
    emu.addBinding(Binding("bgp_lg", filter=Filter(nodeName="lg", asn=2)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(looking_glass)

    emu.render()

    reg = emu.getRegistry()
    lg = reg.get("2", "hnode", "lg")
    router = reg.get("2", "rnode", "router0")

    proxy = _file_content(router, "/opt/seed-lg/proxy.py")
    frontend = _file_content(lg, "/opt/seed-lg/frontend.py")
    proxy_cmds = [cmd for cmd, _ in router.getStartCommands()]

    assert "show bgp summary" in proxy
    assert "show ip ospf neighbor" in proxy
    assert "/api/state" in frontend
    assert any("SEED_LG_BACKEND=\"frr\"" in cmd for cmd in proxy_cmds)
    assert any("waiting for frr" in cmd for cmd in proxy_cmds)
    assert not any("waiting for bird" in cmd for cmd in proxy_cmds)


def test_new_bgp_examples_compile_outputs_exist():
    repo_root = Path(__file__).resolve().parents[2]
    examples = [
        repo_root / "examples" / "basic" / "A12_bgp_mixed_backend" / "bgp_mixed_backend.py",
        repo_root / "examples" / "basic" / "A13_exabgp_control_plane" / "exabgp_control_plane.py",
        repo_root / "examples" / "basic" / "A14_bgp_event_looking_glass" / "bgp_event_looking_glass.py",
    ]
    for script in examples:
        env = dict(**os.environ)
        env["PYTHONPATH"] = str(repo_root)
        result = subprocess.run(
            [sys.executable, str(script), "amd"],
            cwd=script.parent,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    for output_dir in [
        repo_root / "examples" / "basic" / "A12_bgp_mixed_backend" / "output",
        repo_root / "examples" / "basic" / "A13_exabgp_control_plane" / "output",
        repo_root / "examples" / "basic" / "A14_bgp_event_looking_glass" / "output",
    ]:
        assert output_dir.exists()
    a13_compose = (repo_root / "examples" / "basic" / "A13_exabgp_control_plane" / "output" / "docker-compose.yml").read_text(encoding="utf-8")
    a14_compose = (repo_root / "examples" / "basic" / "A14_bgp_event_looking_glass" / "output" / "docker-compose.yml").read_text(encoding="utf-8")
    assert "5001:5000/tcp" in a13_compose
    assert "5002:5000/tcp" in a14_compose
    assert "5003:5000/tcp" in a14_compose


def test_b30_mini_internet_exabgp_ix_compile_assertions():
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "examples" / "internet" / "B30_mini_internet_exabgp_ix" / "mini_internet_exabgp_ix.py"
    output_dir = script.parent / "output"

    env = dict(**os.environ)
    env["PYTHONPATH"] = str(repo_root)
    env["SEED_B30_EXABGP_PORT"] = "5130"
    result = subprocess.run(
        [sys.executable, str(script), "amd"],
        cwd=script.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert output_dir.exists()

    compose = (output_dir / "docker-compose.yml").read_text(encoding="utf-8")
    output_text = compose + "\n" + _compiled_output_text(output_dir)
    assert "5130:5000/tcp" in compose
    assert "203.0.113.0/24" in output_text
    assert "peer-as 2" in output_text
    assert "peer-as 3" in output_text
    assert "neighbor 10.100.0.180 as 180" in output_text
    assert "bgp_large_community.add(CUSTOMER_COMM)" in output_text
    assert "bgp_local_pref = 30" in output_text
    assert "process exabgp_json_sink" in output_text
    assert "dashboard.py" in output_text


def test_b30_mini_internet_exabgp_ix_emulator_compiles_from_builder():
    from examples.internet.B30_mini_internet_exabgp_ix import mini_internet_exabgp_ix

    emu = mini_internet_exabgp_ix.build_emulator()
    emu.render()
    output_dir = Path("/tmp/seedemu-b30-static-compile")
    emu.compile(Docker(selfManagedNetwork=True, platform=Platform.AMD64), str(output_dir), override=True)

    output_text = _compiled_output_text(output_dir)
    assert "203.0.113.0/24" in output_text
    assert "peer-as 2" in output_text
    assert "peer-as 3" in output_text

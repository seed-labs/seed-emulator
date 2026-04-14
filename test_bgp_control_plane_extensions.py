from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, FrrBgp, Ibgp, Ospf, PeerRelationship, Routing
from seedemu.services import BgpLookingGlassService, ExaBgpService


def _file_content(node, path: str) -> str:
    for file in node.getFiles():
        file_path, content = file.get()
        if file_path == path:
            return content
    return ""


def test_frr_bgp_layer_renders_frr_config_for_selected_router():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    ebgp = Ebgp()
    frr_bgp = FrrBgp()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix100")
    as2.createRouter("r2").joinNetwork("net0").joinNetwork("ix101")

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    as152 = base.createAutonomousSystem(152)
    as152.createNetwork("net0")
    as152.createRouter("router0").joinNetwork("net0").joinNetwork("ix101")

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 2, 152, abRelationship=PeerRelationship.Provider)
    frr_bgp.enableOn(2, "r2")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(ebgp)
    emu.addLayer(frr_bgp)
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
    assert "bgp_large_community.add(LOCAL_COMM)" in bird_conf


def test_exabgp_service_renders_frr_peer_without_bird_config():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    ebgp = Ebgp()
    frr_bgp = FrrBgp()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as2.createHost("observer").joinNetwork("net0")

    frr_bgp.enableOn(2, "router0")
    exabgp.install("observer_tool").attachToRouter("router0").setLocalAsn(65010).addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("observer_tool", filter=Filter(nodeName="observer", asn=2)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(ebgp)
    emu.addLayer(exabgp)
    emu.addLayer(frr_bgp)
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


def test_frr_bgp_respects_ospf_stub_intent():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    frr_bgp = FrrBgp()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("net1")

    ospf.markAsStub(2, "net1")
    frr_bgp.enableOn(2, "r1")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(frr_bgp)
    emu.render()

    reg = emu.getRegistry()
    r1 = reg.get("2", "rnode", "r1")
    frr_conf = _file_content(r1, "/etc/frr/frr.conf")
    assert "interface net0" in frr_conf
    assert "interface net1" in frr_conf
    assert "ip ospf passive" in frr_conf


def test_bgp_looking_glass_fails_fast_on_frr_router():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()
    frr_bgp = FrrBgp()
    looking_glass = BgpLookingGlassService()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0").joinNetwork("net0")
    as2.createHost("lg").joinNetwork("net0")

    frr_bgp.enableOn(2, "router0")
    looking_glass.install("bgp_lg").attach("router0")
    emu.addBinding(Binding("bgp_lg", filter=Filter(nodeName="lg", asn=2)))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.addLayer(frr_bgp)
    emu.addLayer(looking_glass)

    try:
        emu.render()
    except AssertionError as exc:
        assert "Bird routers only" in str(exc)
    else:
        raise AssertionError("BgpLookingGlassService should fail fast on FRR routers")


def test_new_bgp_examples_compile_outputs_exist():
    repo_root = Path(__file__).resolve().parent
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

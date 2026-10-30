from __future__ import annotations

import importlib

import pytest

from seedemu.core import Binding, Emulator, Filter
from seedemu.layers import Base, Ebgp, Ibgp, Mpls, Ospf, PeerRelationship, Routing
from seedemu.layers._bgp_metadata import get_bgp_sessions, get_ospf_interface_intents
from seedemu.services import ExaBgpService


def _file_content(node, path: str) -> str:
    for file in node.getFiles():
        file_path, content = file.get()
        if file_path == path:
            return content
    return ""


def test_router_backend_default_and_legacy_rejection():
    as2 = Base().createAutonomousSystem(2)
    assert as2.createRouter("default").getRoutingBackend() == "bird"
    assert as2.createRouter("frr", routingBackend="frr").getRoutingBackend() == "frr"

    with pytest.raises(AssertionError, match="unsupported routing backend"):
        as2.createRouter("exabgp", routingBackend="exabgp")
    with pytest.raises(AssertionError, match="unsupported routing backend"):
        as2.createRouter("external", routingBackend="external")


def test_as_level_control_plane_modes_are_explicit_intent():
    as2 = Base().createAutonomousSystem(2)

    assert as2.getIbgpMode() == "full-mesh"
    assert not as2.hasIbgpMode()
    assert as2.getOspfMode() == "legacy"
    assert not as2.hasOspfMode()

    as2.setIbgpMode("route-reflector")
    as2.setOspfMode("router-transit-only")
    assert as2.getIbgpMode() == "route-reflector"
    assert as2.hasIbgpMode()
    assert as2.getOspfMode() == "router-transit-only"
    assert as2.hasOspfMode()

    with pytest.raises(AssertionError, match="unsupported iBGP mode"):
        as2.setIbgpMode("rr")
    with pytest.raises(AssertionError, match="unsupported OSPF mode"):
        as2.setOspfMode("host-facing")


def test_frr_bgp_layer_shim_is_not_exported():
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("seedemu.layers.FrrBgp")
    assert not hasattr(importlib.import_module("seedemu.layers"), "FrrBgp")


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

    route_server = emu.getRegistry().get("ix", "rs", "ix100")
    router = emu.getRegistry().get("150", "rnode", "router0")

    rs_conf = _file_content(route_server, "/etc/bird/bird.conf")
    router_conf = _file_content(router, "/etc/bird/bird.conf")

    assert "protocol bgp p_as150" in rs_conf
    assert "rs client" in rs_conf
    assert "neighbor 10.100.0.150 as 150" in rs_conf
    assert "protocol bgp p_rs100" in router_conf
    assert "neighbor 10.100.0.100 as 100" in router_conf
    assert "bgp_large_community.add(PEER_COMM)" in router_conf


def test_frr_route_server_backend_renders_route_server_client_config():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    ix = base.createInternetExchange(100)
    ix.getRouteServerNode().setRoutingBackend("frr")
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork("net0")
    as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    ebgp.addRsPeer(100, 150)
    ebgp.addRsPeer(100, 151)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.render()

    route_server = emu.getRegistry().get("ix", "rs", "ix100")
    as150_router = emu.getRegistry().get("150", "rnode", "router0")
    frr_conf = _file_content(route_server, "/etc/frr/frr.conf")

    assert _file_content(route_server, "/etc/bird/bird.conf") == ""
    assert "router bgp 100" in frr_conf
    assert " bgp router-id 10.100.0.100" in frr_conf
    assert "neighbor 10.100.0.150 remote-as 150" in frr_conf
    assert "neighbor 10.100.0.151 remote-as 151" in frr_conf
    assert "neighbor 10.100.0.150 route-server-client" in frr_conf
    assert "neighbor 10.100.0.151 route-server-client" in frr_conf
    assert "redistribute connected" not in frr_conf
    assert "protocol bgp p_rs100" in _file_content(as150_router, "/etc/bird/bird.conf")


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

    r1 = emu.getRegistry().get("2", "rnode", "r1")
    r2 = emu.getRegistry().get("2", "rnode", "r2")

    assert any(cmd == "bird -d" for cmd, _ in r1.getStartCommands())
    assert not any(cmd == "bird -d" for cmd, _ in r2.getStartCommands())
    assert _file_content(r2, "/etc/bird/bird.conf") == ""

    r1_bird_conf = _file_content(r1, "/etc/bird/bird.conf")
    assert r1_bird_conf.index("ipv4 table t_ospf") < r1_bird_conf.index("protocol bgp ibgp1")

    frr_conf = _file_content(r2, "/etc/frr/frr.conf")
    assert "router bgp 2" in frr_conf
    assert "neighbor 10.101.0.152 remote-as 152" in frr_conf
    assert "RM_CONNECTED_TO_BGP" in frr_conf
    assert "LC_LOCAL_OR_CUSTOMER" in frr_conf
    assert "router ospf" in frr_conf
    assert "interface net0" in frr_conf


def _build_three_router_ibgp_emulator(ibgp: Ibgp, configure_as=None):
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("west")
    as2.createNetwork("east")
    as2.createRouter("edge_west").joinNetwork("west")
    as2.createRouter("core").joinNetwork("west").joinNetwork("east")
    as2.createRouter("edge_east", routingBackend="frr").joinNetwork("east")
    if configure_as is not None:
        configure_as(as2)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    return (
        emu.getRegistry().get("2", "rnode", "edge_west"),
        emu.getRegistry().get("2", "rnode", "core"),
        emu.getRegistry().get("2", "rnode", "edge_east"),
    )


def test_default_ibgp_mode_preserves_legacy_full_mesh():
    edge_west, core, edge_east = _build_three_router_ibgp_emulator(Ibgp())

    assert len([session for session in get_bgp_sessions(edge_west) if session["kind"] == "ibgp"]) == 2
    assert len([session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"]) == 2
    assert len([session for session in get_bgp_sessions(edge_east) if session["kind"] == "ibgp"]) == 2


def test_edge_only_full_mesh_ibgp_scope_excludes_core_router():
    def configure_edge_only(as2):
        as2.setIbgpMode("full-mesh")
        as2.setBgpScope("edge-only")
        as2.getRouter("edge_west").setBgpRole("edge")
        as2.getRouter("edge_east").setBgpRole("edge")
        as2.getRouter("core").setBgpRole("core")

    edge_west, core, edge_east = _build_three_router_ibgp_emulator(
        Ibgp(),
        configure_as=configure_edge_only,
    )

    west_sessions = [session for session in get_bgp_sessions(edge_west) if session["kind"] == "ibgp"]
    east_sessions = [session for session in get_bgp_sessions(edge_east) if session["kind"] == "ibgp"]
    assert len(west_sessions) == 1
    assert len(east_sessions) == 1
    assert west_sessions[0]["peer_address"] == str(edge_east.getLoopbackAddress())
    assert east_sessions[0]["peer_address"] == str(edge_west.getLoopbackAddress())
    assert [session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"] == []


def test_router_bgp_roles_drive_edge_only_full_mesh_scope():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.setIbgpMode("full-mesh")
    as2.setBgpScope("edge-only")
    as2.createNetwork("west")
    as2.createNetwork("east")
    edge_west = as2.createRouter("edge_west").joinNetwork("west")
    core = as2.createRouter("core").joinNetwork("west").joinNetwork("east")
    edge_east = as2.createRouter("edge_east").joinNetwork("east")
    edge_west.setBgpRole("edge")
    core.setBgpRole("core")
    edge_east.setBgpRole("edge")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    edge_west = emu.getRegistry().get("2", "rnode", "edge_west")
    core = emu.getRegistry().get("2", "rnode", "core")
    edge_east = emu.getRegistry().get("2", "rnode", "edge_east")

    west_sessions = [session for session in get_bgp_sessions(edge_west) if session["kind"] == "ibgp"]
    east_sessions = [session for session in get_bgp_sessions(edge_east) if session["kind"] == "ibgp"]
    assert edge_west.getBgpRole() == "edge"
    assert edge_west.getLabel()["seedemu_bgp_role"] == "edge"
    assert core.getBgpRole() == "core"
    assert len(west_sessions) == 1
    assert len(east_sessions) == 1
    assert west_sessions[0]["peer_address"] == str(edge_east.getLoopbackAddress())
    assert east_sessions[0]["peer_address"] == str(edge_west.getLoopbackAddress())
    assert [session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"] == []


def test_router_bgp_roles_do_not_change_legacy_ibgp_default():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("west")
    as2.createNetwork("east")
    as2.createRouter("edge_west").joinNetwork("west").setBgpRole("edge")
    as2.createRouter("core").joinNetwork("west").joinNetwork("east").setBgpRole("core")
    as2.createRouter("edge_east").joinNetwork("east").setBgpRole("edge")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    core = emu.getRegistry().get("2", "rnode", "core")
    assert len([session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"]) == 2


def test_router_bgp_role_and_disable_validation():
    router = Base().createAutonomousSystem(2).createRouter("r1")

    with pytest.raises(AssertionError, match="unsupported BGP role"):
        router.setBgpRole("rr")
    with pytest.raises(AssertionError, match="unsupported router control-plane disable flag"):
        router.disableControlPlane("ospf")

    router.disableControlPlane("ibgp")
    assert router.isControlPlaneDisabled("ibgp")
    assert router.getDisabledControlPlanes() == {"ibgp"}
    assert router.getLabel()["seedemu_control_plane_disabled_ibgp"] == "true"


def test_router_ibgp_disable_removes_local_and_remote_sessions():
    edge_west, core, edge_east = _build_three_router_ibgp_emulator(
        Ibgp(),
        configure_as=lambda as2: as2.getRouter("core").disableControlPlane("ibgp"),
    )

    west_sessions = [session for session in get_bgp_sessions(edge_west) if session["kind"] == "ibgp"]
    east_sessions = [session for session in get_bgp_sessions(edge_east) if session["kind"] == "ibgp"]
    assert len(west_sessions) == 1
    assert len(east_sessions) == 1
    assert west_sessions[0]["peer_address"] == str(edge_east.getLoopbackAddress())
    assert east_sessions[0]["peer_address"] == str(edge_west.getLoopbackAddress())
    assert [session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"] == []

def test_disabled_ibgp_mode_matches_as_masking_semantics():
    ibgp = Ibgp()
    edge_west, core, edge_east = _build_three_router_ibgp_emulator(
        ibgp,
        configure_as=lambda as2: as2.setIbgpMode("disabled"),
    )

    assert get_bgp_sessions(edge_west) == []
    assert get_bgp_sessions(core) == []
    assert get_bgp_sessions(edge_east) == []

def test_route_reflector_mode_completes_default_cluster_membership():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.setIbgpMode("route-reflector")
    as2.createNetwork("net0")
    as2.createBgpCluster("10.2.0.1")
    as2.createRouter("rr").joinNetwork("net0").joinBgpCluster("10.2.0.1").makeRouteReflector()
    as2.createRouter("client").joinNetwork("net0").joinBgpCluster("10.2.0.1")
    as2.createRouter("core").joinNetwork("net0")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    rr = emu.getRegistry().get("2", "rnode", "rr")
    client = emu.getRegistry().get("2", "rnode", "client")
    core = emu.getRegistry().get("2", "rnode", "core")

    assert len([session for session in get_bgp_sessions(rr) if session["route_reflector_client"]]) == 2
    assert len([session for session in get_bgp_sessions(client) if session["kind"] == "ibgp"]) == 1
    assert len([session for session in get_bgp_sessions(core) if session["kind"] == "ibgp"]) == 1
    assert core.getBgpClusterId() == "10.2.0.1"


def test_edge_router_can_also_be_route_reflector():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.setIbgpMode("route-reflector")
    as2.createNetwork("net0")
    as2.createBgpCluster("10.2.0.1")
    rr = as2.createRouter("edge_rr").joinNetwork("net0").joinBgpCluster("10.2.0.1")
    rr.setBgpRole("edge").makeRouteReflector()
    as2.createRouter("client").joinNetwork("net0").joinBgpCluster("10.2.0.1")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    edge_rr = emu.getRegistry().get("2", "rnode", "edge_rr")
    assert edge_rr.getBgpRole() == "edge"
    assert edge_rr.isRouteReflector()
    assert len([session for session in get_bgp_sessions(edge_rr) if session["route_reflector_client"]]) == 1


def test_ospf_legacy_mode_keeps_local_networks_active_by_default():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("transit")
    as2.createNetwork("hostnet")
    as2.createRouter("r1").joinNetwork("transit").joinNetwork("hostnet")
    as2.createRouter("r2").joinNetwork("transit")
    as2.createHost("host").joinNetwork("hostnet")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.render()

    r1 = emu.getRegistry().get("2", "rnode", "r1")
    intents = get_ospf_interface_intents(r1)
    assert "transit" in intents["active"]
    assert "hostnet" in intents["active"]


def test_ospf_router_transit_only_mode_keeps_host_network_passive():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()

    as2 = base.createAutonomousSystem(2)
    as2.setOspfMode("router-transit-only")
    as2.createNetwork("transit")
    as2.createNetwork("hostnet")
    as2.createNetwork("hostnet2")
    as2.createRouter("r1").joinNetwork("transit").joinNetwork("hostnet")
    as2.createRouter("r2", routingBackend="frr").joinNetwork("transit").joinNetwork("hostnet2")
    as2.createHost("host").joinNetwork("hostnet")
    as2.createHost("host2").joinNetwork("hostnet2")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.render()

    r1 = emu.getRegistry().get("2", "rnode", "r1")
    intents = get_ospf_interface_intents(r1)
    assert "transit" in intents["active"]
    assert "hostnet" in intents["passive"]
    assert "hostnet" not in intents["active"]

    bird_conf = _file_content(r1, "/etc/bird/bird.conf")
    frr_conf = _file_content(emu.getRegistry().get("2", "rnode", "r2"), "/etc/frr/frr.conf")
    assert 'interface "transit" { hello 1; dead count 2; }' in bird_conf
    assert 'interface "hostnet" { stub; }' in bird_conf
    assert "interface transit\n ip ospf area 0" in frr_conf
    assert "interface hostnet2\n ip ospf area 0\n ip ospf passive" in frr_conf


def test_ospf_router_transit_only_respects_explicit_stub_and_mask():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ospf.markAsStub(2, "stubbed")
    ospf.maskNetwork(2, "masked")

    as2 = base.createAutonomousSystem(2)
    as2.setOspfMode("router-transit-only")
    as2.createNetwork("transit")
    as2.createNetwork("stubbed")
    as2.createNetwork("masked")
    as2.createRouter("r1").joinNetwork("transit").joinNetwork("stubbed").joinNetwork("masked")
    as2.createRouter("r2").joinNetwork("transit").joinNetwork("stubbed").joinNetwork("masked")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.render()

    r1 = emu.getRegistry().get("2", "rnode", "r1")
    intents = get_ospf_interface_intents(r1)
    assert "transit" in intents["active"]
    assert "stubbed" in intents["passive"]
    assert "stubbed" not in intents["active"]
    assert "masked" not in intents["active"]
    assert "masked" not in intents["passive"]


def test_duplicate_bgp_session_names_are_preserved_with_unique_render_names():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.createRouter("router0").joinNetwork("ix100").joinNetwork("ix101")

    as151 = base.createAutonomousSystem(151)
    as151.createRouter("router0").joinNetwork("ix100").joinNetwork("ix101")

    ebgp.addPrivatePeering(100, 2, 151, abRelationship=PeerRelationship.Peer)
    ebgp.addPrivatePeering(101, 2, 151, abRelationship=PeerRelationship.Peer)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.render()

    router = emu.getRegistry().get("2", "rnode", "router0")
    sessions = get_bgp_sessions(router)
    assert len([session for session in sessions if session["name"] == "p_as151"]) == 2
    assert len({session["render_name"] for session in sessions}) == len(sessions)

    bird_conf = _file_content(router, "/etc/bird/bird.conf")
    assert bird_conf.count("neighbor 10.100.0.151 as 151") == 1
    assert bird_conf.count("neighbor 10.101.0.151 as 151") == 1
    assert bird_conf.count("protocol bgp p_as151") == 2


def test_private_peering_can_select_explicit_ix_routers():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createRouter("edge_west").joinNetwork("ix100", address="10.100.0.20")
    as2.createRouter("edge_east").joinNetwork("ix100", address="10.100.0.21")

    as151 = base.createAutonomousSystem(151)
    as151.createRouter("router0").joinNetwork("ix100", address="10.100.0.151")

    ebgp.addPrivatePeeringByRouters(
        100,
        2,
        "edge_east",
        151,
        "router0",
        abRelationship=PeerRelationship.Provider,
    )

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.render()

    edge_west = emu.getRegistry().get("2", "rnode", "edge_west")
    edge_east = emu.getRegistry().get("2", "rnode", "edge_east")
    customer = emu.getRegistry().get("151", "rnode", "router0")

    assert [session for session in get_bgp_sessions(edge_west) if session["kind"] == "ebgp"] == []
    east_sessions = [session for session in get_bgp_sessions(edge_east) if session["kind"] == "ebgp"]
    assert len(east_sessions) == 1
    assert east_sessions[0]["local_address"] == "10.100.0.21"
    assert east_sessions[0]["peer_address"] == "10.100.0.151"
    assert east_sessions[0]["peer_asn"] == 151

    customer_conf = _file_content(customer, "/etc/bird/bird.conf")
    assert "neighbor 10.100.0.21 as 2" in customer_conf
    assert "neighbor 10.100.0.20 as 2" not in customer_conf


def test_route_server_peer_can_select_explicit_ix_router():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createRouter("edge_west").joinNetwork("ix100", address="10.100.0.20")
    as2.createRouter("edge_east").joinNetwork("ix100", address="10.100.0.21")

    ebgp.addRsPeerByRouter(100, 2, "edge_east")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.render()

    route_server = emu.getRegistry().get("ix", "rs", "ix100")
    edge_west = emu.getRegistry().get("2", "rnode", "edge_west")
    edge_east = emu.getRegistry().get("2", "rnode", "edge_east")

    assert [session for session in get_bgp_sessions(edge_west) if session["kind"] == "ebgp"] == []
    east_sessions = [session for session in get_bgp_sessions(edge_east) if session["kind"] == "ebgp"]
    assert len(east_sessions) == 1
    assert east_sessions[0]["local_address"] == "10.100.0.21"
    assert east_sessions[0]["peer_asn"] == 100

    rs_conf = _file_content(route_server, "/etc/bird/bird.conf")
    assert "neighbor 10.100.0.21 as 2" in rs_conf
    assert "neighbor 10.100.0.20 as 2" not in rs_conf


def test_explicit_ix_router_selection_rejects_non_attached_router():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("edge").joinNetwork("ix100", address="10.100.0.20")
    as2.createRouter("core").joinNetwork("net0")

    as151 = base.createAutonomousSystem(151)
    as151.createRouter("router0").joinNetwork("ix100", address="10.100.0.151")

    ebgp.addPrivatePeeringByRouters(100, 2, "core", 151, "router0")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)

    with pytest.raises(AssertionError, match="explicit peering router as2/core is not connected to ix100"):
        emu.render()


def test_route_reflector_intent_renders_without_direct_ibgp_bird_writes():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createBgpCluster("10.2.0.1")
    as2.createRouter("rr").joinNetwork("net0").joinBgpCluster("10.2.0.1").makeRouteReflector()
    as2.createRouter("client").joinNetwork("net0").joinBgpCluster("10.2.0.1")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    rr = emu.getRegistry().get("2", "rnode", "rr")
    client = emu.getRegistry().get("2", "rnode", "client")

    rr_conf = _file_content(rr, "/etc/bird/bird.conf")
    client_conf = _file_content(client, "/etc/bird/bird.conf")

    assert "protocol bgp Ibgp_rr_client_client" in rr_conf
    assert "passive yes" in rr_conf
    assert "rr client" in rr_conf
    assert "rr cluster id 10.2.0.1" in rr_conf
    assert "protocol bgp Ibgp_rr_rr" in client_conf
    assert "next hop self" in client_conf
    assert rr_conf.index("ipv4 table t_ospf") < rr_conf.index("protocol bgp Ibgp_rr_client_client")


def test_frr_route_reflector_renders_cluster_id_and_client():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ospf = Ospf()
    ibgp = Ibgp()

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createBgpCluster("10.2.0.1")
    as2.createRouter("rr", routingBackend="frr").joinNetwork("net0").joinBgpCluster("10.2.0.1").makeRouteReflector()
    as2.createRouter("client").joinNetwork("net0").joinBgpCluster("10.2.0.1")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ospf)
    emu.addLayer(ibgp)
    emu.render()

    rr = emu.getRegistry().get("2", "rnode", "rr")
    frr_conf = _file_content(rr, "/etc/frr/frr.conf")

    assert "router bgp 2" in frr_conf
    assert " bgp cluster-id 10.2.0.1" in frr_conf
    assert "neighbor 10.0.0.2 route-reflector-client" in frr_conf
    assert "neighbor 10.0.0.2 passive" in frr_conf


def test_as_level_mpls_core_forwarding_rejects_bird_backend():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()
    mpls = Mpls()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createNetwork("net2")
    as2.createRouter("r1").joinNetwork("net0").joinNetwork("ix100")
    as2.createRouter("r2").joinNetwork("net0").joinNetwork("net1")
    as2.createRouter("r3").joinNetwork("net1").joinNetwork("net2")
    as2.createRouter("r4").joinNetwork("net2").joinNetwork("ix101")
    as2.setCoreForwarding("mpls")

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
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(mpls)
    with pytest.raises(AssertionError, match="MPLS requires FRR routing backend"):
        emu.render()


def test_mpls_preserves_frr_edge_bgp_config_while_core_stays_bgp_free():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    ibgp = Ibgp()
    ospf = Ospf()
    mpls = Mpls()

    base.createInternetExchange(112)
    base.createInternetExchange(113)

    as8 = base.createAutonomousSystem(8)
    as8.createNetwork("net_edge0_core0")
    as8.createNetwork("net_core0_core1")
    as8.createNetwork("net_core1_edge1")
    as8.createRouter("edge0", routingBackend="frr").joinNetwork("ix112").joinNetwork("net_edge0_core0").setBgpRole("edge")
    as8.createRouter("core0", routingBackend="frr").joinNetwork("net_edge0_core0").joinNetwork("net_core0_core1").setBgpRole("core")
    as8.createRouter("core1", routingBackend="frr").joinNetwork("net_core0_core1").joinNetwork("net_core1_edge1").setBgpRole("core")
    as8.createRouter("edge1", routingBackend="frr").joinNetwork("ix113").joinNetwork("net_core1_edge1").setBgpRole("edge")
    as8.setIbgpMode("full-mesh")
    as8.setBgpScope("edge-only")
    as8.setCoreForwarding("mpls")

    as162 = base.createAutonomousSystem(162)
    as162.createNetwork("net0")
    as162.createRouter("router0").joinNetwork("net0").joinNetwork("ix112")

    as163 = base.createAutonomousSystem(163)
    as163.createNetwork("net0")
    as163.createRouter("router0").joinNetwork("net0").joinNetwork("ix113")

    ebgp.addPrivatePeering(112, 8, 162, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(113, 8, 163, abRelationship=PeerRelationship.Provider)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(mpls)
    emu.render()

    edge0 = emu.getRegistry().get("8", "rnode", "edge0")
    core0 = emu.getRegistry().get("8", "rnode", "core0")
    edge0_conf = _file_content(edge0, "/etc/frr/frr.conf")
    core0_conf = _file_content(core0, "/etc/frr/frr.conf")
    edge0_start = _file_content(edge0, "/frr_start")
    core0_start = _file_content(core0, "/frr_start")

    assert "router bgp 8" in edge0_conf
    assert "neighbor 10.112.0.162 remote-as 162" in edge0_conf
    assert "neighbor 10.0.0.4 remote-as 8" in edge0_conf
    assert "mpls ldp" in edge0_conf
    assert "router ospf" in edge0_conf
    assert "router bgp" not in core0_conf
    assert "mpls ldp" in core0_conf
    assert "router ospf" in core0_conf
    assert "bgpd=no" in edge0_start
    assert "bgpd=no" not in core0_start
    assert "ldpd=no" in edge0_start
    assert "ldpd=no" in core0_start
    assert "while read -r iface" in edge0_start


def test_mpls_preserves_explicit_route_reflector_ibgp_mode():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ibgp = Ibgp()
    ospf = Ospf()
    mpls = Mpls()

    base.createInternetExchange(100)
    base.createInternetExchange(101)

    as2 = base.createAutonomousSystem(2)
    as2.setIbgpMode("route-reflector")
    as2.setBgpScope("edge-only")
    as2.createNetwork("net0")
    as2.createNetwork("net1")
    as2.createBgpCluster("10.2.0.1")
    as2.createRouter("r1", routingBackend="frr").joinNetwork("ix100").joinNetwork("net0").joinBgpCluster("10.2.0.1").setBgpRole("edge").makeRouteReflector()
    as2.createRouter("r2", routingBackend="frr").joinNetwork("net0").joinNetwork("net1").setBgpRole("core")
    as2.createRouter("r4", routingBackend="frr").joinNetwork("net1").joinNetwork("ix101").joinBgpCluster("10.2.0.1").setBgpRole("edge")
    as2.setCoreForwarding("mpls")

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    emu.addLayer(mpls)
    emu.render()

    r1 = emu.getRegistry().get("2", "rnode", "r1")
    r2 = emu.getRegistry().get("2", "rnode", "r2")
    r4 = emu.getRegistry().get("2", "rnode", "r4")

    r1_ibgp = [session for session in get_bgp_sessions(r1) if session["kind"] == "ibgp"]
    r4_ibgp = [session for session in get_bgp_sessions(r4) if session["kind"] == "ibgp"]
    assert len(r1_ibgp) == 1
    assert r1_ibgp[0]["route_reflector_client"]
    assert r1_ibgp[0]["igp_table"] == "master4"
    assert len(r4_ibgp) == 1
    assert r4_ibgp[0]["name"] == "Ibgp_rr_r1"
    assert get_bgp_sessions(r2) == []

    r1_conf = _file_content(r1, "/etc/frr/frr.conf")
    r2_conf = _file_content(r2, "/etc/frr/frr.conf")
    r2_frr = _file_content(r2, "/etc/frr/frr.conf")
    assert "router bgp 2" in r1_conf
    assert " route-reflector-client" in r1_conf
    assert "mpls_ibgp" not in r1_conf
    assert "router bgp" not in r2_conf
    assert "mpls ldp" in r2_frr


def test_exabgp_service_renders_speaker_and_router_peer():
    emu = Emulator()
    base = Base()
    routing = Routing()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")

    as180 = base.createAutonomousSystem(180)
    as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")

    exabgp.install("as180_exabgp") \
        .setLocalAsn(180) \
        .addPeer("router0", router_asn=2, router_relationship="customer") \
        .addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(exabgp)
    emu.render()

    speaker = emu.getRegistry().get("180", "hnode", "exabgp")
    router = emu.getRegistry().get("2", "rnode", "router0")

    exabgp_conf = _file_content(speaker, "/etc/exabgp/exabgp.conf")
    assert "neighbor 10.100.0.2" in exabgp_conf
    assert "local-as 180" in exabgp_conf
    assert "peer-as 2" in exabgp_conf
    assert "198.51.100.0/24" in exabgp_conf

    bird_conf = _file_content(router, "/etc/bird/bird.conf")
    assert "protocol bgp exabgp_180" in bird_conf
    assert "neighbor 10.100.0.180 as 180" in bird_conf
    assert "bgp_large_community.add(CUSTOMER_COMM)" in bird_conf
    assert "bgp_local_pref = 30" in bird_conf


def test_exabgp_service_renders_frr_router_peer_without_bird():
    emu = Emulator()
    base = Base()
    routing = Routing()
    exabgp = ExaBgpService()

    base.createInternetExchange(100)

    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    as2.createRouter("router0", routingBackend="frr").joinNetwork("net0").joinNetwork("ix100")

    as180 = base.createAutonomousSystem(180)
    as180.createHost("exabgp").joinNetwork("ix100", address="10.100.0.180")

    exabgp.install("as180_exabgp") \
        .setLocalAsn(180) \
        .addPeer("router0", router_asn=2, router_relationship="customer") \
        .addAnnouncement("198.51.100.0/24")
    emu.addBinding(Binding("as180_exabgp", filter=Filter(asn=180, nodeName="exabgp")))

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(exabgp)
    emu.render()

    speaker = emu.getRegistry().get("180", "hnode", "exabgp")
    router = emu.getRegistry().get("2", "rnode", "router0")

    assert _file_content(router, "/etc/bird/bird.conf") == ""
    frr_conf = _file_content(router, "/etc/frr/frr.conf")
    assert "router bgp 2" in frr_conf
    assert "neighbor 10.100.0.180 remote-as 180" in frr_conf
    assert "neighbor 10.100.0.180 description exabgp_180" in frr_conf
    assert "neighbor 10.100.0.180 next-hop-self" in frr_conf

    exabgp_conf = _file_content(speaker, "/etc/exabgp/exabgp.conf")
    assert "peer-as 2" in exabgp_conf
    assert "198.51.100.0/24" in exabgp_conf

"""RIP protocol policy, backend composition and OSPF replacement regressions."""

import importlib
from pathlib import Path

import pytest

from seedemu.core import Emulator, Hook
from seedemu.layers import Base, Ibgp, Ospf, Rip, Routing
from seedemu.layers._bgp_metadata import get_bgp_sessions
from seedemu.layers._igp_metadata import (
    OSPF_INTERFACE_INTENTS_ATTR,
    RIP_DEFAULTS,
    RIP_INTERFACE_INTENTS_ATTR,
    get_igp_protocol,
    get_ospf_interface_intents,
    get_ospf_timers,
    get_rip_interface_intents,
    get_rip_timers,
    normalize_ospf_timers,
    normalize_rip_timers,
    set_ospf_interface_intents,
    set_rip_interface_intents,
)
from seedemu.mergers import DEFAULT_MERGERS, DefaultRipMerger


REPO_ROOT = Path(__file__).resolve().parents[1]


def readFile(node, path):
    """Read node's generated file at path, or return an empty string."""
    return next((content for file in node.getFiles() for name, content in [file.get()] if name == path), "")


def createChain(rip=None, backend="mixed", ibgp=True, igp="rip"):
    """Create a policy topology; igp=None retains the AS's default OSPF choice."""
    emulator, base = Emulator(), Base()
    base.createInternetExchange(100)
    as2 = base.createAutonomousSystem(2)
    if igp is not None:
        as2.setIgpMode(igp)
    for name in ("net12", "net23", "lan1", "lan3", "mgmt"):
        as2.createNetwork(name)
    routers = {
        "r1": as2.createRouter("r1").joinNetwork("net12").joinNetwork("lan1").joinNetwork("mgmt").joinNetwork("ix100"),
        "r2": as2.createRouter("r2").joinNetwork("net12").joinNetwork("net23"),
        "r3": as2.createRouter("r3").joinNetwork("net23").joinNetwork("lan3"),
    }
    as2.createHost("h1").joinNetwork("lan1")
    as2.createHost("h3").joinNetwork("lan3")
    for index, router in enumerate(routers.values()):
        router.setRoutingBackend("frr" if backend == "frr" or backend == "mixed" and index == 1 else "bird")
    emulator.addLayer(base)
    emulator.addLayer(Routing())
    if ibgp:
        emulator.addLayer(Ibgp())
    emulator.addLayer(rip if rip is not None else Rip())
    return emulator, base, routers


def readOptions(router):
    """Index resolved interface options from router's RIP intent."""
    return {item["name"]: item["options"] for item in get_rip_interface_intents(router)["interfaces"]}


def test_rip_export_and_default_timers():
    assert not hasattr(importlib.import_module("seedemu.layers"), "RIP")
    assert not hasattr(importlib.import_module("seedemu.layers.Rip"), "RIP")
    assert Rip().getName() == "Rip"
    assert Rip().getTimers() == {"update": 30, "timeout": 180, "garbage": 120}
    rip = Rip().setTimers(update=2, timeout=12, garbage=8)
    assert rip.getTimers() == {"update": 2, "timeout": 12, "garbage": 8}
    assert rip.setTimers(garbage=6) is rip
    assert rip.getTimers()["update"] == 2


def test_igp_metadata_copies_inputs_and_keeps_protocol_intents_independent():
    router = Base().createAutonomousSystem(2).createRouter("r1")
    Emulator().getRegistry().register("2", "rnode", "r1", router)
    active = ["net12"]
    set_ospf_interface_intents(router, active, ["dummy0"], tick=2, hello=3, dead=12)
    defaults = {"update": 6, "timeout": 36, "garbage": 24}
    interfaces = [{"name": "net12", "prefix": "10.2.0.0/24", "exchange": True,
                   "options": {**RIP_DEFAULTS, **defaults, "passive": False}}]
    set_rip_interface_intents(router, interfaces, defaults=defaults)

    active.append("lan1")
    defaults["update"] = 9
    interfaces[0]["options"]["metric"] = 4
    interfaces.append({"name": "lan1"})
    ospf = get_ospf_interface_intents(router)
    rip = get_rip_interface_intents(router)
    assert ospf == {"active": ["net12"], "passive": ["dummy0"]}
    assert len(rip["interfaces"]) == 1 and rip["interfaces"][0]["options"]["metric"] == 1
    assert get_ospf_timers(router) == {"tick": 2, "hello": 3, "dead": 12}
    assert get_rip_timers(router) == {"update": 6, "timeout": 36, "garbage": 24}

    ospf["active"].clear()
    rip["defaults"]["update"] = 10
    rip["interfaces"][0]["options"]["metric"] = 5
    assert get_ospf_interface_intents(router)["active"] == ["net12"]
    assert get_rip_timers(router)["update"] == 6
    assert get_rip_interface_intents(router)["interfaces"][0]["options"]["metric"] == 1
    assert not get_igp_protocol(router)  # Metadata storage alone does not enable a protocol.


def test_igp_metadata_reads_legacy_keys_and_missing_timer_defaults():
    router = Base().createAutonomousSystem(2).createRouter("r1")
    Emulator().getRegistry().register("2", "rnode", "r1", router)
    assert get_ospf_interface_intents(router) == {"active": [], "passive": []}
    assert get_rip_interface_intents(router) == {}
    assert get_ospf_timers(router) == normalize_ospf_timers() == {"tick": 1, "hello": 1, "dead": 4}
    assert get_rip_timers(router) == normalize_rip_timers() == {"update": 30, "timeout": 180, "garbage": 120}

    assert OSPF_INTERFACE_INTENTS_ATTR == "__ospf_interface_intents"
    assert RIP_INTERFACE_INTENTS_ATTR == "__rip_intent"
    router.setAttribute("__ospf_interface_intents", {"active": ["net12"], "passive": []})
    router.setAttribute("__rip_intent", {"defaults": {"garbage": 90}, "interfaces": []})
    assert get_ospf_timers(router) == {"tick": 1, "hello": 1, "dead": 4}
    assert get_rip_timers(router) == {"update": 30, "timeout": 180, "garbage": 90}
    assert get_rip_interface_intents(router)["defaults"] == {"garbage": 90}


def test_policy_precedence_and_directional_metrics():
    rip = Rip().setDefaults(metric=1).setTimers(update=5, timeout=30, garbage=20)
    rip.setNetworkOptions(2, "net12", metric=2, poison_reverse=False)
    rip.setRouterOptions(2, "r2", metric=3)
    rip.setInterfaceOptions(2, "r2", "net12", metric=4)
    emulator, _, routers = createChain(rip)
    emulator.render()
    assert readOptions(routers["r1"])["net12"]["metric"] == 2
    assert readOptions(routers["r2"])["net12"]["metric"] == 4
    assert readOptions(routers["r2"])["net23"]["metric"] == 3
    assert not readOptions(routers["r2"])["net12"]["poison_reverse"]
    assert "offset-list SEED_RIP_METRIC in 4 net12" in readFile(routers["r2"], "/etc/frr/frr.conf")
    assert "ip rip split-horizon" in readFile(routers["r2"], "/etc/frr/frr.conf")


@pytest.mark.parametrize("backend", ["bird", "frr", "mixed"])
def test_rip_ibgp_composition_and_loopback_advertisement(backend):
    emulator, _, routers = createChain(backend=backend)
    emulator.render()
    for router in routers.values():
        assert all(session["igp_table"] == "t_rip" for session in get_bgp_sessions(router))
        assert len(get_bgp_sessions(router)) == 2
        intent = get_rip_interface_intents(router)
        assert any(item["prefix"] == "{}/32".format(router.getLoopbackAddress()) for item in intent["interfaces"])
        bird, frr = readFile(router, "/etc/bird/bird.conf"), readFile(router, "/etc/frr/frr.conf")
        if router.getRoutingBackend() == "bird":
            assert bird.index("ipv4 table t_rip") < bird.index("protocol bgp")
            assert "protocol rip rip1" in bird and "igp table t_rip" in bird
            assert 'interface "dummy0";' in bird
            assert "export where source = RTS_DEVICE || source = RTS_RIP" in bird
            assert "peer table master4;\n    import none;" in bird
        else:
            assert "router rip" in frr and "router bgp 2" in frr
            assert "timers basic 30 180 120" in frr
            assert "no passive-interface default" in frr
            assert "no passive-interface net12" not in frr
            assert "redistribute connected metric 1 route-map RM_CONNECTED_TO_RIP" in frr
            assert "ripd=no/ripd=yes" in readFile(router, "/frr_start")
            assert "ospfd=no/ospfd=yes" not in readFile(router, "/frr_start")
        assert "protocol ospf" not in bird and "router ospf" not in frr


def test_host_passivity_and_external_as_isolation():
    rip = Rip().setNetworkOptions(2, "ix100", passive=False)
    emulator, _, routers = createChain(rip, backend="bird")
    emulator.render()
    options = readOptions(routers["r1"])
    assert not options["net12"]["passive"]
    assert options["lan1"]["passive"] and options["ix100"]["passive"]
    interfaces = {item["name"]: item for item in get_rip_interface_intents(routers["r1"])["interfaces"]}
    assert not interfaces["ix100"]["exchange"]
    bird = readFile(routers["r1"], "/etc/bird/bird.conf").split("protocol rip rip1", 1)[1]
    assert 'interface "ix100"' not in bird and 'interface "dummy0"' not in bird


def test_frr_uses_explicit_passive_entries_without_nonpassive_exceptions():
    emulator, _, routers = createChain(backend="frr")
    emulator.render()
    configuration = readFile(routers["r1"], "/etc/frr/frr.conf")
    assert "no passive-interface default" in configuration
    assert "passive-interface lan1" in configuration
    assert "network ix100" not in configuration
    assert "no passive-interface net12" not in configuration


def test_masks_and_disabled_router_preserve_other_protocols():
    rip = Rip().maskNetwork(2, "mgmt").markAsStub(2, "lan1")
    rip.setRouterOptions(2, "r3", advertise_loopback=False)
    rip.setInterfaceOptions(2, "r2", "net23", enabled=False)
    emulator, _, routers = createChain(rip)
    emulator.render()
    assert "mgmt" not in readOptions(routers["r1"])
    assert "net23" not in readOptions(routers["r2"])
    assert "dummy0" not in readOptions(routers["r3"])
    assert 'interface "mgmt"' not in readFile(routers["r1"], "/etc/bird/bird.conf").split("protocol direct rip_connected", 1)[1]
    assert get_bgp_sessions(routers["r3"])


@pytest.mark.parametrize("disable", ["asn", "router"])
def test_rip_can_be_disabled(disable):
    rip = Rip()
    if disable == "asn":
        rip.maskAsn(2)
    else:
        for name in ("r1", "r2", "r3"):
            rip.setRouterOptions(2, name, enabled=False)
    emulator, _, routers = createChain(rip, ibgp=False)
    emulator.render()
    assert all(not get_rip_interface_intents(router) for router in routers.values())


def test_disabled_rip_router_does_not_reference_a_missing_bird_table():
    rip = Rip().setRouterOptions(2, "r2", enabled=False)
    emulator, _, routers = createChain(rip, backend="bird")
    emulator.render()
    assert all(session["igp_table"] == "master4" for session in get_bgp_sessions(routers["r2"]))
    assert "igp table t_rip" not in readFile(routers["r2"], "/etc/bird/bird.conf")


def test_disabled_layer_defaults_can_be_overridden_on_a_network():
    rip = Rip().setDefaults(enabled=False).setNetworkOptions(2, "net12", enabled=True)
    emulator, _, routers = createChain(rip, backend="bird", ibgp=False)
    emulator.render()
    assert set(readOptions(routers["r1"])) == {"net12"}
    assert set(readOptions(routers["r2"])) == {"net12"}
    assert not get_rip_interface_intents(routers["r3"])


@pytest.mark.parametrize("backend", ["bird", "frr", "mixed"])
def test_rip_route_reflector_uses_the_selected_igp(backend):
    emulator, base, routers = createChain(backend=backend)
    as2 = base.getAutonomousSystem(2)
    as2.setIbgpMode("route-reflector")
    as2.createBgpCluster("10.2.0.1")
    routers["r2"].joinBgpCluster("10.2.0.1").makeRouteReflector()
    routers["r1"].joinBgpCluster("10.2.0.1")
    routers["r3"].joinBgpCluster("10.2.0.1")
    emulator.render()
    for router in routers.values():
        sessions = get_bgp_sessions(router)
        assert sessions and all(session["igp_table"] == "t_rip" for session in sessions)
    if routers["r2"].getRoutingBackend() == "bird":
        assert "rr client" in readFile(routers["r2"], "/etc/bird/bird.conf")
    else:
        assert "route-reflector-client" in readFile(routers["r2"], "/etc/frr/frr.conf")


@pytest.mark.parametrize("backend", ["bird", "frr", "mixed"])
@pytest.mark.parametrize("disabled", ["r1", "r2"])
def test_route_reflector_tables_follow_each_local_router(backend, disabled):
    rip = Rip().setRouterOptions(2, disabled, enabled=False)
    emulator, base, routers = createChain(rip, backend=backend)
    as2 = base.getAutonomousSystem(2)
    as2.setIbgpMode("route-reflector")
    as2.createBgpCluster("10.2.0.1")
    routers["r1"].joinBgpCluster("10.2.0.1")
    for name in ("r2", "r3"):
        routers[name].joinBgpCluster("10.2.0.1").makeRouteReflector()
    emulator.render()
    for name, router in routers.items():
        sessions = get_bgp_sessions(router)
        expected = "master4" if name == disabled else "t_rip"
        assert len(sessions) == 2 and all(session["igp_table"] == expected for session in sessions)
        if router.getRoutingBackend() == "bird":
            config = readFile(router, "/etc/bird/bird.conf")
            assert "igp table {};".format(expected) in config
            assert ("ipv4 table t_rip;" in config) == (name != disabled)


@pytest.mark.parametrize("mode", ["full-mesh", "route-reflector"])
def test_ibgp_without_igp_intents_uses_existing_master_table(mode):
    emulator, base = Emulator(), Base()
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("lan")
    routers = [as2.createRouter(name).joinNetwork("lan") for name in ("r1", "r2")]
    as2.setIbgpMode(mode)
    if mode == "route-reflector":
        as2.createBgpCluster("10.2.0.1")
        routers[0].joinBgpCluster("10.2.0.1").makeRouteReflector()
        routers[1].joinBgpCluster("10.2.0.1")
    emulator.addLayer(base)
    emulator.addLayer(Routing())
    emulator.addLayer(Ibgp())
    emulator.render()
    assert as2.getIgpMode() == "ospf"
    for router in routers:
        sessions = get_bgp_sessions(router)
        assert len(sessions) == 1 and sessions[0]["igp_table"] == "master4"
        config = readFile(router, "/etc/bird/bird.conf")
        assert "igp table master4;" in config and "ipv4 table t_ospf;" not in config


@pytest.mark.parametrize("options", [
    {"metric": 0}, {"metric": 16}, {"metric": True}, {"version": 3},
    {"update": 0}, {"timeout": -1}, {"garbage": 65536}, {"update": 1.5},
    {"passive": "yes"}, {"split_horizon": 1}, {"area": 0},
    {"update": 10, "timeout": 10},
])
def test_invalid_options_fail_at_api_boundary(options):
    with pytest.raises(ValueError, match="RIP"):
        Rip().setNetworkOptions(2, "net12", **options)


def test_resolved_timer_validation_and_no_partial_default_mutation():
    rip = Rip()
    with pytest.raises(ValueError, match="timeout must be larger"):
        rip.setTimers(timeout=1)
    assert rip.getTimers()["timeout"] == 180
    rip.setNetworkOptions(2, "net12", timeout=1)
    emulator, _, _ = createChain(rip)
    with pytest.raises(ValueError, match="timeout must be larger"):
        emulator.render()


@pytest.mark.parametrize("configure", [
    lambda rip: rip.maskAsn(999),
    lambda rip: rip.setNetworkOptions(2, "typo", metric=2),
    lambda rip: rip.setRouterOptions(2, "typo", metric=2),
    lambda rip: rip.setInterfaceOptions(2, "r1", "net23", metric=2),
])
def test_unknown_policy_targets_are_rejected(configure):
    rip = Rip()
    configure(rip)
    emulator, _, _ = createChain(rip)
    with pytest.raises(ValueError, match="RIP references unknown"):
        emulator.render()


def test_bird_interface_timers_and_frr_capability_check():
    rip = Rip().setInterfaceOptions(2, "r2", "net12", update=5)
    emulator, _, routers = createChain(rip, backend="bird")
    emulator.render()
    assert readOptions(routers["r2"])["net12"]["update"] == 5
    assert "update time 5;" in readFile(routers["r2"], "/etc/bird/bird.conf")
    emulator, _, _ = createChain(rip, backend="frr")
    with pytest.raises(ValueError, match="FRR RIP uses router-wide timers"):
        emulator.render()


def test_frr_minimum_timer_capability_is_explicit():
    rip = Rip().setTimers(update=2, timeout=12, garbage=8)
    emulator, _, _ = createChain(rip, backend="frr")
    with pytest.raises(ValueError, match="FRR RIP timers must be at least 5 seconds"):
        emulator.render()
    emulator, _, _ = createChain(rip, backend="bird")
    emulator.render()


def test_protocol_layer_does_not_write_native_rip_configuration():
    class InspectIntent(Hook):
        def getName(self):
            return "inspect-rip-intent"

        def getTargetLayer(self):
            return "Rip"

        def postconfigure(self, emulator):
            router = emulator.getRegistry().get("2", "rnode", "r1")
            assert get_rip_interface_intents(router)
            assert "protocol rip" not in readFile(router, "/etc/bird/bird.conf")
            assert "router rip" not in readFile(router, "/etc/frr/frr.conf")

    emulator, _, _ = createChain()
    emulator.addHook(InspectIntent())
    emulator.render()


def test_as_igp_selection_keeps_different_as_protocols_independent():
    emulator, base, routers = createChain()
    as3 = base.createAutonomousSystem(3)
    as3.createNetwork("net0")
    r3 = as3.createRouter("r0").joinNetwork("net0")
    emulator.addLayer(Ospf())
    emulator.render()
    assert as3.getIgpMode() == "ospf" and not as3.hasIgpMode()
    assert get_rip_interface_intents(routers["r1"]) and not get_rip_interface_intents(r3)
    assert "protocol ospf" in readFile(r3, "/etc/bird/bird.conf")


def test_as_igp_api_defaults_to_ospf_and_records_explicit_selection():
    autonomous_system = Base().createAutonomousSystem(2)
    assert autonomous_system.getIgpMode() == "ospf" and not autonomous_system.hasIgpMode()
    assert autonomous_system.setIgpMode(" RIP ") is autonomous_system
    assert autonomous_system.getIgpMode() == "rip" and autonomous_system.hasIgpMode()
    assert "IGP: rip" in autonomous_system.print(0)
    autonomous_system.setIgpMode("ospf")
    assert autonomous_system.getIgpMode() == "ospf"


def test_igp_interface_policy_defaults_follow_protocol_and_explicit_policy_is_stable():
    autonomous_system = Base().createAutonomousSystem(2)
    assert autonomous_system.getIgpInterfacePolicy() == "all-local"
    assert not autonomous_system.hasIgpInterfacePolicy()
    autonomous_system.setIgpMode("rip")
    assert autonomous_system.getIgpInterfacePolicy() == "router-links"
    assert not autonomous_system.hasIgpInterfacePolicy()
    assert autonomous_system.setIgpInterfacePolicy(" ALL-LOCAL ") is autonomous_system
    assert autonomous_system.hasIgpInterfacePolicy()
    assert autonomous_system.getIgpInterfacePolicy() == "all-local"
    autonomous_system.setIgpMode("ospf").setIgpInterfacePolicy("router-links")
    assert autonomous_system.getIgpInterfacePolicy() == "router-links"
    assert "IGP interface policy: router-links" in autonomous_system.print(0)
    assert "_AutonomousSystem__ospf_mode" not in autonomous_system.__dict__
    assert "_AutonomousSystem__ospf_mode_explicit" not in autonomous_system.__dict__


@pytest.mark.parametrize("policy", ["legacy", "router-transit-only", "ospf", "", None, True, 2])
def test_invalid_igp_interface_policy_preserves_the_previous_choice(policy):
    autonomous_system = Base().createAutonomousSystem(2).setIgpInterfacePolicy("router-links")
    with pytest.raises(AssertionError, match="unsupported IGP interface policy"):
        autonomous_system.setIgpInterfacePolicy(policy)
    assert autonomous_system.getIgpInterfacePolicy() == "router-links"


@pytest.mark.parametrize("protocol", ["ospf", "rip"])
@pytest.mark.parametrize("policy", ["all-local", "router-links"])
@pytest.mark.parametrize("backend", ["bird", "frr"])
def test_common_interface_policy_drives_both_igps_and_backends(protocol, policy, backend):
    emulator, base = Emulator(), Base()
    base.createInternetExchange(100)
    autonomous_system = base.createAutonomousSystem(2).setIgpMode(protocol).setIgpInterfacePolicy(policy)
    for name in ("transit", "hostnet", "solo", "stubbed", "masked"):
        autonomous_system.createNetwork(name)
    first = autonomous_system.createRouter("r1", routingBackend=backend)
    second = autonomous_system.createRouter("r2", routingBackend=backend)
    for name in ("transit", "hostnet", "solo", "stubbed", "masked", "ix100"):
        first.joinNetwork(name)
    for name in ("transit", "stubbed", "masked"):
        second.joinNetwork(name)
    autonomous_system.createHost("host").joinNetwork("hostnet")
    selected = (Ospf() if protocol == "ospf" else Rip()).markAsStub(2, "stubbed").maskNetwork(2, "masked")
    for layer in (base, Routing(), Ibgp(), selected):
        emulator.addLayer(layer)
    emulator.render()
    host_passive = policy == "router-links"
    if protocol == "ospf":
        intent = get_ospf_interface_intents(first)
        assert "transit" in intent["active"]
        assert {"stubbed", "ix100", "dummy0"} <= set(intent["passive"])
        assert {"hostnet", "solo"} <= set(intent["passive"] if host_passive else intent["active"])
        assert "masked" not in intent["active"] + intent["passive"]
    else:
        options = readOptions(first)
        assert not options["transit"]["passive"]
        assert options["hostnet"]["passive"] == host_passive
        assert options["solo"]["passive"] == host_passive
        assert all(options[name]["passive"] for name in ("stubbed", "ix100", "dummy0"))
        assert "masked" not in options
        assert not next(item for item in get_rip_interface_intents(first)["interfaces"] if item["name"] == "ix100")["exchange"]
    assert all(session["igp_table"] == "t_" + protocol for session in get_bgp_sessions(first))
    native = readFile(first, "/etc/bird/bird.conf" if backend == "bird" else "/etc/frr/frr.conf")
    if backend == "bird":
        if protocol == "ospf":
            assert ('interface "hostnet" { stub; }' in native) == host_passive
        else:
            host_block = native.split('interface "hostnet" {', 1)[1].split("};", 1)[0]
            assert "passive {};".format("yes" if host_passive else "no") in host_block
    elif protocol == "ospf":
        host_block = native.split("interface hostnet\n", 1)[1].split("!", 1)[0]
        assert ("ip ospf passive" in host_block) == host_passive
    else:
        assert ("passive-interface hostnet\n" in native) == host_passive


@pytest.mark.parametrize("old_mode,policy", [("legacy", "all-local"), ("router-transit-only", "router-links")])
def test_old_ospf_api_is_a_view_of_the_shared_interface_policy(old_mode, policy):
    autonomous_system = Base().createAutonomousSystem(2)
    assert autonomous_system.setOspfMode(old_mode) is autonomous_system
    assert autonomous_system.getIgpInterfacePolicy() == policy and autonomous_system.hasIgpInterfacePolicy()
    assert autonomous_system.getOspfMode() == old_mode and autonomous_system.hasOspfMode()
    assert "_AutonomousSystem__ospf_mode" not in autonomous_system.__dict__
    assert "_AutonomousSystem__ospf_mode_explicit" not in autonomous_system.__dict__
    autonomous_system.setIgpInterfacePolicy("router-links" if policy == "all-local" else "all-local")
    assert autonomous_system.getOspfMode() != old_mode


@pytest.mark.parametrize("protocol", ["ospf", "rip"])
@pytest.mark.parametrize("old_mode,explicit", [("legacy", False), ("legacy", True), ("router-transit-only", True)])
def test_old_ospf_policy_fields_survive_dump_load_as_common_igp_intent(tmp_path, protocol, old_mode, explicit):
    emulator, base, _ = createChain(rip=Ospf() if protocol == "ospf" else Rip(), backend="bird")
    autonomous_system = base.getAutonomousSystem(2).setIgpMode(protocol)
    del autonomous_system.__dict__["_AutonomousSystem__igp_interface_policy"]
    autonomous_system.__dict__["_AutonomousSystem__ospf_mode"] = old_mode
    autonomous_system.__dict__["_AutonomousSystem__ospf_mode_explicit"] = explicit
    component = tmp_path / "old-interface-policy.bin"
    emulator.dump(str(component))
    restored = Emulator()
    restored.load(str(component))
    restored_as = restored.getLayer("Base").getAutonomousSystem(2)
    expected = "router-links" if old_mode == "router-transit-only" or not explicit and protocol == "rip" else "all-local"
    assert restored_as.getIgpInterfacePolicy() == expected
    assert restored_as.hasIgpInterfacePolicy() == explicit
    restored.render()
    router = restored.getRegistry().get("2", "rnode", "r1")
    if protocol == "ospf":
        assert "lan1" in get_ospf_interface_intents(router)["passive" if expected == "router-links" else "active"]
    else:
        assert readOptions(router)["lan1"]["passive"] == (expected == "router-links")
    restored_as.setIgpInterfacePolicy("all-local" if expected == "router-links" else "router-links")
    assert restored_as.getIgpInterfacePolicy() != expected


def test_rip_explicit_passive_override_takes_precedence_over_common_interface_policy():
    emulator, base, routers = createChain(rip=Rip().setInterfaceOptions(2, "r1", "lan1", passive=False))
    base.getAutonomousSystem(2).setIgpInterfacePolicy("router-links")
    emulator.render()
    assert not readOptions(routers["r1"])["lan1"]["passive"]


@pytest.mark.parametrize("mode", ["bgp", "isis", "ospf+rip", "", None, True, 2])
def test_invalid_as_igp_mode_preserves_the_previous_choice(mode):
    autonomous_system = Base().createAutonomousSystem(2).setIgpMode("rip")
    with pytest.raises(AssertionError, match="unsupported IGP mode"):
        autonomous_system.setIgpMode(mode)
    assert autonomous_system.getIgpMode() == "rip"


@pytest.mark.parametrize("rip_first", [False, True])
@pytest.mark.parametrize("backend", ["bird", "frr"])
def test_two_igp_layers_default_to_ospf_independently_of_layer_order(rip_first, backend):
    emulator, base = Emulator(), Base()
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork("net0")
    routers = [as2.createRouter(name).joinNetwork("net0").setRoutingBackend(backend) for name in ("r1", "r2")]
    layers = [Rip(), Ospf()] if rip_first else [Ospf(), Rip()]
    for layer in [base, Routing(), *layers, Ibgp()]:
        emulator.addLayer(layer)
    emulator.render()
    assert as2.getIgpMode() == "ospf" and not as2.hasIgpMode()
    for router in routers:
        assert get_igp_protocol(router) == "ospf" and not get_rip_interface_intents(router)
        assert all(session["igp_table"] == "t_ospf" for session in get_bgp_sessions(router))
        native = readFile(router, "/etc/bird/bird.conf" if backend == "bird" else "/etc/frr/frr.conf")
        assert ("protocol ospf" if backend == "bird" else "router ospf") in native
        assert ("protocol rip" if backend == "bird" else "router rip") not in native


@pytest.mark.parametrize("layer,mode", [(Ospf, "rip"), (Rip, "ospf")])
def test_explicit_as_igp_requires_the_selected_protocol_layer(layer, mode):
    emulator, base, _ = createChain(rip=layer())
    base.getAutonomousSystem(2).setIgpMode(mode)
    with pytest.raises(ValueError, match="IGP layer is missing"):
        emulator.render()


def test_rip_layer_alone_does_not_change_default_ospf():
    emulator, base, routers = createChain(backend="bird", igp=None)
    with pytest.raises(ValueError, match=r"AS2 selects ospf.*IGP layer is missing; add Ospf\(\)"):
        emulator.render()
    as2 = base.getAutonomousSystem(2)
    assert as2.getIgpMode() == "ospf" and not as2.hasIgpMode()
    assert all(not get_rip_interface_intents(router) for router in routers.values())


@pytest.mark.parametrize("mode", ["ospf", "rip"])
def test_explicit_as_igp_selects_one_of_the_installed_layers(mode):
    emulator, base, routers = createChain()
    base.getAutonomousSystem(2).setIgpMode(mode)
    emulator.addLayer(Ospf())
    emulator.render()
    for router in routers.values():
        assert get_igp_protocol(router) == mode
        assert all(session["igp_table"] == "t_" + mode for session in get_bgp_sessions(router))


def test_as_igp_choice_survives_component_dump_and_load(tmp_path):
    emulator, base, _ = createChain(backend="bird")
    base.getAutonomousSystem(2).setIgpMode("rip").setIgpInterfacePolicy("all-local")
    emulator.addLayer(Ospf())
    component = tmp_path / "as-igp.bin"
    emulator.dump(str(component))
    restored = Emulator()
    restored.load(str(component))
    assert restored.getLayer("Base").getAutonomousSystem(2).getIgpMode() == "rip"
    assert restored.getLayer("Base").getAutonomousSystem(2).getIgpInterfacePolicy() == "all-local"
    restored.render()
    assert get_igp_protocol(restored.getRegistry().get("2", "rnode", "r1")) == "rip"


def test_as_components_saved_before_igp_modes_default_to_ospf(tmp_path):
    emulator, base, _ = createChain(rip=Ospf(), backend="bird")
    autonomous_system = base.getAutonomousSystem(2)
    del autonomous_system.__dict__["_AutonomousSystem__igp_mode"]
    del autonomous_system.__dict__["_AutonomousSystem__igp_mode_explicit"]
    component = tmp_path / "old-as.bin"
    emulator.dump(str(component))
    restored = Emulator()
    restored.load(str(component))
    restored_as = restored.getLayer("Base").getAutonomousSystem(2)
    assert restored_as.getIgpMode() == "ospf" and not restored_as.hasIgpMode()
    restored.render()
    assert get_igp_protocol(restored.getRegistry().get("2", "rnode", "r1")) == "ospf"


def test_component_merge_preserves_each_as_igp_choice():
    components = []
    for asn, mode, policy in [(2, "rip", "all-local"), (3, "ospf", "router-links")]:
        emulator, base = Emulator(), Base()
        autonomous_system = base.createAutonomousSystem(asn).setIgpMode(mode).setIgpInterfacePolicy(policy)
        autonomous_system.createNetwork("net0")
        autonomous_system.createRouter("r0").joinNetwork("net0")
        for layer in [base, Routing(), Ospf(), Rip()]:
            emulator.addLayer(layer)
        components.append(emulator)
    merged = components[0].merge(components[1], DEFAULT_MERGERS)
    merged.render()
    for asn, mode, policy in [(2, "rip", "all-local"), (3, "ospf", "router-links")]:
        assert merged.getLayer("Base").getAutonomousSystem(asn).getIgpMode() == mode
        assert merged.getLayer("Base").getAutonomousSystem(asn).getIgpInterfacePolicy() == policy
        assert get_igp_protocol(merged.getRegistry().get(str(asn), "rnode", "r0")) == mode


@pytest.mark.parametrize("as_level", [False, True])
def test_current_mpls_path_rejects_an_explicit_rip_igp(as_level):
    from seedemu.layers import Mpls
    emulator, base, _ = createChain(backend="frr")
    as2 = base.getAutonomousSystem(2).setIgpMode("rip")
    mpls = Mpls()
    if as_level:
        as2.setCoreForwarding("mpls")
    else:
        mpls.enableOn(2)
    emulator.addLayer(mpls)
    with pytest.raises(ValueError, match="current MPLS/LDP implementation requires OSPF"):
        emulator.render()


def test_current_mpls_path_provides_default_ospf_with_a_rip_layer_present():
    from seedemu.layers import Mpls
    emulator, base, routers = createChain(backend="frr", igp=None)
    as2 = base.getAutonomousSystem(2).setCoreForwarding("mpls")
    emulator.addLayer(Mpls())
    emulator.render()
    assert as2.getIgpMode() == "ospf"
    for router in routers.values():
        assert not get_rip_interface_intents(router)
        assert "router ospf" in readFile(router, "/etc/frr/frr.conf")


@pytest.mark.parametrize("layer,mode", [(Ospf, "ospf"), (Rip, "rip")])
def test_saved_layer_scope_does_not_override_as_igp_selection(layer, mode, tmp_path):
    protocol = layer()
    protocol.__dict__["_{}__asns".format(layer.__name__)] = set()
    emulator, _, _ = createChain(rip=protocol, backend="bird", igp=None if mode == "ospf" else mode)
    component = tmp_path / "old-layer-scope.bin"
    emulator.dump(str(component))
    restored = Emulator()
    restored.load(str(component))
    assert restored.getLayer("Base").getAutonomousSystem(2).getIgpMode() == mode
    restored.render()
    assert get_igp_protocol(restored.getRegistry().get("2", "rnode", "r1")) == mode


def test_default_merger_preserves_policies_and_rejects_conflicts():
    first = Rip().setTimers(update=2, timeout=12, garbage=8).maskAsn(3)
    first.setNetworkOptions(2, "net12", metric=2)
    second = Rip().markAsStub(2, "lan1").maskNetwork(2, "mgmt")
    second.setNetworkOptions(2, "net12", poison_reverse=False)
    second.setInterfaceOptions(2, "r1", "net12", metric=3)
    merged = DefaultRipMerger().doMerge(first, second)
    assert any(merger.getTargetType() == "RipLayer" for merger in DEFAULT_MERGERS)
    assert merged.getTimers() == first.getTimers()
    assert merged.getNetworkOptions(2, "net12") == {"metric": 2, "poison_reverse": False}
    assert merged.getInterfaceOptions(2, "r1", "net12") == {"metric": 3}
    assert merged.getMaskedAsns() == {3} and merged.getMaskedNetworks() == {(2, "mgmt")}
    assert merged.getStubs() == {(2, "lan1")}
    with pytest.raises(ValueError, match="conflicting RIP networks"):
        DefaultRipMerger().doMerge(first, Rip().setNetworkOptions(2, "net12", metric=4))
    with pytest.raises(ValueError, match="conflicting RIP defaults"):
        DefaultRipMerger().doMerge(first, Rip().setTimers(update=5))


def test_copied_getters_and_component_dump_load(tmp_path):
    rip = Rip().setNetworkOptions(2, "net12", metric=2)
    options = rip.getNetworkOptions(2, "net12")
    options["metric"] = 15
    assert rip.getNetworkOptions(2, "net12")["metric"] == 2
    emulator, _, _ = createChain(rip)
    component = tmp_path / "rip.bin"
    emulator.dump(str(component))
    restored = Emulator()
    restored.load(str(component))
    assert restored.getLayer("Rip").getConfiguration() == rip.getConfiguration()
    restored.render()
    router = restored.getRegistry().get("2", "rnode", "r1")
    intent = get_rip_interface_intents(router)
    intent["interfaces"].clear()
    assert get_rip_interface_intents(router)["interfaces"]


def test_emulator_component_merge_keeps_rip_policies_per_as():
    components = []
    for asn in (2, 3):
        emulator, base = Emulator(), Base()
        autonomous_system = base.createAutonomousSystem(asn).setIgpMode("rip")
        autonomous_system.createNetwork("net0")
        autonomous_system.createRouter("r0").joinNetwork("net0")
        emulator.addLayer(base)
        emulator.addLayer(Routing())
        emulator.addLayer(Rip().setNetworkOptions(asn, "net0", metric=asn))
        components.append(emulator)
    merged = components[0].merge(components[1], DEFAULT_MERGERS)
    merged.render()
    for asn in (2, 3):
        router = merged.getRegistry().get(str(asn), "rnode", "r0")
        assert readOptions(router)["net0"]["metric"] == asn


def selectRipInB00(source):
    """Adapt a B00 source copy with explicit AS choices and the Rip layer."""
    assert source.count("    emu.addLayer(Ospf())") == 1
    source = source.replace(
        "    emu.addLayer(Ospf())",
        '    for asn in base.getAsns():\n'
        '        base.getAutonomousSystem(asn).setIgpMode("rip")\n'
        '    emu.addLayer(Rip())',
    )
    return source.replace("from seedemu.layers import ", "from seedemu.layers import Rip, ", 1)


def test_b00_renders_with_explicit_rip_as_selection():
    path = REPO_ROOT / "examples/internet/B00_mini_internet/mini_internet.py"
    source = selectRipInB00(path.read_text())
    namespace = {"__name__": "b00_rip_selection", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)
    emulator = namespace["build_emulator"]()
    emulator.render()
    routers = [node for (_, kind, _), node in emulator.getRegistry().getAll().items() if kind == "rnode"]
    assert len(routers) == 27 and all(get_rip_interface_intents(router) for router in routers)
    assert not any(layer.getName() == "Ospf" for layer in emulator.getLayers())
    for router in routers:
        assert all(session["igp_table"] == "t_rip" for session in get_bgp_sessions(router) if session["kind"] == "ibgp")


@pytest.mark.parametrize("example", ["b00-ospf", "b00-rip", "b51-bird", "b51-frr", "b51-mixed"])
def test_example_cli_preserves_addresses_and_selected_network_mode(example, tmp_path):
    import ipaddress
    import yaml

    directory, filename = ("B51_rip", "rip.py") if example.startswith("b51") else ("B00_mini_internet", "mini_internet.py")
    path = REPO_ROOT / "examples/internet" / directory / filename
    source = path.read_text()
    if example == "b00-rip":
        source = selectRipInB00(source)
    namespace = {"__name__": "example_deployment_regression", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)
    output = tmp_path / "output"
    arguments = {"output": str(output)}
    if example.startswith("b51"):
        arguments["backend"] = example.split("-", 1)[1]
    namespace["run"](**arguments)
    compose = yaml.safe_load((output / "docker-compose.yml").read_text())
    prefix_label = "org.seedsecuritylabs.seedemu.meta.prefix"
    emulated = [ipaddress.ip_network(network["labels"][prefix_label]) for network in compose["networks"].values()]
    transport = [ipaddress.ip_network(network["ipam"]["config"][0]["subnet"]) for network in compose["networks"].values()]
    assert transport == emulated
    nodes = [service for service in compose["services"].values() if "org.seedsecuritylabs.seedemu.meta.role" in service.get("labels", {})]
    assert len(nodes) == 58
    for service in nodes:
        context = output / service["build"]
        dockerfile = (context / "Dockerfile").read_text()
        def copied_file(destination):
            line = next(line for line in dockerfile.splitlines() if line.startswith("COPY ") and line.endswith(" " + destination))
            return (context / line.split()[1]).read_text()
        start = copied_file("/start.sh")
        declared = [str(value) for key, value in service["labels"].items() if key.endswith(".address")]
        assert "/replace_address.sh" not in start
        assert not any(line.startswith("COPY ") and line.endswith(" /dummy_addr_map.txt")
                       for line in dockerfile.splitlines())
        assert {address["ipv4_address"] for address in service["networks"].values()} == {
            str(ipaddress.ip_interface(address).ip) for address in declared
        }
        if example.startswith("b51") and service["labels"]["org.seedsecuritylabs.seedemu.meta.role"] == "BorderRouter":
            exchanges = [str(value) for key, value in service["labels"].items() if key.endswith(".name") and str(value).startswith("ix")]
            backend = service["labels"].get("org.seedsecuritylabs.seedemu.meta.seedemu_bgp_backend", "bird")
            if backend == "bird":
                direct = copied_file("/etc/bird/bird.conf").split("protocol direct local_nets", 1)[1].split("\n}", 1)[0]
                assert all('interface "' + exchange + '"' in direct for exchange in exchanges)
            else:
                configuration = copied_file("/etc/frr/frr.conf")
                for exchange in exchanges:
                    prefix = next(network["labels"][prefix_label] for network in compose["networks"].values()
                                  if network["labels"]["org.seedsecuritylabs.seedemu.meta.name"] == exchange)
                    assert any(line.startswith("ip prefix-list PL_CONNECTED4_TO_BGP ") and line.endswith(" permit " + prefix)
                               for line in configuration.splitlines())


@pytest.mark.parametrize("backend", ["bird", "frr", "mixed"])
def test_b51_renders_for_each_supported_backend(backend):
    from examples.internet.B51_rip.rip import buildEmulator
    emulator = buildEmulator(backend=backend)
    emulator.render()
    base = emulator.getLayer("Base")
    assert {asn for asn in base.getAsns() if base.getAutonomousSystem(asn).getIgpMode() == "ospf"} == {3, 4, 12}
    for name in ("Ospf", "Rip"):
        assert not emulator.getLayer(name).getMaskedAsns()
        assert not emulator.getLayer(name).getMaskedNetworks()
    routers = [node for (_, kind, _), node in emulator.getRegistry().getAll().items() if kind == "rnode"]
    assert sum(get_igp_protocol(node) == "ospf" for node in routers) == 9
    assert sum(get_igp_protocol(node) == "rip" for node in routers) == 18
    for node in routers:
        expected = "ospf" if node.getAsn() in {3, 4, 12} else "rip"
        assert get_igp_protocol(node) == expected
        assert all(session["igp_table"] == "t_" + expected for session in get_bgp_sessions(node) if session["kind"] == "ibgp")
        bird, frr = readFile(node, "/etc/bird/bird.conf"), readFile(node, "/etc/frr/frr.conf")
        if node.getRoutingBackend() == "bird":
            assert "protocol " + expected in bird
        else:
            assert "router " + expected in frr
    router = emulator.getRegistry().get("2", "rnode", "r101")
    options = readOptions(router)
    assert options["net_100_101"]["metric"] == 4
    assert options["net_101_102"]["metric"] == 3
    assert options["net_101_102"]["poison_reverse"] is False
    assert "mgmt" not in options


def test_b51_manifest_and_runtime_router_discovery(tmp_path):
    from examples.internet.B51_rip.rip import buildEmulator
    from examples.internet.B51_rip.test_runtime import discoverRouters
    from seedemu.compiler import Docker
    from seedemu.testing.registry import create_runner
    from seedemu.testing import ComposeRuntimeTest
    manifest = REPO_ROOT / "examples/internet/B51_rip/example.yaml"
    runner = create_runner(manifest)
    assert runner.runner_name == "internet" and len(runner.manifest["probes"]) == 3
    emulator = buildEmulator()
    emulator.render()
    emulator.compile(Docker(), str(tmp_path / "output"))
    test = ComposeRuntimeTest.__new__(ComposeRuntimeTest)
    import yaml
    test.compose = yaml.safe_load((tmp_path / "output/docker-compose.yml").read_text())
    routers = discoverRouters(test)
    assert len(routers) == 27
    assert {router.labels["org.seedsecuritylabs.seedemu.meta.seedemu_igp"] for router in routers} == {"ospf", "rip"}
    assert {router.labels["org.seedsecuritylabs.seedemu.meta.seedemu_bgp_backend"] for router in routers} == {"bird", "frr"}


@pytest.mark.parametrize("wrapped", [False, True])
@pytest.mark.parametrize("state", ["Established", "Active"])
@pytest.mark.parametrize("igp", ["ospf", "rip"])
def test_frr_runtime_bgp_check_accepts_both_json_shapes_and_rejects_down_peers(monkeypatch, wrapped, state, igp):
    import json
    import shlex
    import subprocess
    from examples.internet.B51_rip.test_runtime import checkRouter, META
    from seedemu.testing.runtime import ComposeService

    summary = {"peers": {"10.0.0.2": {"state": state}}}
    if wrapped:
        summary = {"ipv4Unicast": summary}
    monkeypatch.setattr(subprocess, "check_output", lambda command: json.dumps(summary).encode())

    class Runtime:
        def exec_check(self, name, router, command, **options):
            if "established BGP sessions" in name:
                executable, flag, code = shlex.split(command)
                assert (executable, flag) == ("python3", "-c")
                exec(code, {})

    router = ComposeService("r1", "", {META + "seedemu_bgp_backend": "frr", META + "seedemu_igp": igp})
    peer = ComposeService("r2", "", {META + "loopback_addr": "10.0.0.2"})
    if state == "Established":
        checkRouter(Runtime(), router, [peer])
    else:
        with pytest.raises(AssertionError):
            checkRouter(Runtime(), router, [peer])


def test_b51_cli_prefers_its_repository_over_another_examples_namespace(tmp_path):
    import os
    import subprocess
    import sys
    other = tmp_path / "other"
    source = other / "examples/internet/B00_mini_internet/mini_internet.py"
    source.parent.mkdir(parents=True)
    source.write_text("raise RuntimeError('wrong repository')\n")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join((str(other), str(REPO_ROOT)))
    component = tmp_path / "rip.bin"
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "examples/internet/B51_rip/rip.py"), "--dumpfile", str(component)],
        cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert component.exists()

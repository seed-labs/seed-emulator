#!/usr/bin/env python3
"""Scenario registry with explicit benchmark tracks."""

from pathlib import Path

from scenarios.wrong_asn import WrongAsnScenario
from scenarios.service_not_running import ServiceNotRunningScenario
from scenarios.dns_failure import DnsFailureScenario
from scenarios.missing_bgp_peering import MissingBgpPeeringScenario
from scenarios.missing_ospf_adjacency import MissingOspfAdjacencyScenario
from scenarios.wrong_docker_network import WrongDockerNetworkScenario
from scenarios.route_reflector_misconfig import RouteReflectorMisconfigScenario
from scenarios.mpls_label_problem import MplsLabelProblemScenario
from scenarios.ipv6_route_missing import Ipv6RouteMissingScenario
from scenarios.dual_fault_bgp_ospf import DualFaultBgpOspfScenario
from scenarios.dual_fault_dns_network import DualFaultDnsNetworkScenario
from scenarios.cascading_bgp_to_ospf import CascadingBgpToOspfScenario
from scenarios.randomized_transit_acl import RandomizedTransitAclScenario
from scenarios.cascading_network_to_bgp import CascadingNetworkToBgpScenario
from scenarios.firewall_misconfiguration import FirewallMisconfigurationScenario
from scenarios.frr_route_policy import FrrRoutePolicyScenario
from scenarios.bird_route_policy import BirdRoutePolicyScenario
from scenarios.bind9_config_error import Bind9ConfigErrorScenario
from scenarios.wireguard_allowed_ips import WireGuardAllowedIpsScenario
from scenarios.netem_packet_loss import NetemPacketLossScenario
from scenarios.kea_dhcp_config import KeaDhcpConfigScenario
from generator.runtime import load_generated_scenarios

# Full catalog. Track filtering decides which scenarios contribute to a score.
BUILTIN_SCENARIOS = [
    WrongAsnScenario,
    ServiceNotRunningScenario,
    DnsFailureScenario,
    MissingBgpPeeringScenario,
    MissingOspfAdjacencyScenario,
    WrongDockerNetworkScenario,
    RouteReflectorMisconfigScenario,
    MplsLabelProblemScenario,
    Ipv6RouteMissingScenario,
    CascadingBgpToOspfScenario,
    DualFaultBgpOspfScenario,
    DualFaultDnsNetworkScenario,
    CascadingNetworkToBgpScenario,
    FirewallMisconfigurationScenario,
    FrrRoutePolicyScenario,
    BirdRoutePolicyScenario,
    Bind9ConfigErrorScenario,
    WireGuardAllowedIpsScenario,
    NetemPacketLossScenario,
    KeaDhcpConfigScenario,
    RandomizedTransitAclScenario,
]

BENCHMARKS_DIR = Path(__file__).resolve().parents[1]
GENERATED_SCENARIOS = list(load_generated_scenarios(BENCHMARKS_DIR))
SCENARIO_CATALOG = BUILTIN_SCENARIOS + GENERATED_SCENARIOS

ALL_SCENARIOS = SCENARIO_CATALOG
MAIN_SCENARIOS = [
    cls for cls in SCENARIO_CATALOG if cls.main_score_eligible
]
SCENARIO_MAP = {cls.name: cls for cls in SCENARIO_CATALOG}
SCENARIO_MAP["cascading_bgp_to_ospf_01"] = CascadingBgpToOspfScenario


def get_scenario(name: str):
    """获取场景类。"""
    return SCENARIO_MAP.get(name)


def list_scenarios():
    """列出所有场景名称。"""
    return [cls.name for cls in SCENARIO_CATALOG]


def get_scenarios_by_topology(topology: str):
    """获取指定拓扑的所有场景。"""
    return [cls for cls in SCENARIO_CATALOG if cls.topology == topology]


def get_scenarios_by_track(track: str):
    """Return scenarios in one explicit benchmark track."""
    if track == "all":
        return list(SCENARIO_CATALOG)
    if track == "main":
        return list(MAIN_SCENARIOS)
    return [
        cls for cls in SCENARIO_CATALOG
        if cls.benchmark_track == track
    ]

#!/usr/bin/env python3
"""
场景 7: 路由反射器配置错误
"""

from scenarios.base import BaseScenario


class RouteReflectorMisconfigScenario(BaseScenario):
    name = "route_reflector_misconfig_01"
    description = "路由反射器配置错误"
    topology = "R02_bgp_free_core_mpls"
    fault_type = "route_reflector_misconfig"
    diagnosis_artifact = "FRR running-config"
    diagnosis_faulty_value = "no neighbor 10.0.0.10 route-reflector-client"
    diagnosis_expected_value = "neighbor 10.0.0.10 route-reflector-client"
    benchmark_track = "network_control_plane"
    difficulty = "advanced"

    def get_inject_cmd(self) -> str:
        return "docker exec as9brd-edge0-10.114.0.9 vtysh -c 'configure terminal' -c 'router bgp 9' -c 'no neighbor 10.0.0.10 route-reflector-client' -c 'end' -c 'write memory'"

    def get_verify_cmd(self) -> str:
        return (
            "docker exec as9brd-edge0-10.114.0.9 sh -c \""
            "vtysh -c 'show running-config' | "
            "grep -q 'neighbor 10.0.0.10 route-reflector-client' && "
            "vtysh -c 'show bgp ipv4 unicast summary' | "
            "grep -q '10.0.0.10' && "
            "echo ROUTE_REFLECTOR_OK\""
        )

    def get_fix_cmd(self) -> str:
        return "docker exec as9brd-edge0-10.114.0.9 vtysh -c 'configure terminal' -c 'router bgp 9' -c 'neighbor 10.0.0.10 route-reflector-client' -c 'end' -c 'write memory'"

    def check_verified(self, output: str) -> bool:
        return "ROUTE_REFLECTOR_OK" in output

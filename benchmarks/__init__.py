#!/usr/bin/env python3
"""
Benchmark suite for evaluating AI agents diagnosing Internet emulator failures.

Fault categories:
1. missing_bgp_peering - Missing BGP peering session
2. wrong_asn - Incorrect ASN assignment
3. route_reflector_misconfig - Route reflector misconfiguration
4. missing_ospf_adjacency - Missing OSPF adjacency
5. wrong_docker_network - Wrong Docker network configuration
6. service_not_running - Service not running
7. dns_failure - DNS resolution failure
8. mpls_label_problem - MPLS label issue
9. ipv6_route_missing - Missing IPv6 route
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import yaml


class FaultCategory(Enum):
    """Categories of faults that can be injected into the emulator."""
    MISSING_BGP_PEERING = "missing_bgp_peering"
    WRONG_ASN = "wrong_asn"
    ROUTE_REFLECTOR_MISCONFIG = "route_reflector_misconfig"
    MISSING_OSPF_ADJACENCY = "missing_ospf_adjacency"
    WRONG_DOCKER_NETWORK = "wrong_docker_network"
    SERVICE_NOT_RUNNING = "service_not_running"
    DNS_FAILURE = "dns_failure"
    MPLS_LABEL_PROBLEM = "mpls_label_problem"
    IPV6_ROUTE_MISSING = "ipv6_route_missing"


@dataclass
class FaultInjection:
    """Describes a single fault to inject into the emulator."""
    category: FaultCategory
    target: str  # e.g., "AS150", "router0", "ix100"
    description: str
    injection_point: str  # Python code location or config file
    injection_method: str  # How to inject the fault
    expected_symptoms: List[str]  # What symptoms should appear
    verification_command: str  # Command to verify fault is present
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class BenchmarkScenario:
    """A complete benchmark scenario with fault injection."""
    name: str
    description: str
    base_topology: str  # Path to base topology script
    faults: List[FaultInjection]
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "base_topology": self.base_topology,
            "faults": [
                {
                    "category": f.category.value,
                    "target": f.target,
                    "description": f.description,
                    "injection_point": f.injection_point,
                    "injection_method": f.injection_method,
                    "expected_symptoms": f.expected_symptoms,
                    "verification_command": f.verification_command,
                    "severity": f.severity,
                }
                for f in self.faults
            ],
            "difficulty": self.difficulty,
            "tags": self.tags or [],
        }


# ============================================================================
# Scenario Definitions
# ============================================================================

def create_missing_bgp_peering_scenario() -> BenchmarkScenario:
    """Scenario: Missing BGP peering between two ASes at an IX."""
    return BenchmarkScenario(
        name="missing_bgp_peering_01",
        description="BGP peering session missing between AS150 and AS2 at IX100. "
                    "AS150 cannot reach AS2's prefixes.",
        base_topology="examples/internet/B00_mini_internet/mini_internet.py",
        faults=[
            FaultInjection(
                category=FaultCategory.MISSING_BGP_PEERING,
                target="AS150-IX100",
                description="eBGP peering between AS150 and AS2 at IX100 is removed",
                injection_point="Ebgp layer: removePrivatePeerings or removeRsPeer",
                injection_method="Remove the ebgp.addPrivatePeerings(100, 150, 2) call",
                expected_symptoms=[
                    "AS150 cannot ping AS2's hosts",
                    "BGP table on AS150 router missing AS2 prefixes",
                    "Traceroute from AS150 to AS2 fails",
                ],
                verification_command="docker exec as150r-router0 vtysh -c 'show ip bgp'",
                severity="high",
            )
        ],
        difficulty="easy",
        tags=["bgp", "peering", "connectivity"],
    )


def create_wrong_asn_scenario() -> BenchmarkScenario:
    """Scenario: Router configured with wrong ASN."""
    return BenchmarkScenario(
        name="wrong_asn_01",
        description="Router in AS2 is misconfigured with ASN 999 instead of 2, "
                    "causing BGP session failures.",
        base_topology="examples/internet/B00_mini_internet/mini_internet.py",
        faults=[
            FaultInjection(
                category=FaultCategory.WRONG_ASN,
                target="AS2-router0",
                description="Router's BGP local-as set to 999 instead of 2",
                injection_point="BGP daemon configuration (FRR: bgp 999)",
                injection_method="Modify router's BGP config to use wrong local-as",
                expected_symptoms=[
                    "BGP sessions to peers show 'Connection refused' or ASN mismatch",
                    "No routes learned from peers",
                    "Peers report 'wrong remote AS' errors",
                ],
                verification_command="docker exec as2r-router0 vtysh -c 'show ip bgp summary'",
                severity="critical",
            )
        ],
        difficulty="easy",
        tags=["bgp", "asn", "configuration"],
    )


def create_route_reflector_misconfig_scenario() -> BenchmarkScenario:
    """Scenario: Route reflector not properly configured."""
    return BenchmarkScenario(
        name="route_reflector_misconfig_01",
        description="Route reflector in AS4 is misconfigured - not reflecting routes "
                    "to client routers, causing internal routing failures.",
        base_topology="examples/routing/R01_routing_matrix/example.yaml",
        faults=[
            FaultInjection(
                category=FaultCategory.ROUTE_REFLECTOR_MISCONFIG,
                target="AS4-rr",
                description="Route reflector missing 'neighbor X route-reflector-client' config",
                injection_point="Ibgp layer: route reflector configuration",
                injection_method="Remove route-reflector-client designation from RR config",
                expected_symptoms=[
                    "Client routers don't receive reflected routes",
                    "iBGP full mesh required but not present",
                    "Some internal prefixes unreachable",
                ],
                verification_command="docker exec as4r-rr vtysh -c 'show ip bgp neighbors'",
                severity="high",
            )
        ],
        difficulty="medium",
        tags=["bgp", "route-reflector", "ibgp"],
    )


def create_missing_ospf_adjacency_scenario() -> BenchmarkScenario:
    """Scenario: OSPF adjacency not forming between routers."""
    return BenchmarkScenario(
        name="missing_ospf_adjacency_01",
        description="OSPF adjacency missing between two routers in same AS due to "
                    "mismatched area ID or network statement.",
        base_topology="examples/internet/B00_mini_internet/mini_internet.py",
        faults=[
            FaultInjection(
                category=FaultCategory.MISSING_OSPF_ADJACENCY,
                target="AS2-internal-link",
                description="OSPF area mismatch on internal link between routers",
                injection_point="OSPF configuration: area ID mismatch",
                injection_method="Set different OSPF area IDs on connected interfaces",
                expected_symptoms=[
                    "OSPF neighbors not in FULL state",
                    "Routes not being learned via OSPF",
                    "show ip ospf neighbor shows no adjacency",
                ],
                verification_command="docker exec as2r-router0 vtysh -c 'show ip ospf neighbor'",
                severity="high",
            )
        ],
        difficulty="medium",
        tags=["ospf", "adjacency", "routing"],
    )


def create_wrong_docker_network_scenario() -> BenchmarkScenario:
    """Scenario: Container connected to wrong Docker network."""
    return BenchmarkScenario(
        name="wrong_docker_network_01",
        description="A router container is connected to the wrong Docker network, "
                    "causing Layer 2 isolation from its intended peers.",
        base_topology="examples/internet/B00_mini_internet/mini_internet.py",
        faults=[
            FaultInjection(
                category=FaultCategory.WRONG_DOCKER_NETWORK,
                target="as150-router0",
                description="Router's IX interface connected to wrong bridge network",
                injection_point="Docker compose: networks section",
                injection_method="Change network assignment in docker-compose.yml",
                expected_symptoms=[
                    "Cannot reach IX peering LAN",
                    "No BGP sessions established at IX",
                    "ARP requests unanswered",
                ],
                verification_command="docker exec as150-router0 ip addr show",
                severity="critical",
            )
        ],
        difficulty="easy",
        tags=["docker", "network", "layer2"],
    )


def create_service_not_running_scenario() -> BenchmarkScenario:
    """Scenario: Critical service container not starting."""
    return BenchmarkScenario(
        name="service_not_running_01",
        description="DNS authoritative server container fails to start due to "
                    "configuration error, causing DNS resolution failures.",
        base_topology="examples/internet/B01_dns_component/dns_component.py",
        faults=[
            FaultInjection(
                category=FaultCategory.SERVICE_NOT_RUNNING,
                target="dns-server-com",
                description="DNS server container exits immediately after start",
                injection_point="Named.conf or zone file syntax error",
                injection_method="Introduce syntax error in BIND configuration",
                expected_symptoms=[
                    "Container in 'exited' state",
                    "DNS queries timeout",
                    "dig/nslookup failures",
                ],
                verification_command="docker ps -a | grep dns",
                severity="high",
            )
        ],
        difficulty="easy",
        tags=["service", "docker", "dns"],
    )


def create_dns_failure_scenario() -> BenchmarkScenario:
    """Scenario: DNS resolution failing for specific domain."""
    return BenchmarkScenario(
        name="dns_failure_01",
        description="DNS resolution fails for example.com due to missing or "
                    "incorrect NS/A records in authoritative zone.",
        base_topology="examples/internet/B01_dns_component/dns_component.py",
        faults=[
            FaultInjection(
                category=FaultCategory.DNS_FAILURE,
                target="zone-example-com",
                description="Missing A record for www.example.com in zone file",
                injection_point="DomainNameService: zone record configuration",
                injection_method="Remove or corrupt A record in zone file",
                expected_symptoms=[
                    "dig www.example.com returns NXDOMAIN or SERVFAIL",
                    "Web service unreachable by hostname",
                    "DNSSEC validation failures if signed",
                ],
                verification_command="docker exec dns-server-com dig @localhost www.example.com",
                severity="medium",
            )
        ],
        difficulty="easy",
        tags=["dns", "resolution", "records"],
    )


def create_mpls_label_problem_scenario() -> BenchmarkScenario:
    """Scenario: MPLS label distribution not working properly."""
    return BenchmarkScenario(
        name="mpls_label_problem_01",
        description="MPLS LDP not establishing sessions between core routers, "
                    "causing label-switched path failures.",
        base_topology="examples/routing/R02_bgp_free_core_mpls/example.yaml",
        faults=[
            FaultInjection(
                category=FaultCategory.MPLS_LABEL_PROBLEM,
                target="AS2-core-routers",
                description="LDP session not established due to interface mismatch",
                injection_point="MPLS layer: LDP configuration",
                injection_method="Disable MPLS on one interface in the LSP path",
                expected_symptoms=[
                    "show mpls ldp neighbor shows no session",
                    "MPLS labels not being exchanged",
                    "Traffic taking unexpected IP path instead of LSP",
                ],
                verification_command="docker exec as2r-router0 vtysh -c 'show mpls ldp neighbor'",
                severity="high",
            )
        ],
        difficulty="hard",
        tags=["mpls", "ldp", "labels"],
    )


def create_ipv6_route_missing_scenario() -> BenchmarkScenario:
    """Scenario: IPv6 route not being advertised or received."""
    return BenchmarkScenario(
        name="ipv6_route_missing_01",
        description="IPv6 prefix not being advertised via BGP, causing IPv6 "
                    "connectivity failure while IPv4 works.",
        base_topology="examples/internet/B00_mini_internet/mini_internet.py",
        faults=[
            FaultInjection(
                category=FaultCategory.IPV6_ROUTE_MISSING,
                target="AS150-ipv6",
                description="IPv6 prefix not advertised in BGP due to missing network statement",
                injection_point="BGP configuration: address-family ipv6",
                injection_method="Remove IPv6 network statement from BGP config",
                expected_symptoms=[
                    "show bgp ipv6 unicast returns empty table",
                    "IPv6 ping fails between ASes",
                    "IPv4 connectivity works fine",
                ],
                verification_command="docker exec as150-router0 vtysh -c 'show bgp ipv6 unicast'",
                severity="medium",
            )
        ],
        difficulty="medium",
        tags=["ipv6", "bgp", "dual-stack"],
    )


# ============================================================================
# Scenario Registry
# ============================================================================

SCENARIO_REGISTRY = {
    "missing_bgp_peering_01": create_missing_bgp_peering_scenario,
    "wrong_asn_01": create_wrong_asn_scenario,
    "route_reflector_misconfig_01": create_route_reflector_misconfig_scenario,
    "missing_ospf_adjacency_01": create_missing_ospf_adjacency_scenario,
    "wrong_docker_network_01": create_wrong_docker_network_scenario,
    "service_not_running_01": create_service_not_running_scenario,
    "dns_failure_01": create_dns_failure_scenario,
    "mpls_label_problem_01": create_mpls_label_problem_scenario,
    "ipv6_route_missing_01": create_ipv6_route_missing_scenario,
}


def get_scenario(name: str) -> BenchmarkScenario:
    """Get a scenario by name."""
    if name not in SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIO_REGISTRY.keys())}")
    return SCENARIO_REGISTRY[name]()


def list_scenarios() -> List[str]:
    """List all available scenario names."""
    return list(SCENARIO_REGISTRY.keys())


def get_scenarios_by_category(category: FaultCategory) -> List[BenchmarkScenario]:
    """Get all scenarios that include a specific fault category."""
    results = []
    for creator in SCENARIO_REGISTRY.values():
        scenario = creator()
        if any(f.category == category for f in scenario.faults):
            results.append(scenario)
    return results


def export_scenario_json(scenario: BenchmarkScenario, output_path: Path):
    """Export scenario to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(scenario.to_dict(), f, indent=2)


def export_scenario_yaml(scenario: BenchmarkScenario, output_path: Path):
    """Export scenario to YAML file."""
    with open(output_path, 'w') as f:
        yaml.dump(scenario.to_dict(), f, default_flow_style=False)


if __name__ == "__main__":
    # Export all scenarios
    output_dir = Path("benchmarks/scenarios")
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, creator in SCENARIO_REGISTRY.items():
        scenario = creator()
        export_scenario_yaml(scenario, output_dir / f"{name}.yaml")
        print(f"Exported: {name}")

    print(f"\nTotal scenarios: {len(SCENARIO_REGISTRY)}")
    print("Categories covered:")
    for cat in FaultCategory:
        count = len(get_scenarios_by_category(cat))
        print(f"  {cat.value}: {count} scenario(s)")

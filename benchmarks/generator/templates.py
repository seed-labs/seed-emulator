"""Audited fault templates for deterministic scenario generation."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import Any, Callable, Dict, Iterable, Mapping, Tuple

from generator.models import ScenarioSpec


@dataclass(frozen=True)
class RenderedScenario:
    inject_command: str
    verify_command: str
    fix_command: str
    verifier_kind: str
    verifier_value: str


@dataclass(frozen=True)
class FaultTemplate:
    template_id: str
    topology: str
    fault_type: str
    difficulty: str
    description: str
    candidate_factory: Callable[[int, int], Dict[str, Any]]
    renderer: Callable[[Mapping[str, Any]], RenderedScenario]
    diagnosis_factory: Callable[
        [Mapping[str, Any]], Tuple[Tuple[str, ...], str, str, str]
    ]
    default_enabled: bool = True

    def candidate(self, sequence: int, seed: int) -> Dict[str, Any]:
        return self.candidate_factory(sequence, seed)

    def diagnosis(
        self, parameters: Mapping[str, Any]
    ) -> Tuple[Tuple[str, ...], str, str, str]:
        return self.diagnosis_factory(parameters)


BIRD_TARGETS = (
    "as2brd-r100-10.100.0.2",
    "as2brd-r101-10.101.0.2",
    "as2brd-r102-10.102.0.2",
    "as2brd-r105-10.105.0.2",
)

HOST_TARGETS = tuple(
    (
        f"as{asn}h-host_0-10.{asn}.0.71",
        f"as{asn}brd-router0-10.{asn}.0.254",
        f"10.{asn}.0.254",
    )
    for asn in range(150, 155)
)


def _bird_asn_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    target = BIRD_TARGETS[(sequence + seed) % len(BIRD_TARGETS)]
    block = sequence // len(BIRD_TARGETS)
    bad_asn = 64512 + ((block + seed) % 1000)
    if bad_asn == 2:
        bad_asn += 1
    return {"container": target, "correct_asn": 2, "bad_asn": bad_asn}


def _bird_asn_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = parameters["container"]
    correct = int(parameters["correct_asn"])
    bad = int(parameters["bad_asn"])
    return RenderedScenario(
        inject_command=(
            f"docker exec {container} sed -i "
            f"'s/as {correct};/as {bad};/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
        verify_command=(
            f"docker exec {container} sh -c \""
            "birdc show protocols | grep -Eq "
            "'BGP[[:space:]].*Established' && "
            f"grep -q 'as {correct};' /etc/bird/bird.conf && "
            "echo GENERATED_BGP_ASN_OK\""
        ),
        fix_command=(
            f"docker exec {container} sed -i "
            f"'s/as {bad};/as {correct};/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_BGP_ASN_OK",
    )


def _bird_asn_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "/etc/bird/bird.conf",
        f"AS {parameters['bad_asn']}",
        f"AS {parameters['correct_asn']}",
    )


def _dns_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    target, peer, peer_ip = HOST_TARGETS[(sequence + seed) % len(HOST_TARGETS)]
    documentation_nets = ("192.0.2", "198.51.100", "203.0.113")
    network = documentation_nets[(sequence + seed) % len(documentation_nets)]
    host_octet = 1 + ((sequence // len(HOST_TARGETS) + seed) % 253)
    return {
        "container": target,
        "peer_container": peer,
        "peer_ip": peer_ip,
        "bad_nameserver": f"{network}.{host_octet}",
        "expected_nameserver": "127.0.0.11",
    }


def _dns_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = parameters["container"]
    peer = parameters["peer_container"]
    peer_ip = parameters["peer_ip"]
    bad = parameters["bad_nameserver"]
    expected = parameters["expected_nameserver"]
    return RenderedScenario(
        inject_command=(
            f"docker exec {container} sh -c "
            f"'printf \"nameserver {bad}\\n\" > /etc/resolv.conf'"
        ),
        verify_command=(
            f"docker exec {container} sh -c '"
            f"grep -Eq \"^nameserver[[:space:]]+{expected.replace('.', '[.]')}$\" "
            "/etc/resolv.conf && "
            f"getent hosts {peer} | "
            f"grep -q \"^{peer_ip.replace('.', '[.]')}[[:space:]]\" && "
            "echo GENERATED_DNS_OK'"
        ),
        fix_command=(
            f"docker exec {container} sh -c "
            f"'printf \"nameserver {expected}\\noptions ndots:0\\n\" "
            "> /etc/resolv.conf'"
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_DNS_OK",
    )


def _dns_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "/etc/resolv.conf",
        f"nameserver {parameters['bad_nameserver']}",
        f"nameserver {parameters['expected_nameserver']}",
    )


def _ipv6_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    subnet_id = 1000 + ((sequence + seed) % 60000)
    subnet_hex = f"{subnet_id:x}"
    return {
        "container": "as151brd-router0-10.151.0.254",
        "prefix": f"2001:db8:{subnet_hex}::/64",
        "address": f"2001:db8:{subnet_hex}::1/64",
        "probe": f"2001:db8:{subnet_hex}::2",
        "interface": "dummy0",
    }


def _ipv6_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = parameters["container"]
    prefix = parameters["prefix"]
    address = parameters["address"]
    probe = parameters["probe"]
    interface = parameters["interface"]
    return RenderedScenario(
        inject_command=(
            f"docker exec {container} ip -6 addr del {address} dev {interface}"
        ),
        verify_command=(
            f"docker exec {container} sh -c \""
            f"ip -6 route show {prefix} | "
            f"grep -q '{prefix} dev {interface}' && "
            f"ip -6 route get {probe} | grep -q 'dev {interface}' && "
            "echo GENERATED_IPV6_ROUTE_OK\""
        ),
        fix_command=(
            f"docker exec {container} sh -c '"
            f"ip -6 route del {prefix} dev {interface} 2>/dev/null || true; "
            f"ip -6 addr del {address} dev {interface} 2>/dev/null || true; "
            f"ip -6 addr add {address} dev {interface}'"
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_IPV6_ROUTE_OK",
    )


def _ipv6_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "IPv6 route table",
        f"missing {parameters['prefix']}",
        f"{parameters['prefix']} dev {parameters['interface']}",
    )


def _container_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    target, _, _ = HOST_TARGETS[(sequence + seed) % len(HOST_TARGETS)]
    return {"container": target}


def _container_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = parameters["container"]
    return RenderedScenario(
        inject_command=f"docker stop {container}",
        verify_command=(
            "docker inspect --format '{{.State.Running}}' " f"{container}"
        ),
        fix_command=f"docker start {container}",
        verifier_kind="equals",
        verifier_value="true",
    )


def _container_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "Docker container state",
        "stopped",
        "running",
    )


RANDOM_SOURCE_ASN = 111
RANDOM_SOURCE_IX = 201
# Audited live peers attached to IX 201 by topology seed 20260724. Targeting
# their IX addresses exercises a real router ACL without depending on the VM's
# host-wide bridge-netfilter policy for container-to-container transit.
RANDOM_IX_PEER_ASNS = (21, 22, 24, 25, 107, 113)
RANDOM_ICMP_PAYLOAD_SIZES = (56, 120, 256, 512)


def _random_acl_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    destination_asn = RANDOM_IX_PEER_ASNS[
        (sequence + seed) % len(RANDOM_IX_PEER_ASNS)
    ]
    probe_size = RANDOM_ICMP_PAYLOAD_SIZES[
        ((sequence + seed) // len(RANDOM_IX_PEER_ASNS))
        % len(RANDOM_ICMP_PAYLOAD_SIZES)
    ]
    return {
        "topology_seed": 20260724,
        "source_asn": RANDOM_SOURCE_ASN,
        "destination_asn": destination_asn,
        "source_router": (
            f"as{RANDOM_SOURCE_ASN}brd-router0-10.{RANDOM_SOURCE_ASN}.0.254"
        ),
        "source_interface": f"ix{RANDOM_SOURCE_IX}",
        "source_ip": f"10.{RANDOM_SOURCE_IX}.0.{RANDOM_SOURCE_ASN}",
        "destination_ip": f"10.{RANDOM_SOURCE_IX}.0.{destination_asn}",
        "probe_size": probe_size,
        "rule_comment": "SEED_RANDOM_COMPLEX_ACL",
    }


def _random_acl_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    router = parameters["source_router"]
    source_interface = parameters["source_interface"]
    source_ip = parameters["source_ip"]
    destination_ip = parameters["destination_ip"]
    probe_size = int(parameters["probe_size"])
    comment = parameters["rule_comment"]
    rule = (
        f"-s {source_ip} -d {destination_ip} -p icmp "
        f"-m length --length {probe_size + 28} -m comment "
        f"--comment {comment} -j REJECT"
    )
    return RenderedScenario(
        inject_command=(
            f"docker exec {router} sh -c '"
            f"iptables -D OUTPUT {rule} 2>/dev/null || true; "
            f"iptables -I OUTPUT 1 {rule}'"
        ),
        verify_command=(
            f"docker exec {router} ping -I {source_interface} "
            f"-s {probe_size} -c 2 -W 2 {destination_ip}"
        ),
        fix_command=(
            f"docker exec {router} sh -c '"
            f"iptables -D OUTPUT {rule} 2>/dev/null || true'"
        ),
        verifier_kind="regex",
        verifier_value=r"(?<!\d)0% packet loss",
    )


def _random_acl_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["source_router"]),),
        "iptables OUTPUT chain",
        (
            f"REJECT {parameters['source_ip']} to "
            f"{parameters['destination_ip']} payload={parameters['probe_size']}"
        ),
        "no matching REJECT rule",
    )


TEMPLATES: Dict[str, FaultTemplate] = {
    item.template_id: item
    for item in (
        FaultTemplate(
            template_id="bird_wrong_asn",
            topology="B00_mini_internet",
            fault_type="wrong_asn",
            difficulty="core",
            description="BIRD local ASN differs from its healthy baseline",
            candidate_factory=_bird_asn_candidate,
            renderer=_bird_asn_render,
            diagnosis_factory=_bird_asn_diagnosis,
        ),
        FaultTemplate(
            template_id="dns_nameserver",
            topology="B00_mini_internet",
            fault_type="dns_failure",
            difficulty="core",
            description="Docker embedded DNS is replaced by an unreachable resolver",
            candidate_factory=_dns_candidate,
            renderer=_dns_render,
            diagnosis_factory=_dns_diagnosis,
        ),
        FaultTemplate(
            template_id="ipv6_connected_route",
            topology="B00_mini_internet",
            fault_type="ipv6_route_missing",
            difficulty="core",
            description="Removing an IPv6 address removes its connected route",
            candidate_factory=_ipv6_candidate,
            renderer=_ipv6_render,
            diagnosis_factory=_ipv6_diagnosis,
        ),
        FaultTemplate(
            template_id="container_stopped",
            topology="B00_mini_internet",
            fault_type="container_not_running",
            difficulty="basic",
            description="A target workload container is unexpectedly stopped",
            candidate_factory=_container_candidate,
            renderer=_container_render,
            diagnosis_factory=_container_diagnosis,
        ),
        FaultTemplate(
            template_id="random_complex_transit_acl",
            topology="RANDOM_COMPLEX_INTERNET",
            fault_type="randomized_transit_acl_shadowing",
            difficulty="advanced",
            description=(
                "A scoped OUTPUT ACL blocks one deterministic IX peer path "
                "in a 100+ container topology"
            ),
            candidate_factory=_random_acl_candidate,
            renderer=_random_acl_render,
            diagnosis_factory=_random_acl_diagnosis,
            default_enabled=False,
        ),
    )
}


def get_template(template_id: str) -> FaultTemplate:
    try:
        return TEMPLATES[template_id]
    except KeyError as exc:
        raise ValueError(f"unknown template_id={template_id}") from exc


def render_scenario(spec: ScenarioSpec) -> RenderedScenario:
    return get_template(spec.template_id).renderer(spec.parameters)


def evaluate_verifier(kind: str, value: str, output: str) -> bool:
    text = output or ""
    if kind == "contains":
        return bool(value) and value in text
    if kind == "equals":
        return text.strip().lower() == value.strip().lower()
    if kind == "regex":
        return re.search(value, text) is not None
    raise ValueError(f"unsupported verifier_kind={kind}")


def validate_template_parameters(spec: ScenarioSpec) -> None:
    """Validate typed parameters independently of command rendering."""
    parameters = spec.parameters
    template_id = spec.template_id
    if template_id == "bird_wrong_asn":
        if parameters.get("container") not in BIRD_TARGETS:
            raise ValueError("bird_wrong_asn target is not in the audited set")
        if int(parameters.get("correct_asn", -1)) != 2:
            raise ValueError("bird_wrong_asn correct ASN must be 2")
        bad = int(parameters.get("bad_asn", -1))
        if not 64512 <= bad <= 65534:
            raise ValueError("bird_wrong_asn bad ASN must be private")
    elif template_id == "dns_nameserver":
        targets = {item[0] for item in HOST_TARGETS}
        peers = {item[1] for item in HOST_TARGETS}
        if parameters.get("container") not in targets:
            raise ValueError("dns target is not in the audited set")
        if parameters.get("peer_container") not in peers:
            raise ValueError("dns peer is not in the audited set")
        if parameters.get("expected_nameserver") != "127.0.0.11":
            raise ValueError("Docker DNS baseline must be 127.0.0.11")
        bad_ip = ipaddress.ip_address(str(parameters.get("bad_nameserver")))
        documentation_ranges = (
            ipaddress.ip_network("192.0.2.0/24"),
            ipaddress.ip_network("198.51.100.0/24"),
            ipaddress.ip_network("203.0.113.0/24"),
        )
        if not any(bad_ip in network for network in documentation_ranges):
            raise ValueError("bad DNS address must use a documentation range")
    elif template_id == "ipv6_connected_route":
        if parameters.get("container") != "as151brd-router0-10.151.0.254":
            raise ValueError("IPv6 target is not in the audited set")
        if parameters.get("interface") != "dummy0":
            raise ValueError("IPv6 template is limited to dummy0")
        if ipaddress.ip_network(str(parameters.get("prefix"))).version != 6:
            raise ValueError("IPv6 prefix is invalid")
        if ipaddress.ip_interface(str(parameters.get("address"))).version != 6:
            raise ValueError("IPv6 address is invalid")
    elif template_id == "container_stopped":
        if parameters.get("container") not in {item[0] for item in HOST_TARGETS}:
            raise ValueError("container stop target is not in the audited set")
    elif template_id == "random_complex_transit_acl":
        if int(parameters.get("topology_seed", -1)) != 20260724:
            raise ValueError("random topology seed differs from the audited build")
        if int(parameters.get("source_asn", -1)) != RANDOM_SOURCE_ASN:
            raise ValueError("random ACL source differs from the audited build")
        destination = int(parameters.get("destination_asn", -1))
        if destination not in RANDOM_IX_PEER_ASNS:
            raise ValueError("random ACL IX peer destination is invalid")
        if parameters.get("rule_comment") != "SEED_RANDOM_COMPLEX_ACL":
            raise ValueError("random ACL rule marker is invalid")
        expected_router = (
            f"as{RANDOM_SOURCE_ASN}brd-router0-10.{RANDOM_SOURCE_ASN}.0.254"
        )
        if parameters.get("source_router") != expected_router:
            raise ValueError("random ACL router is invalid")
        if parameters.get("source_interface") != f"ix{RANDOM_SOURCE_IX}":
            raise ValueError("random ACL source interface is invalid")
        if parameters.get("source_ip") != (
            f"10.{RANDOM_SOURCE_IX}.0.{RANDOM_SOURCE_ASN}"
        ):
            raise ValueError("random ACL source IP is invalid")
        if parameters.get("destination_ip") != (
            f"10.{RANDOM_SOURCE_IX}.0.{destination}"
        ):
            raise ValueError("random ACL destination IP is invalid")
        if int(parameters.get("probe_size", -1)) not in RANDOM_ICMP_PAYLOAD_SIZES:
            raise ValueError("random ACL ICMP probe size is invalid")
    else:
        raise ValueError(f"unknown template_id={template_id}")

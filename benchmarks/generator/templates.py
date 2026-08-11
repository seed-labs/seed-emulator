"""Audited fault templates for deterministic scenario generation."""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

from generator.models import ScenarioSpec


@dataclass(frozen=True)
class RenderedFaultComponent:
    """One mutation with an independent activation check and safe cleanup."""

    component_id: str
    category: str
    target_containers: Tuple[str, ...]
    artifact: str
    faulty_value: str
    expected_value: str
    inject_order: int
    cleanup_order: int
    inject_command: str
    fault_check_command: str
    fault_verifier_kind: str
    fault_verifier_value: str
    cleanup_command: str
    depends_on: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RenderedScenario:
    inject_command: str
    verify_command: str
    fix_command: str
    verifier_kind: str
    verifier_value: str
    components: Tuple[RenderedFaultComponent, ...] = ()


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
    fault_relationship: str = "single"
    causal_chain_factory: Optional[
        Callable[[Mapping[str, Any]], Tuple[str, ...]]
    ] = None
    default_enabled: bool = True

    def candidate(self, sequence: int, seed: int) -> Dict[str, Any]:
        return self.candidate_factory(sequence, seed)

    def diagnosis(
        self, parameters: Mapping[str, Any]
    ) -> Tuple[Tuple[str, ...], str, str, str]:
        return self.diagnosis_factory(parameters)

    def causal_chain(self, parameters: Mapping[str, Any]) -> Tuple[str, ...]:
        if self.causal_chain_factory is None:
            return ()
        return self.causal_chain_factory(parameters)


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


def _compose_components(
    components: Tuple[RenderedFaultComponent, ...],
    *,
    verify_command: str,
    verifier_kind: str,
    verifier_value: str,
) -> RenderedScenario:
    """Build aggregate lifecycle commands from explicitly ordered components."""
    injection = tuple(sorted(components, key=lambda item: item.inject_order))
    cleanup = tuple(sorted(components, key=lambda item: item.cleanup_order))
    return RenderedScenario(
        inject_command=" && ".join(item.inject_command for item in injection),
        verify_command=verify_command,
        fix_command="; ".join(item.cleanup_command for item in cleanup),
        verifier_kind=verifier_kind,
        verifier_value=verifier_value,
        components=components,
    )


COMPLEX_BIRD_CONTAINER = "as2brd-r101-10.101.0.2"
COMPLEX_BAD_OSPF_AREAS = (42, 77, 99)


def _dual_bgp_ospf_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    bad_asn = 64512 + ((sequence + seed) % 1000)
    bad_area = COMPLEX_BAD_OSPF_AREAS[
        ((sequence // 1000) + seed) % len(COMPLEX_BAD_OSPF_AREAS)
    ]
    return {
        "template_revision": 1,
        "container": COMPLEX_BIRD_CONTAINER,
        "correct_asn": 2,
        "bad_asn": bad_asn,
        "correct_area": 0,
        "bad_area": bad_area,
    }


def _dual_bgp_ospf_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = str(parameters["container"])
    correct_asn = int(parameters["correct_asn"])
    bad_asn = int(parameters["bad_asn"])
    correct_area = int(parameters["correct_area"])
    bad_area = int(parameters["bad_area"])
    asn_component = RenderedFaultComponent(
        component_id="bird_wrong_asn",
        category="wrong_asn",
        target_containers=(container,),
        artifact="/etc/bird/bird.conf",
        faulty_value=f"AS {bad_asn}",
        expected_value=f"AS {correct_asn}",
        inject_order=0,
        cleanup_order=1,
        inject_command=(
            f"docker exec {container} sed -i "
            f"'s/as {correct_asn};/as {bad_asn};/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
        fault_check_command=(
            f"docker exec {container} sh -c \""
            f"grep -q 'as {bad_asn};' /etc/bird/bird.conf && "
            "echo GENERATED_ASN_COMPONENT_ACTIVE\""
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_ASN_COMPONENT_ACTIVE",
        cleanup_command=(
            f"docker exec {container} sed -i "
            f"'s/as {bad_asn};/as {correct_asn};/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
    )
    ospf_component = RenderedFaultComponent(
        component_id="ospf_wrong_area",
        category="missing_ospf_adjacency",
        target_containers=(container,),
        artifact="/etc/bird/bird.conf",
        faulty_value=f"area {bad_area}",
        expected_value=f"area {correct_area}",
        inject_order=1,
        cleanup_order=0,
        inject_command=(
            f"docker exec {container} sed -i "
            f"'s/area {correct_area}/area {bad_area}/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
        fault_check_command=(
            f"docker exec {container} sh -c \""
            f"grep -q 'area {bad_area}' /etc/bird/bird.conf && "
            "echo GENERATED_OSPF_COMPONENT_ACTIVE\""
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_OSPF_COMPONENT_ACTIVE",
        cleanup_command=(
            f"docker exec {container} sed -i "
            f"'s/area {bad_area}/area {correct_area}/g' /etc/bird/bird.conf && "
            f"docker exec {container} birdc configure"
        ),
    )
    return _compose_components(
        (asn_component, ospf_component),
        verify_command=(
            f"docker exec {container} sh -c \""
            f"grep -q 'as {correct_asn};' /etc/bird/bird.conf && "
            f"grep -q 'area {correct_area}' /etc/bird/bird.conf && "
            "birdc show protocols | grep -Eq 'BGP[[:space:]].*Established' && "
            "birdc show ospf neighbors | grep -q 'Full/' && "
            "echo GENERATED_DUAL_BGP_OSPF_OK\""
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_DUAL_BGP_OSPF_OK",
    )


def _dual_bgp_ospf_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "/etc/bird/bird.conf (ASN and OSPF area)",
        f"AS {parameters['bad_asn']} and area {parameters['bad_area']}",
        f"AS {parameters['correct_asn']} and area {parameters['correct_area']}",
    )


def _dual_dns_network_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    target, peer, peer_ip = HOST_TARGETS[(sequence + seed) % len(HOST_TARGETS)]
    match = re.match(r"as(\d+)h-", target)
    if match is None:
        raise ValueError("unexpected generated host name")
    asn = int(match.group(1))
    documentation_nets = ("192.0.2", "198.51.100", "203.0.113")
    network = documentation_nets[(sequence + seed) % len(documentation_nets)]
    host_octet = 1 + ((sequence // len(HOST_TARGETS) + seed) % 253)
    return {
        "template_revision": 1,
        "container": target,
        "peer_container": peer,
        "peer_ip": peer_ip,
        "target_ip": f"10.{asn}.0.71",
        "docker_network": f"output_net_{asn}_net0",
        "interface": "net0",
        "bad_nameserver": f"{network}.{host_octet}",
        "expected_nameserver": "127.0.0.11",
    }


def _dual_dns_network_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = str(parameters["container"])
    peer = str(parameters["peer_container"])
    peer_ip = str(parameters["peer_ip"])
    target_ip = str(parameters["target_ip"])
    docker_network = str(parameters["docker_network"])
    interface = str(parameters["interface"])
    bad = str(parameters["bad_nameserver"])
    expected = str(parameters["expected_nameserver"])
    dns_component = RenderedFaultComponent(
        component_id="dns_bad_nameserver",
        category="dns_failure",
        target_containers=(container,),
        artifact="/etc/resolv.conf",
        faulty_value=f"nameserver {bad}",
        expected_value=f"nameserver {expected}",
        inject_order=0,
        cleanup_order=1,
        inject_command=(
            f"docker exec {container} sh -c "
            f"'printf \"nameserver {bad}\\n\" > /etc/resolv.conf'"
        ),
        fault_check_command=(
            f"docker exec {container} sh -c '"
            f"grep -Eq \"^nameserver[[:space:]]+{bad.replace('.', '[.]')}$\" "
            "/etc/resolv.conf && echo GENERATED_DNS_COMPONENT_ACTIVE'"
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_DNS_COMPONENT_ACTIVE",
        cleanup_command=(
            f"docker exec {container} sh -c "
            f"'printf \"nameserver {expected}\\noptions ndots:0\\n\" "
            "> /etc/resolv.conf'"
        ),
    )
    network_component = RenderedFaultComponent(
        component_id="docker_network_disconnect",
        category="wrong_docker_network",
        target_containers=(container,),
        artifact=f"Docker network {docker_network}",
        faulty_value="disconnected",
        expected_value=f"connected with {target_ip}",
        inject_order=1,
        cleanup_order=0,
        inject_command=(
            f"docker network disconnect {docker_network} {container}"
        ),
        fault_check_command=(
            f"docker inspect {container} --format "
            "'{{json .NetworkSettings.Networks}}'"
        ),
        fault_verifier_kind="nonempty_not_contains",
        fault_verifier_value=docker_network,
        cleanup_command=(
            f"docker network disconnect {docker_network} {container} "
            "2>/dev/null || true; "
            f"docker exec {container} ip link del {interface} "
            "2>/dev/null || true; "
            f"docker network connect --ip {target_ip} "
            f"{docker_network} {container}; "
            f"docker exec {container} sh -c '"
            "for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            f"if ip -o -4 addr show dev \"$iface\" | grep -q \"{target_ip}/24\"; then "
            "ip link set \"$iface\" down; "
            f"ip link set \"$iface\" name {interface}; "
            f"ip link set {interface} up; fi; done'"
        ),
    )
    return _compose_components(
        (dns_component, network_component),
        verify_command=(
            f"docker inspect {container} --format "
            "'{{json .NetworkSettings.Networks}}'; "
            f"docker exec {container} sh -c '"
            f"grep -Eq \"^nameserver[[:space:]]+{expected.replace('.', '[.]')}$\" "
            "/etc/resolv.conf && "
            f"getent hosts {peer} | "
            f"grep -q \"^{peer_ip.replace('.', '[.]')}[[:space:]]\" && "
            "echo GENERATED_DUAL_DNS_NETWORK_OK'"
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_DUAL_DNS_NETWORK_OK",
    )


def _dual_dns_network_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        "/etc/resolv.conf and Docker network attachment",
        f"nameserver {parameters['bad_nameserver']} and disconnected",
        f"nameserver {parameters['expected_nameserver']} and connected",
    )


def _cascading_network_bgp_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    return {
        "template_revision": 3,
        "container": COMPLEX_BIRD_CONTAINER,
        "docker_network": "output_net_ix_ix101",
        "interface": "ix101",
        "target_ip": "10.101.0.2",
        "peer_ip": "10.101.0.12",
        "peer_protocol": "c_as12",
        "required_prefix": "10.12.0.0/24",
    }


def _cascading_network_bgp_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    container = str(parameters["container"])
    docker_network = str(parameters["docker_network"])
    interface = str(parameters["interface"])
    target_ip = str(parameters["target_ip"])
    peer_ip = str(parameters["peer_ip"])
    peer_protocol = str(parameters["peer_protocol"])
    required_prefix = str(parameters["required_prefix"])
    component = RenderedFaultComponent(
        component_id="docker_network_disconnect",
        category="wrong_docker_network",
        target_containers=(container,),
        artifact=f"Docker network {docker_network} and interface {interface}",
        faulty_value="attachment disconnected and interface missing",
        expected_value=f"connected with {target_ip} on {interface}",
        inject_order=0,
        cleanup_order=0,
        inject_command=(
            f"docker network disconnect {docker_network} {container} && "
            f"docker exec {container} ip link del {interface}"
        ),
        fault_check_command=(
            f"docker inspect {container} --format "
            f"'{{{{json .NetworkSettings.Networks}}}}' | "
            f"grep -vq '{docker_network}' && "
            f"docker exec {container} sh -c '"
            f"if ! ip link show {interface} >/dev/null 2>&1; then "
            "echo GENERATED_NETWORK_INTERFACE_REMOVED; fi'"
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_NETWORK_INTERFACE_REMOVED",
        cleanup_command=(
            f"docker network disconnect {docker_network} {container} "
            "2>/dev/null || true; "
            f"docker exec {container} ip link del {interface} "
            "2>/dev/null || true; "
            f"docker network connect --ip {target_ip} "
            f"{docker_network} {container}; "
            f"docker exec {container} sh -c '"
            "for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            f"if ip -o -4 addr show dev \"$iface\" | grep -q \"{target_ip}/24\"; then "
            "ip link set \"$iface\" down; "
            f"ip link set \"$iface\" name {interface}; "
            f"ip link set {interface} up; fi; done'; "
            f"docker exec {container} birdc configure"
        ),
    )
    return _compose_components(
        (component,),
        verify_command=(
            f"docker inspect {container} --format "
            "'{{json .NetworkSettings.Networks}}'; "
            f"docker exec {container} sh -c \""
            f"ping -I {interface} -c 2 -W 1 {peer_ip} >/dev/null && "
            f"birdc show protocols {peer_protocol} | "
            f"grep -Eq '^{peer_protocol}[[:space:]]+BGP.*Established' && "
            f"birdc show route protocol {peer_protocol} | "
            f"grep -q '{required_prefix}' && "
            "echo GENERATED_NETWORK_BGP_CASCADE_OK\""
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_NETWORK_BGP_CASCADE_OK",
    )


def _cascading_network_bgp_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["container"]),),
        f"Docker network {parameters['docker_network']}",
        "attachment disconnected and interface missing",
        f"connected with {parameters['target_ip']} on {parameters['interface']}",
    )


def _random_dual_candidate(sequence: int, seed: int) -> Dict[str, Any]:
    parameters = _random_acl_candidate(sequence, seed)
    parameters.update(
        {
            "template_revision": 1,
            "correct_asn": RANDOM_SOURCE_ASN,
            "bad_asn": 64512 + (((sequence // 24) + seed) % 1000),
        }
    )
    return parameters


def _random_dual_render(parameters: Mapping[str, Any]) -> RenderedScenario:
    router = str(parameters["source_router"])
    source_interface = str(parameters["source_interface"])
    source_ip = str(parameters["source_ip"])
    destination_ip = str(parameters["destination_ip"])
    probe_size = int(parameters["probe_size"])
    comment = str(parameters["rule_comment"])
    correct_asn = int(parameters["correct_asn"])
    bad_asn = int(parameters["bad_asn"])
    rule = (
        f"-s {source_ip} -d {destination_ip} -p icmp "
        f"-m length --length {probe_size + 28} -m comment "
        f"--comment {comment} -j REJECT"
    )
    asn_component = RenderedFaultComponent(
        component_id="random_bird_wrong_asn",
        category="wrong_asn",
        target_containers=(router,),
        artifact="/etc/bird/bird.conf",
        faulty_value=f"local {source_ip} as {bad_asn}",
        expected_value=f"local {source_ip} as {correct_asn}",
        inject_order=0,
        cleanup_order=1,
        inject_command=(
            f"docker exec {router} sed -i "
            f"'s/local {source_ip} as {correct_asn};/"
            f"local {source_ip} as {bad_asn};/' /etc/bird/bird.conf && "
            f"docker exec {router} birdc configure"
        ),
        fault_check_command=(
            f"docker exec {router} sh -c \""
            f"grep -q 'local {source_ip} as {bad_asn};' /etc/bird/bird.conf && "
            "echo GENERATED_RANDOM_ASN_ACTIVE\""
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_RANDOM_ASN_ACTIVE",
        cleanup_command=(
            f"docker exec {router} sed -i "
            f"'s/local {source_ip} as {bad_asn};/"
            f"local {source_ip} as {correct_asn};/' /etc/bird/bird.conf && "
            f"docker exec {router} birdc configure"
        ),
    )
    acl_component = RenderedFaultComponent(
        component_id="random_transit_acl",
        category="randomized_transit_acl_shadowing",
        target_containers=(router,),
        artifact="iptables OUTPUT chain",
        faulty_value=(
            f"REJECT {source_ip} to {destination_ip} payload={probe_size}"
        ),
        expected_value="no matching REJECT rule",
        inject_order=1,
        cleanup_order=0,
        inject_command=(
            f"docker exec {router} sh -c '"
            f"iptables -D OUTPUT {rule} 2>/dev/null || true; "
            f"iptables -I OUTPUT 1 {rule}'"
        ),
        fault_check_command=(
            f"docker exec {router} sh -c '"
            f"iptables -C OUTPUT {rule} && echo GENERATED_RANDOM_ACL_ACTIVE'"
        ),
        fault_verifier_kind="contains",
        fault_verifier_value="GENERATED_RANDOM_ACL_ACTIVE",
        cleanup_command=(
            f"docker exec {router} sh -c '"
            f"iptables -D OUTPUT {rule} 2>/dev/null || true'"
        ),
    )
    return _compose_components(
        (asn_component, acl_component),
        verify_command=(
            f"docker exec {router} sh -c \""
            f"grep -q 'local {source_ip} as {correct_asn};' /etc/bird/bird.conf && "
            "birdc show protocols | grep -Eq '^u_as24[[:space:]]+BGP.*Established'\" && "
            f"docker exec {router} ping -I {source_interface} "
            f"-s {probe_size} -c 2 -W 2 {destination_ip} && "
            "echo GENERATED_RANDOM_DUAL_OK"
        ),
        verifier_kind="contains",
        verifier_value="GENERATED_RANDOM_DUAL_OK",
    )


def _random_dual_diagnosis(parameters: Mapping[str, Any]):
    return (
        (str(parameters["source_router"]),),
        "/etc/bird/bird.conf and iptables OUTPUT chain",
        (
            f"AS {parameters['bad_asn']} and REJECT to "
            f"{parameters['destination_ip']}"
        ),
        f"AS {parameters['correct_asn']} and no matching REJECT rule",
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
            template_id="dual_bgp_ospf",
            topology="B00_mini_internet",
            fault_type="multiple_faults",
            difficulty="advanced",
            description=(
                "Independent BGP ASN and OSPF area faults coexist in one router"
            ),
            candidate_factory=_dual_bgp_ospf_candidate,
            renderer=_dual_bgp_ospf_render,
            diagnosis_factory=_dual_bgp_ospf_diagnosis,
            fault_relationship="independent",
        ),
        FaultTemplate(
            template_id="dual_dns_network",
            topology="B00_mini_internet",
            fault_type="multiple_faults",
            difficulty="advanced",
            description=(
                "An invalid resolver and a disconnected Docker network require "
                "ordered recovery"
            ),
            candidate_factory=_dual_dns_network_candidate,
            renderer=_dual_dns_network_render,
            diagnosis_factory=_dual_dns_network_diagnosis,
            fault_relationship="independent",
        ),
        FaultTemplate(
            template_id="cascading_network_bgp",
            topology="B00_mini_internet",
            fault_type="wrong_docker_network",
            difficulty="advanced",
            description=(
                "A Docker network detachment makes its external BGP path unusable"
            ),
            candidate_factory=_cascading_network_bgp_candidate,
            renderer=_cascading_network_bgp_render,
            diagnosis_factory=_cascading_network_bgp_diagnosis,
            fault_relationship="cascading",
            causal_chain_factory=lambda _parameters: (
                "docker_network_disconnect",
                "interface_removed",
                "external_peer_unreachable",
                "external_bgp_path_unusable",
            ),
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
        FaultTemplate(
            template_id="random_complex_dual_bgp_acl",
            topology="RANDOM_COMPLEX_INTERNET",
            fault_type="multiple_faults",
            difficulty="advanced",
            description=(
                "Independent BIRD ASN and scoped ACL faults coexist in a "
                "100+ container topology"
            ),
            candidate_factory=_random_dual_candidate,
            renderer=_random_dual_render,
            diagnosis_factory=_random_dual_diagnosis,
            fault_relationship="independent",
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
    if kind == "nonempty_not_contains":
        return bool(text.strip()) and value not in text
    raise ValueError(f"unsupported verifier_kind={kind}")


def validate_template_parameters(spec: ScenarioSpec) -> None:
    """Validate typed parameters independently of command rendering."""
    parameters = spec.parameters
    template_id = spec.template_id
    if spec.topology.startswith("DECLARATIVE_"):
        from generator.topology.bindings import (
            TEMPLATE_COMPONENTS,
            load_capability_manifest,
            validate_fault_binding,
        )
        from generator.topology.registry import topology_id_from_name

        try:
            component_id = TEMPLATE_COMPONENTS[template_id]
        except KeyError as exc:
            raise ValueError("template has no declarative topology binding") from exc
        manifest = load_capability_manifest(topology_id_from_name(spec.topology))
        validate_fault_binding(manifest, component_id, parameters)
        return
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
    elif template_id == "dual_bgp_ospf":
        if int(parameters.get("template_revision", -1)) != 1:
            raise ValueError("dual BGP/OSPF template revision is invalid")
        if parameters.get("container") != COMPLEX_BIRD_CONTAINER:
            raise ValueError("dual BGP/OSPF target is not audited")
        if int(parameters.get("correct_asn", -1)) != 2:
            raise ValueError("dual BGP/OSPF healthy ASN must be 2")
        if int(parameters.get("correct_area", -1)) != 0:
            raise ValueError("dual BGP/OSPF healthy area must be 0")
        if int(parameters.get("bad_area", -1)) not in COMPLEX_BAD_OSPF_AREAS:
            raise ValueError("dual BGP/OSPF bad area is not audited")
        bad = int(parameters.get("bad_asn", -1))
        if not 64512 <= bad <= 65534:
            raise ValueError("dual BGP/OSPF bad ASN must be private")
    elif template_id == "dual_dns_network":
        if int(parameters.get("template_revision", -1)) != 1:
            raise ValueError("dual DNS/network template revision is invalid")
        target_map = {
            target: (peer, peer_ip)
            for target, peer, peer_ip in HOST_TARGETS
        }
        container = parameters.get("container")
        if container not in target_map:
            raise ValueError("dual DNS/network target is not audited")
        peer, peer_ip = target_map[container]
        match = re.match(r"as(\d+)h-", str(container))
        if match is None:
            raise ValueError("dual DNS/network target name is invalid")
        asn = int(match.group(1))
        if parameters.get("peer_container") != peer:
            raise ValueError("dual DNS/network peer differs from audited topology")
        if parameters.get("peer_ip") != peer_ip:
            raise ValueError("dual DNS/network peer IP is invalid")
        if parameters.get("target_ip") != f"10.{asn}.0.71":
            raise ValueError("dual DNS/network target IP is invalid")
        if parameters.get("docker_network") != f"output_net_{asn}_net0":
            raise ValueError("dual DNS/network attachment is invalid")
        if parameters.get("interface") != "net0":
            raise ValueError("dual DNS/network interface must be net0")
        if parameters.get("expected_nameserver") != "127.0.0.11":
            raise ValueError("dual DNS/network healthy resolver is invalid")
        bad_ip = ipaddress.ip_address(str(parameters.get("bad_nameserver")))
        if not any(
            bad_ip in network
            for network in (
                ipaddress.ip_network("192.0.2.0/24"),
                ipaddress.ip_network("198.51.100.0/24"),
                ipaddress.ip_network("203.0.113.0/24"),
            )
        ):
            raise ValueError("dual DNS/network bad resolver is not documentation IP")
    elif template_id == "cascading_network_bgp":
        expected = {
            "template_revision": 3,
            "container": COMPLEX_BIRD_CONTAINER,
            "docker_network": "output_net_ix_ix101",
            "interface": "ix101",
            "target_ip": "10.101.0.2",
            "peer_ip": "10.101.0.12",
            "peer_protocol": "c_as12",
            "required_prefix": "10.12.0.0/24",
        }
        if any(parameters.get(key) != value for key, value in expected.items()):
            raise ValueError("cascading network/BGP parameters are not audited")
    elif template_id in {
        "random_complex_transit_acl",
        "random_complex_dual_bgp_acl",
    }:
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
        if template_id == "random_complex_dual_bgp_acl":
            if int(parameters.get("template_revision", -1)) != 1:
                raise ValueError("random dual template revision is invalid")
            if int(parameters.get("correct_asn", -1)) != RANDOM_SOURCE_ASN:
                raise ValueError("random dual healthy ASN is invalid")
            bad = int(parameters.get("bad_asn", -1))
            if not 64512 <= bad <= 65534:
                raise ValueError("random dual bad ASN must be private")
    else:
        raise ValueError(f"unknown template_id={template_id}")

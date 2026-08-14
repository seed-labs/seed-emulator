"""FaultDriver interface and audited Docker network fault plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
import base64
from pathlib import PurePosixPath
import re
import shlex
import time
from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.faults.models import FaultAction, FaultSpec
from generator.software import (
    EXECUTABLE_ROOTS,
    MANAGED_FILE_ROOTS,
    PROTECTED_PATHS,
)


class FaultDriver(ABC):
    """A versioned backend plugin that compiles semantics into safe actions."""

    fault_type: str
    version = "1.0"

    @abstractmethod
    def plan(
        self,
        spec: FaultSpec,
        targets: Sequence[Mapping[str, Any]],
    ) -> FaultAction:
        raise NotImplementedError

    def discover(
        self, spec: FaultSpec, capabilities: Mapping[str, Any]
    ) -> Tuple[Mapping[str, Any], ...]:
        """Advertise compatible assets; the compiler applies selectors."""
        return tuple(capabilities.get("assets") or ())

    def precheck(self, action: FaultAction) -> None:
        if not action.targets or not action.inject_command or not action.cleanup_command:
            raise ValueError(f"driver {self.fault_type} produced an incomplete action")

    @staticmethod
    def _run_with_retry(runner, command: str, timeout: int):
        """Retry Docker runtime launch failures, not fault command failures."""
        result = (125, "fault command was not executed")
        transient_markers = (
            "transient scope not created",
            "context deadline exceeded",
            "cannot connect to the docker daemon",
            "command execution timeout",
        )
        for attempt in range(3):
            result = runner(command, timeout)
            returncode, output = result
            if returncode == 0 or not any(
                marker in output.lower() for marker in transient_markers
            ):
                return result
            if attempt < 2:
                time.sleep(2)
        return result

    def inject(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.inject_command, 120)

    def snapshot(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.snapshot_command, 30)

    def verify_active(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.active_check_command, 30)

    def observe(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.active_check_command, 30)

    def recover(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.cleanup_command, 120)

    def verify_recovered(self, action: FaultAction, runner):
        return self._run_with_retry(runner, action.active_check_command, 30)


def _one_target(targets: Sequence[Mapping[str, Any]]) -> str:
    if len(targets) != 1 or not targets[0].get("container"):
        raise ValueError("fault driver requires exactly one resolved container")
    return str(targets[0]["container"])


def _software_profile(
    spec: FaultSpec, targets: Sequence[Mapping[str, Any]]
) -> Tuple[str, Mapping[str, Any]]:
    container = _one_target(targets)
    if spec.parameters:
        raise ValueError("software profile faults do not accept runtime command parameters")
    software_id = str(spec.selector.get("software", ""))
    profile_id = str(spec.selector.get("fault_profile", ""))
    matches = []
    for software in targets[0].get("software") or ():
        if software.get("software_id") != software_id:
            continue
        for profile in software.get("fault_profiles") or ():
            if (
                profile.get("profile_id") == profile_id
                and profile.get("fault_type") == spec.fault_type
            ):
                matches.append(profile)
    if len(matches) != 1:
        raise ValueError("software fault profile is absent or ambiguous on selected asset")
    parameters = matches[0].get("parameters")
    if not isinstance(parameters, Mapping):
        raise ValueError("software fault profile parameters are invalid")
    return container, parameters


def _assets_with_profile(
    spec: FaultSpec, capabilities: Mapping[str, Any]
) -> Tuple[Mapping[str, Any], ...]:
    software_id = str(spec.selector.get("software", ""))
    profile_id = str(spec.selector.get("fault_profile", ""))
    if not software_id or not profile_id:
        raise ValueError("software fault selector requires software and fault_profile")
    selected = []
    for asset in capabilities.get("assets") or ():
        for software in asset.get("software") or ():
            if software.get("software_id") != software_id:
                continue
            if any(
                item.get("profile_id") == profile_id
                and item.get("fault_type") == spec.fault_type
                for item in software.get("fault_profiles") or ()
            ):
                selected.append(asset)
                break
    return tuple(selected)


def _docker_exec(container: str, *argv: str) -> str:
    return "docker exec " + shlex.quote(container) + " " + shlex.join(argv)


class SoftwareConfigReplaceDriver(FaultDriver):
    """Mutate one exact managed-file value and restore it idempotently."""

    fault_type = "software.config.replace"

    def discover(self, spec, capabilities):
        return _assets_with_profile(spec, capabilities)

    def plan(self, spec, targets):
        container, p = _software_profile(spec, targets)
        if set(p) != {"path", "healthy_value", "faulty_value"}:
            raise ValueError("software.config.replace profile parameters are invalid")
        path = str(p["path"])
        if (
            not PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
            or path in PROTECTED_PATHS or not path.startswith(MANAGED_FILE_ROOTS)
        ):
            raise ValueError("software.config.replace path is outside managed roots")
        healthy = str(p["healthy_value"])
        faulty = str(p["faulty_value"])
        if not healthy or not faulty or healthy == faulty:
            raise ValueError("software.config.replace values are invalid")
        healthy64 = base64.b64encode(healthy.encode("utf-8")).decode("ascii")
        faulty64 = base64.b64encode(faulty.encode("utf-8")).decode("ascii")
        inject_program = (
            "import base64,pathlib,sys;p=pathlib.Path(sys.argv[1]);"
            "a=base64.b64decode(sys.argv[2]);b=base64.b64decode(sys.argv[3]);"
            "d=p.read_bytes();assert d.count(a)==1 and d.count(b)==0;"
            "p.write_bytes(d.replace(a,b,1))"
        )
        active_program = (
            "import base64,pathlib,sys;p=pathlib.Path(sys.argv[1]);"
            "a=base64.b64decode(sys.argv[2]);b=base64.b64decode(sys.argv[3]);"
            "d=p.read_bytes();assert d.count(a)==0 and d.count(b)==1;"
            "print('GENERATED_SOFTWARE_CONFIG_ACTIVE')"
        )
        snapshot_program = (
            "import hashlib,pathlib,sys;"
            "print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())"
        )
        cleanup_program = (
            "import base64,pathlib,sys;p=pathlib.Path(sys.argv[1]);"
            "a=base64.b64decode(sys.argv[2]);b=base64.b64decode(sys.argv[3]);"
            "d=p.read_bytes();ok=d.count(a)==1 and d.count(b)==0;"
            "bad=d.count(a)==0 and d.count(b)==1;assert ok or bad;"
            "p.write_bytes(d.replace(b,a,1) if bad else d)"
        )
        profile = str(spec.selector["fault_profile"])
        software = str(spec.selector["software"])
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="software_configuration_error", targets=(container,),
            artifact=path, faulty_value=faulty, expected_value=healthy,
            resource_locks=(f"container:{container}:file:{path}",),
            inject_command=_docker_exec(
                container, "python3", "-c", inject_program, path, healthy64, faulty64
            ),
            active_check_command=_docker_exec(
                container, "python3", "-c", active_program, path, healthy64, faulty64
            ),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_SOFTWARE_CONFIG_ACTIVE",
            snapshot_command=_docker_exec(
                container, "python3", "-c", snapshot_program, path
            ),
            cleanup_command=_docker_exec(
                container, "python3", "-c", cleanup_program, path, healthy64, faulty64
            ),
        )


class SoftwareExecutableDisabledDriver(FaultDriver):
    """Disable one declared executable without stopping the container."""

    fault_type = "software.executable.disabled"

    def discover(self, spec, capabilities):
        return _assets_with_profile(spec, capabilities)

    def plan(self, spec, targets):
        container, p = _software_profile(spec, targets)
        if set(p) != {"path", "expected_mode"}:
            raise ValueError("software.executable.disabled profile parameters are invalid")
        path, mode = str(p["path"]), str(p["expected_mode"])
        candidate = PurePosixPath(path)
        if (
            not candidate.is_absolute() or ".." in candidate.parts
            or path in PROTECTED_PATHS or not path.startswith(EXECUTABLE_ROOTS)
            or not re.fullmatch(r"[0-7]{3,4}", mode)
            or mode.endswith(("0", "2", "4", "6"))
        ):
            raise ValueError("software.executable.disabled path/mode is unsafe")
        quoted = shlex.quote(path)
        inject = f'test "$(stat -c %a {quoted})" = {mode.lstrip("0")} && chmod 000 {quoted}'
        active = f"test ! -x {quoted} && echo GENERATED_SOFTWARE_EXECUTABLE_DISABLED"
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="software_executable_unavailable", targets=(container,),
            artifact=path, faulty_value="mode 000", expected_value=f"mode {mode}",
            resource_locks=(f"container:{container}:executable:{path}",),
            inject_command=_docker_exec(container, "sh", "-c", inject),
            active_check_command=_docker_exec(container, "sh", "-c", active),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_SOFTWARE_EXECUTABLE_DISABLED",
            snapshot_command=_docker_exec(container, "stat", "-c", "%a", path),
            cleanup_command=_docker_exec(container, "chmod", mode, path),
        )


class ContainerStoppedDriver(FaultDriver):
    fault_type = "container.stopped"

    def plan(self, spec, targets):
        container = _one_target(targets)
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="container_not_running", targets=(container,),
            artifact="Docker container state", faulty_value="stopped",
            expected_value="running", resource_locks=(f"container:{container}:exclusive",),
            inject_command=f"docker stop {container}",
            active_check_command=(
                "docker inspect --format '{{.State.Running}}' " + container
            ),
            active_verifier_kind="equals", active_verifier_value="false",
            snapshot_command=(
                "docker inspect --format '{{.State.Running}}' " + container
            ),
            cleanup_command=f"docker start {container}",
        )


class DnsNameserverDriver(FaultDriver):
    fault_type = "dns.nameserver"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        bad = str(p["bad_nameserver"])
        expected = str(p.get("expected_nameserver", "127.0.0.11"))
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="dns_failure", targets=(container,), artifact="/etc/resolv.conf",
            faulty_value=f"nameserver {bad}", expected_value=f"nameserver {expected}",
            resource_locks=(f"container:{container}:file:/etc/resolv.conf",),
            inject_command=(f"docker exec {container} sh -c "
                            f"'printf \"nameserver {bad}\\n\" > /etc/resolv.conf'"),
            active_check_command=(f"docker exec {container} sh -c '"
                                  f"grep -Eq \"^nameserver[[:space:]]+{bad.replace('.', '[.]')}$\" "
                                  "/etc/resolv.conf && echo GENERATED_DNS_COMPONENT_ACTIVE'"),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_DNS_COMPONENT_ACTIVE",
            snapshot_command=f"docker exec {container} cat /etc/resolv.conf",
            cleanup_command=(f"docker exec {container} sh -c "
                             f"'printf \"nameserver {expected}\\noptions ndots:0\\n\" "
                             "> /etc/resolv.conf'"),
        )


class BirdWrongAsnDriver(FaultDriver):
    fault_type = "routing.bird.wrong_asn"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        correct, bad = int(p["correct_asn"]), int(p["bad_asn"])
        source = str(p.get("source_ip", ""))
        if source:
            healthy = f"local {source} as {correct};"
            broken = f"local {source} as {bad};"
        else:
            healthy, broken = f"as {correct};", f"as {bad};"
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="wrong_asn", targets=(container,), artifact="/etc/bird/bird.conf",
            faulty_value=(broken.removesuffix(";")),
            expected_value=(healthy.removesuffix(";")),
            resource_locks=(f"container:{container}:file:/etc/bird/bird.conf:asn",),
            inject_command=(f"docker exec {container} sed -i "
                            f"'s/{healthy}/{broken}/g' /etc/bird/bird.conf && "
                            f"docker exec {container} birdc configure"),
            active_check_command=(f"docker exec {container} sh -c \""
                                  f"grep -q '{broken}' /etc/bird/bird.conf && "
                                  "echo GENERATED_BIRD_ASN_ACTIVE\""),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_BIRD_ASN_ACTIVE",
            snapshot_command=f"docker exec {container} sha256sum /etc/bird/bird.conf",
            cleanup_command=(f"docker exec {container} sed -i "
                             f"'s/{broken}/{healthy}/g' /etc/bird/bird.conf && "
                             f"docker exec {container} birdc configure"),
        )


class ScopedAclDriver(FaultDriver):
    fault_type = "network.acl.scoped"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        source_ip, destination_ip = str(p["source_ip"]), str(p["destination_ip"])
        size = int(p["probe_size"])
        comment = str(p.get("rule_comment", "SEED_RANDOM_COMPLEX_ACL"))
        rule = (f"-s {source_ip} -d {destination_ip} -p icmp "
                f"-m length --length {size + 28} -m comment "
                f"--comment {comment} -j REJECT")
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="randomized_transit_acl_shadowing", targets=(container,),
            artifact="iptables OUTPUT chain",
            faulty_value=f"REJECT {source_ip} to {destination_ip} payload={size}",
            expected_value="no matching REJECT rule",
            resource_locks=(f"container:{container}:iptables:OUTPUT:{comment}",),
            inject_command=(f"docker exec {container} sh -c '"
                            f"iptables -D OUTPUT {rule} 2>/dev/null || true; "
                            f"iptables -I OUTPUT 1 {rule}'"),
            active_check_command=(f"docker exec {container} sh -c '"
                                  f"iptables -C OUTPUT {rule} && "
                                  "echo GENERATED_SCOPED_ACL_ACTIVE'"),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_SCOPED_ACL_ACTIVE",
            snapshot_command=f"docker exec {container} iptables-save",
            cleanup_command=(f"docker exec {container} sh -c '"
                             f"iptables -D OUTPUT {rule} 2>/dev/null || true'"),
        )


class NetemDriver(FaultDriver):
    fault_type = "network.netem"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        interface = str(p["interface"])
        terms = []
        labels = []
        delay = int(p.get("delay_ms", 0))
        jitter = int(p.get("jitter_ms", 0))
        loss = float(p.get("loss_percent", 0))
        rate = int(p.get("rate_kbit", 0))
        if delay:
            terms += ["delay", f"{delay}ms"]
            labels.append(f"delay={delay}ms")
            if jitter:
                terms.append(f"{jitter}ms")
                labels.append(f"jitter={jitter}ms")
        elif jitter:
            raise ValueError("netem jitter_ms requires delay_ms")
        if loss:
            terms += ["loss", f"{loss:g}%"]
            labels.append(f"loss={loss:g}%")
        if rate:
            terms += ["rate", f"{rate}kbit"]
            labels.append(f"rate={rate}kbit")
        if not terms:
            raise ValueError("netem requires delay, loss, rate, or jitter")
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="network_impairment", targets=(container,),
            artifact=f"tc qdisc {interface}", faulty_value=", ".join(labels),
            expected_value="no netem qdisc",
            resource_locks=(f"container:{container}:qdisc:{interface}",),
            inject_command=(f"docker exec {container} tc qdisc replace dev "
                            f"{interface} root netem {' '.join(terms)}"),
            active_check_command=(f"docker exec {container} tc qdisc show dev {interface}"),
            active_verifier_kind="contains", active_verifier_value="netem",
            snapshot_command=f"docker exec {container} tc qdisc show dev {interface}",
            cleanup_command=(f"docker exec {container} sh -c 'tc qdisc del dev "
                             f"{interface} root 2>/dev/null || true'"),
        )


class Ipv6ConnectedRouteRemovedDriver(FaultDriver):
    """Remove one declared IPv6 address and its kernel connected route."""

    fault_type = "network.ipv6.connected_route_removed"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        address, prefix = str(p["address"]), str(p["prefix"])
        interface = str(p["interface"])
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", interface):
            raise ValueError("invalid IPv6 interface")
        marker = "GENERATED_IPV6_CONNECTED_ROUTE_REMOVED"
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="ipv6_route_missing", targets=(container,),
            artifact=f"IPv6 address {address} on {interface}",
            faulty_value=f"missing {prefix}",
            expected_value=f"{prefix} dev {interface}",
            resource_locks=(f"container:{container}:ipv6:{interface}:{prefix}",),
            inject_command=(
                f"docker exec {container} ip -6 addr del {address} dev {interface}"
            ),
            active_check_command=(
                f"docker exec {container} sh -c '"
                f"if ! ip -6 addr show dev {interface} | grep -Fq {shlex.quote(address.split('/')[0])} "
                f"&& ! ip -6 route show {prefix} | grep -Fq {shlex.quote(prefix)}; "
                f"then echo {marker}; fi'"
            ),
            active_verifier_kind="contains", active_verifier_value=marker,
            snapshot_command=(
                f"docker exec {container} sh -c 'ip -6 addr show dev {interface}; "
                f"ip -6 route show {prefix}'"
            ),
            cleanup_command=(
                f"docker exec {container} sh -c '"
                f"ip -6 route del {prefix} dev {interface} 2>/dev/null || true; "
                f"ip -6 addr del {address} dev {interface} 2>/dev/null || true; "
                f"ip -6 addr add {address} dev {interface}'"
            ),
        )


class BirdOspfWrongAreaDriver(FaultDriver):
    """Replace one audited BIRD OSPF area and restore the healthy value."""

    fault_type = "routing.bird.ospf_wrong_area"

    def plan(self, spec, targets):
        container = _one_target(targets)
        correct, bad = int(spec.parameters["correct_area"]), int(spec.parameters["bad_area"])
        if correct == bad:
            raise ValueError("OSPF healthy and faulty areas must differ")
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="missing_ospf_adjacency", targets=(container,),
            artifact="/etc/bird/bird.conf", faulty_value=f"area {bad}",
            expected_value=f"area {correct}",
            resource_locks=(f"container:{container}:file:/etc/bird/bird.conf:ospf-area",),
            inject_command=(
                f"docker exec {container} sed -i 's/area {correct}/area {bad}/g' "
                f"/etc/bird/bird.conf && docker exec {container} birdc configure"
            ),
            active_check_command=(
                f"docker exec {container} sh -c \"grep -q 'area {bad}' "
                "/etc/bird/bird.conf && echo GENERATED_OSPF_AREA_ACTIVE\""
            ),
            active_verifier_kind="contains",
            active_verifier_value="GENERATED_OSPF_AREA_ACTIVE",
            snapshot_command=f"docker exec {container} sha256sum /etc/bird/bird.conf",
            cleanup_command=(
                f"docker exec {container} sed -i 's/area {bad}/area {correct}/g' "
                f"/etc/bird/bird.conf && docker exec {container} birdc configure"
            ),
        )


class DockerNetworkDisconnectedDriver(FaultDriver):
    """Disconnect one declared Compose network and deterministically reconnect it."""

    fault_type = "docker.network.disconnected"

    def plan(self, spec, targets):
        container = _one_target(targets)
        p = spec.parameters
        network = str(p["docker_network"])
        interface = str(p["interface"])
        target_ip = str(p["target_ip"])
        remove_interface = bool(p.get("remove_interface", False))
        for value in (network, interface, target_ip):
            if not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
                raise ValueError("invalid Docker network fault parameter")
        inject = f"docker network disconnect {network} {container}"
        if remove_interface:
            inject += (
                f"; docker exec {container} ip link del {interface} 2>/dev/null || true"
            )
        marker = "GENERATED_DOCKER_NETWORK_DISCONNECTED"
        active = (
            f"docker inspect {container} --format '"
            "{{json .NetworkSettings.Networks}}'"
        )
        # Make the verifier independent from grep exit-code details.
        active += f" | grep -vq {shlex.quote(network)} && echo {marker}"
        cleanup = (
            f"docker network disconnect {network} {container} 2>/dev/null || true; "
            f"docker exec {container} ip link del {interface} 2>/dev/null || true; "
            f"docker network connect --ip {target_ip} {network} {container}; "
            f"docker exec {container} sh -c 'for path in /sys/class/net/eth*; do "
            "iface=${path##*/}; "
            f"if ip -o -4 addr show dev \"$iface\" | grep -q \"{target_ip}/24\"; then "
            "ip link set \"$iface\" down; "
            f"ip link set \"$iface\" name {interface}; ip link set {interface} up; fi; done'"
        )
        if bool(p.get("bird_reconfigure", False)):
            cleanup += f"; docker exec {container} birdc configure"
        return FaultAction(
            action_id=spec.fault_id, driver=self.fault_type,
            category="wrong_docker_network", targets=(container,),
            artifact=f"Docker network {network} and interface {interface}",
            faulty_value="attachment disconnected and interface missing",
            expected_value=f"connected with {target_ip} on {interface}",
            resource_locks=(f"container:{container}:docker-network:{network}",),
            inject_command=inject, active_check_command=active,
            active_verifier_kind="contains", active_verifier_value=marker,
            snapshot_command=(
                f"docker inspect {container} --format '"
                "{{json .NetworkSettings.Networks}}'"
            ),
            cleanup_command=cleanup,
        )


DRIVERS: Dict[str, FaultDriver] = {}


def register_driver(driver: FaultDriver) -> None:
    """Register an extension without permitting silent built-in overrides."""
    if not isinstance(driver, FaultDriver) or not driver.fault_type:
        raise TypeError("fault driver plugin must implement FaultDriver")
    if driver.fault_type in DRIVERS:
        raise ValueError(f"fault driver already registered: {driver.fault_type}")
    DRIVERS[driver.fault_type] = driver


for _driver in (
    ContainerStoppedDriver(), DnsNameserverDriver(), BirdWrongAsnDriver(),
    ScopedAclDriver(), NetemDriver(), SoftwareConfigReplaceDriver(),
    SoftwareExecutableDisabledDriver(), Ipv6ConnectedRouteRemovedDriver(),
    BirdOspfWrongAreaDriver(), DockerNetworkDisconnectedDriver(),
):
    register_driver(_driver)


def get_driver(fault_type: str) -> FaultDriver:
    try:
        return DRIVERS[fault_type]
    except KeyError as exc:
        raise ValueError(f"unsupported fault_type={fault_type}") from exc

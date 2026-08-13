"""FaultDriver interface and audited Docker network fault plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Mapping, Sequence, Tuple

from generator.faults.models import FaultAction, FaultSpec


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

    def inject(self, action: FaultAction, runner):
        return runner(action.inject_command, 120)

    def verify_active(self, action: FaultAction, runner):
        return runner(action.active_check_command, 30)

    def observe(self, action: FaultAction, runner):
        return runner(action.active_check_command, 30)

    def recover(self, action: FaultAction, runner):
        return runner(action.cleanup_command, 120)

    def verify_recovered(self, action: FaultAction, runner):
        return runner(action.active_check_command, 30)


def _one_target(targets: Sequence[Mapping[str, Any]]) -> str:
    if len(targets) != 1 or not targets[0].get("container"):
        raise ValueError("fault driver requires exactly one resolved container")
    return str(targets[0]["container"])


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


DRIVERS: Dict[str, FaultDriver] = {
    item.fault_type: item for item in (
        ContainerStoppedDriver(), DnsNameserverDriver(), BirdWrongAsnDriver(),
        ScopedAclDriver(), NetemDriver(),
    )
}


def get_driver(fault_type: str) -> FaultDriver:
    try:
        return DRIVERS[fault_type]
    except KeyError as exc:
        raise ValueError(f"unsupported fault_type={fault_type}") from exc

"""No-AI bundle lifecycle with independent probes and durable evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import time
from typing import Any, Dict, Mapping, Protocol, Sequence, Tuple
import uuid

from generator.bundle.compiler import resolve_assets
from generator.bundle.models import CompiledBenchmarkBundle
from generator.bundle.specs import ServiceSpec, TestSpec, WorkloadSpec
from generator.faults.journal import FaultExecutor
from generator.faults.models import CompiledFaultPlan
from generator.software import EXECUTABLE_ROOTS


ProbeResult = Tuple[int, str, Dict[str, float]]


class LifecycleRunner(Protocol):
    def ensure_service(self, service: ServiceSpec, capabilities: Mapping[str, Any]) -> ProbeResult: ...
    def run_workload(self, workload: WorkloadSpec, capabilities: Mapping[str, Any]) -> ProbeResult: ...
    def run_test(self, test: TestSpec, capabilities: Mapping[str, Any]) -> ProbeResult: ...


def evaluate_assertion(
    assertion: Mapping[str, Any], code: int, output: str,
    metrics: Mapping[str, float],
) -> bool:
    kind, expected = str(assertion["kind"]), assertion["value"]
    if kind == "exit_code":
        return code == int(expected)
    if kind == "exit_code_not":
        return code != int(expected)
    if kind == "equals":
        return output.strip() == str(expected)
    if kind == "contains":
        return str(expected) in output
    if kind == "not_contains":
        return str(expected) not in output
    if kind == "regex":
        return re.search(str(expected), output) is not None
    if kind == "range":
        spec = dict(expected)
        value = float(metrics[str(spec["metric"])])
        return float(spec.get("min", float("-inf"))) <= value <= float(spec.get("max", float("inf")))
    if kind == "ratio_at_least":
        spec = dict(expected)
        return float(metrics[str(spec["metric"])]) >= float(spec["value"])
    raise ValueError(f"unsupported assertion kind={kind}")


class DockerLifecycleRunner:
    """Shell-free Docker probe runner with a small fixed driver vocabulary."""

    def _run(self, argv: Sequence[str], timeout: float) -> ProbeResult:
        try:
            result = subprocess.run(
                list(argv), capture_output=True, text=True, timeout=timeout,
            )
            return result.returncode, result.stdout + result.stderr, {}
        except subprocess.TimeoutExpired:
            return 124, "command timed out", {}

    @staticmethod
    def _container(selector, capabilities):
        return str(resolve_assets(selector, capabilities)[0]["container"])

    @staticmethod
    def _argv(value: object) -> Tuple[str, ...]:
        if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item for item in value
        ):
            raise ValueError("container command must be a non-empty argv list")
        return tuple(value)

    def ensure_service(self, service, capabilities):
        container = self._container(service.selector, capabilities)
        health = service.parameters.get("health_argv")
        if health:
            code, output, metrics = self._run(
                ("docker", "exec", container, *self._argv(health)), 30
            )
            if code == 0:
                return code, output, metrics
        start = service.parameters.get("start_argv")
        if start:
            code, output, metrics = self._run(
                ("docker", "exec", container, *self._argv(start)), 120
            )
            if code != 0:
                return code, output, metrics
        if health:
            return self._run(("docker", "exec", container, *self._argv(health)), 30)
        return 0, "service declaration accepted", {}

    def run_workload(self, workload, capabilities):
        source = self._container(workload.source, capabilities)
        params = workload.parameters
        if workload.driver == "workload.http":
            argv = ("curl", "-fsS", "--max-time", "10", str(params["url"]))
        elif workload.driver == "workload.dns":
            argv = ("dig", "+short", str(params["name"]), "@" + str(params["server"]))
        elif workload.driver == "workload.tcp":
            argv = ("nc", "-zvw5", str(params["host"]), str(int(params["port"])))
        elif workload.driver == "workload.udp":
            argv = ("nc", "-zvuw5", str(params["host"]), str(int(params["port"])))
        elif workload.driver == "workload.icmp":
            argv = ("ping", "-c", "1", "-W", "5", str(params["host"]))
        else:
            raise ValueError(f"unsupported workload runner={workload.driver}")
        return self._run(("docker", "exec", source, *argv), workload.duration_seconds + 15)

    def run_test(self, test, capabilities):
        container = self._container(test.selector, capabilities)
        params = test.parameters
        if test.driver == "probe.container":
            return self._run(("docker", "inspect", "--format", "{{.State.Running}}", container), test.timeout_seconds)
        if test.driver == "probe.http":
            argv = ("curl", "-fsS", "--max-time", str(int(test.timeout_seconds)), str(params["url"]))
        elif test.driver == "probe.dns":
            argv = ("dig", "+short", str(params["name"]), "@" + str(params["server"]))
        elif test.driver == "probe.hostname":
            name = str(params["name"])
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,253}", name):
                raise ValueError("invalid hostname probe target")
            ipaddress.ip_address(str(params["expected_ip"]))
            argv = ("getent", "hosts", name)
        elif test.driver == "probe.icmp":
            host = str(params["host"])
            source = str(params.get("source_ip", ""))
            ipaddress.ip_address(host)
            if source:
                ipaddress.ip_address(source)
            count, size = int(params.get("count", 1)), int(params.get("size", 56))
            if not 1 <= count <= 10 or not 0 <= size <= 4096:
                raise ValueError("invalid ICMP probe budget")
            values = ["ping", "-c", str(count), "-W", "2", "-s", str(size)]
            if source:
                values += ["-I", source]
            values.append(host)
            argv = tuple(values)
        elif test.driver == "probe.ipv6_route":
            prefix = str(params["prefix"])
            network = ipaddress.ip_network(prefix)
            if network.version != 6:
                raise ValueError("IPv6 route probe requires an IPv6 prefix")
            argv = ("ip", "-6", "route", "show", prefix)
        elif test.driver == "probe.executable":
            path = str(params["path"])
            candidate = PurePosixPath(path)
            if (
                not candidate.is_absolute() or ".." in candidate.parts
                or not path.startswith(EXECUTABLE_ROOTS)
            ):
                raise ValueError("unsafe executable probe path")
            argv = ("test", "-x", path)
        elif test.driver == "probe.docker_network":
            network = str(params["network"])
            if not re.fullmatch(r"decl_[A-Za-z0-9_.-]{3,190}", network):
                raise ValueError("Docker network probe is outside a declarative project")
            return self._run(
                ("docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", container),
                test.timeout_seconds,
            )
        elif test.driver == "probe.docker_network_path":
            network = str(params["network"])
            interface = str(params["interface"])
            target_ip = str(params["target_ip"])
            peer_ip = str(params["peer_ip"])
            if not re.fullmatch(r"[a-z0-9][A-Za-z0-9_.-]{2,190}", network):
                raise ValueError("invalid scoped Docker network identity")
            if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,32}", interface):
                raise ValueError("invalid Docker network interface")
            ipaddress.ip_address(target_ip); ipaddress.ip_address(peer_ip)
            allowed = {
                (
                    str(item.get("container")), str(item.get("docker_network")),
                    str(item.get("interface")), str(item.get("target_ip")),
                    str(item.get("peer_ip")),
                )
                for item in (
                    (capabilities.get("fault_component_bindings") or {}).get(
                        "docker_network_disconnected"
                    ) or ()
                )
            }
            if (container, network, interface, target_ip, peer_ip) not in allowed:
                raise ValueError("Docker path probe is outside runtime capabilities")
            code, attached, _metrics = self._run((
                "docker", "inspect", "--format",
                "{{json .NetworkSettings.Networks}}", container,
            ), test.timeout_seconds)
            if code != 0 or network not in attached:
                return 1, f"attachment_missing network={network}\n{attached}", {}
            code, address, _metrics = self._run((
                "docker", "exec", container, "ip", "-o", "-4", "addr",
                "show", "dev", interface,
            ), test.timeout_seconds)
            if code != 0 or target_ip not in address:
                return 1, f"interface_unhealthy interface={interface}\n{address}", {}
            code, ping, metrics = self._run((
                "docker", "exec", container, "ping", "-c", "1", "-W", "2",
                peer_ip,
            ), test.timeout_seconds)
            return code, (
                f"attachment_ok network={network}\n"
                f"interface_ok interface={interface} address={target_ip}\n{ping}"
            ), metrics
        elif test.driver == "probe.tcp":
            argv = ("nc", "-zvw5", str(params["host"]), str(int(params["port"])))
        elif test.driver == "probe.file":
            path = str(params["path"])
            candidate = PurePosixPath(path)
            if not candidate.is_absolute() or ".." in candidate.parts:
                raise ValueError("unsafe probe file path")
            argv = ("cat", path)
        elif test.driver == "probe.routing":
            argv = ("birdc", "show", "protocols")
        elif test.driver == "probe.metric":
            metric = str(params.get("metric", ""))
            if metric == "netem":
                argv = ("tc", "-s", "qdisc", "show")
            elif metric == "firewall":
                argv = ("iptables", "-S")
            else:
                raise ValueError("unsupported fixed metric probe")
        else:
            raise ValueError(f"unsupported probe runner={test.driver}")
        return self._run(("docker", "exec", container, *argv), test.timeout_seconds)


@dataclass
class BundleLifecycleExecutor:
    journal_root: Path
    runner: LifecycleRunner
    fault_runner: Any = None

    def _write(self, path: Path, value: Mapping[str, Any]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
            os.replace(temporary, path)
        except Exception:
            try: os.unlink(temporary)
            except FileNotFoundError: pass
            raise
        return path

    def _tests(self, tests, phase, capabilities):
        results = []
        for test in (item for item in tests if item.phase == phase):
            passed_samples, evidence = 0, []
            attempts = test.samples + test.retries
            for _index in range(attempts):
                code, output, metrics = self.runner.run_test(test, capabilities)
                passed = evaluate_assertion(test.assertion, code, output, metrics)
                evidence.append({
                    "exit_code": code, "output": output[:2000],
                    "metrics": metrics, "passed": passed,
                })
                if passed:
                    passed_samples += 1
                if passed_samples >= test.samples:
                    break
            results.append({
                "test_id": test.test_id, "phase": phase,
                "expectation_id": test.expectation_id,
                "passed": passed_samples >= test.samples,
                "evidence": evidence,
            })
        return results

    def _wait_for_recovery(
        self, tests, capabilities, *, timeout_seconds: float,
        poll_seconds: float = 2.0, stable_samples: int = 2,
    ):
        """Wait for stable semantic recovery instead of a transient success."""
        if not 0 < timeout_seconds <= 600:
            raise ValueError("recovery convergence timeout is outside 0-600 seconds")
        if not 0 < poll_seconds <= 30 or not 1 <= stable_samples <= 10:
            raise ValueError("invalid recovery convergence policy")
        started = time.monotonic(); streak = 0; attempts = []
        final = []
        while True:
            final = self._tests(tests, "recovery", capabilities)
            passed = bool(final) and all(item["passed"] for item in final)
            streak = streak + 1 if passed else 0
            attempts.append({
                "attempt": len(attempts) + 1,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "passed": passed,
                "stable_streak": streak,
                "failed_tests": [
                    item["test_id"] for item in final if not item["passed"]
                ],
            })
            if streak >= stable_samples:
                return final, {
                    "passed": True, "attempts": attempts,
                    "stable_samples_required": stable_samples,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                }
            elapsed = time.monotonic() - started
            if elapsed >= timeout_seconds:
                return final, {
                    "passed": False, "attempts": attempts,
                    "stable_samples_required": stable_samples,
                    "elapsed_seconds": round(elapsed, 3),
                    "timeout_seconds": timeout_seconds,
                }
            time.sleep(min(poll_seconds, max(0.0, timeout_seconds - elapsed)))

    def run(
        self, bundle: CompiledBenchmarkBundle,
        capabilities: Mapping[str, Any], output: Path,
        *, blind_mode: bool = True,
    ) -> Path:
        if not blind_mode:
            raise ValueError("qualification lifecycle must remain blind")
        if capabilities.get("topology_fingerprint") != bundle.topology_fingerprint:
            raise ValueError("lifecycle capabilities differ from compiled bundle")
        private = bundle.private_bundle
        services = tuple(ServiceSpec.from_dict(x) for x in private["services"])
        workloads = tuple(WorkloadSpec.from_dict(x) for x in private["workloads"])
        tests = tuple(TestSpec.from_dict(x) for x in private["tests"])
        plans = tuple(CompiledFaultPlan.from_dict(x) for x in private["fault_plans"])
        execution_id = str(uuid.uuid4())
        fault_executor = FaultExecutor(
            self.journal_root / "faults",
            runner=self.fault_runner or FaultExecutor.__dataclass_fields__["runner"].default,
        )
        plan_by_fingerprint = {x.plan_fingerprint: x for x in plans}
        fault_executor.recover_incomplete(plan_by_fingerprint)
        report: Dict[str, Any] = {
            "schema_version": 1, "run_id": execution_id,
            "bundle_fingerprint": bundle.bundle_fingerprint,
            "generator_contract_sha256": bundle.generator_contract_sha256,
            "benchmark_id": bundle.benchmark_id, "mode": "no_ai",
            "ai_invoked": False, "blind_mode": True,
            "execution_backend": type(self.runner).__name__,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "services": [], "workloads": [], "tests": [], "faults": [],
            "convergence": {}, "passed": False, "topology_tainted": False,
        }
        active = []
        try:
            for service in services:
                code, text, metrics = self.runner.ensure_service(service, capabilities)
                report["services"].append({"service_id": service.service_id, "exit_code": code, "output": text[:1000], "passed": code == 0})
                if code != 0:
                    raise RuntimeError(f"service not ready: {service.service_id}")
            for workload in workloads:
                if workload.warmup_seconds:
                    time.sleep(workload.warmup_seconds)
                code, text, metrics = self.runner.run_workload(workload, capabilities)
                report["workloads"].append({"workload_id": workload.workload_id, "exit_code": code, "output": text[:1000], "passed": code == 0})
                if code != 0:
                    raise RuntimeError(f"workload warmup failed: {workload.workload_id}")
            baseline = self._tests(tests, "baseline", capabilities)
            report["tests"].extend(baseline)
            if not baseline or not all(x["passed"] for x in baseline):
                raise RuntimeError("healthy baseline tests failed")
            for index, plan in enumerate(plans):
                fault_id = f"{execution_id}-{index:04d}"
                path = fault_executor.inject(plan, fault_id)
                active.append((plan, fault_id))
                report["faults"].append({"plan_fingerprint": plan.plan_fingerprint, "journal": str(path), "injection_verified": True})
            active_tests = self._tests(tests, "active", capabilities)
            report["tests"].extend(active_tests)
            if not active_tests or not all(x["passed"] for x in active_tests):
                raise RuntimeError("fault-active tests failed")
            for plan, fault_id in reversed(active):
                fault_executor.recover(plan, fault_id)
            active.clear()
            # Container-level recovery restores the container, but intentionally
            # does not assume that an init system restarted application daemons.
            # Reconcile declared service state before testing recovery so the
            # lifecycle remains portable across SEED base images.
            for service in services:
                code, text, metrics = self.runner.ensure_service(service, capabilities)
                report["services"].append({
                    "service_id": service.service_id,
                    "phase": "recovery", "exit_code": code,
                    "output": text[:1000], "passed": code == 0,
                })
                if code != 0:
                    raise RuntimeError(
                        f"service recovery failed: {service.service_id}"
                    )
            lifecycle = dict(private.get("lifecycle") or {})
            recovery_timeout = min(
                600.0, float(lifecycle.get("recovery_timeout", 300))
            )
            recovery, convergence = self._wait_for_recovery(
                tests, capabilities, timeout_seconds=recovery_timeout,
            )
            report["convergence"] = convergence
            report["tests"].extend(recovery)
            if not convergence["passed"]:
                raise RuntimeError("semantic recovery did not converge")
            for workload in workloads:
                code, text, metrics = self.runner.run_workload(
                    workload, capabilities
                )
                report["workloads"].append({
                    "workload_id": workload.workload_id,
                    "phase": "recovery", "exit_code": code,
                    "output": text[:1000], "passed": code == 0,
                })
                if code != 0:
                    raise RuntimeError(
                        f"semantic recovery workload failed: {workload.workload_id}"
                    )
            report["passed"] = True
        except Exception as exc:
            report["error"] = str(exc)
        finally:
            failures = []
            for plan, fault_id in reversed(active):
                try:
                    fault_executor.recover(plan, fault_id)
                except Exception as exc:
                    failures.append(str(exc))
            report["topology_tainted"] = bool(failures)
            report["cleanup_failures"] = failures
            report["finished_at"] = datetime.now(timezone.utc).isoformat()
            unsigned = dict(report)
            report["receipt_sha256"] = hashlib.sha256(
                json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            self._write(output.resolve(), report)
        if not report["passed"] or report["topology_tainted"]:
            raise RuntimeError(f"bundle lifecycle failed; receipt={output.resolve()}")
        return output.resolve()

"""Static isolation policy and deterministic Compose hardening for unsafe mode."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from typing import Any, Dict, Mapping, Tuple

import yaml

from generator.nl.unsafe_models import IDENTITY, UnsafeScenarioPlan


ALLOWED_TOP_LEVEL = {"services", "networks"}
ALLOWED_SERVICE_KEYS = {
    "build", "image", "command", "entrypoint", "environment", "hostname",
    "networks", "depends_on", "healthcheck", "working_dir", "user", "cap_add",
    "dns", "dns_search",
}
ALLOWED_BUILD_KEYS = {"context", "dockerfile", "args", "target", "labels"}
ALLOWED_NETWORK_KEYS = {"driver", "internal", "ipam", "attachable", "labels"}
ALLOWED_CAPABILITIES = {"NET_ADMIN", "NET_RAW"}
RESERVED_LABEL_PREFIX = "benchmark.unsafe."
PROHIBITED_TEXT = (
    "/var/run/docker.sock", "/run/docker.sock", "host.docker.internal",
    "MIMO_API_KEY", "BENCHMARK_LLM_API_KEY", "DOCKER_HOST",
)


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _safe_relative(path: str, *, prefix: str | None = None) -> PurePosixPath:
    if "\\" in path or "\x00" in path:
        raise ValueError(f"unsafe generated path is invalid: {path!r}")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or not candidate.parts or ".." in candidate.parts:
        raise ValueError(f"unsafe generated path escapes the bundle: {path!r}")
    if any(part in {"", ".", ".git", ".ssh"} for part in candidate.parts):
        raise ValueError(f"unsafe generated path uses a prohibited component: {path!r}")
    if prefix and candidate.parts[0] != prefix:
        raise ValueError(f"unsafe generated path must stay below {prefix}/: {path!r}")
    return candidate


def _labels(value: Any) -> Dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("unsafe service labels must be a mapping")
    labels = {str(key): str(item) for key, item in value.items()}
    if any(key.startswith(RESERVED_LABEL_PREFIX) for key in labels):
        raise ValueError("unsafe plan cannot set reserved isolation labels")
    return labels


def _validate_dockerfile(path: str, content: str) -> Tuple[str, ...]:
    if not re.search(r"(?im)^\s*FROM\s+\S+", content):
        raise ValueError(f"generated Dockerfile has no FROM instruction: {path}")
    patterns = (
        r"(?im)^\s*#\s*syntax\s*=",
        r"(?im)^\s*VOLUME\b",
        r"(?im)^\s*ADD\s+(?:--\S+\s+)*https?://",
        r"(?im)^\s*RUN\s+--security=(?:insecure|sandbox)\b",
        r"(?i)--mount=type=(?:ssh|secret)",
        r"(?i)/var/run/docker\.sock|/run/docker\.sock",
    )
    if any(re.search(pattern, content) for pattern in patterns):
        raise ValueError(f"generated Dockerfile violates the isolation policy: {path}")
    aliases = set()
    base_images = []
    for match in re.finditer(
        r"(?im)^\s*FROM(?:\s+--platform=\S+)?\s+(\S+)(?:\s+AS\s+(\S+))?\s*$",
        content,
    ):
        reference, alias = match.group(1), match.group(2)
        if "$" in reference:
            raise ValueError(f"generated Dockerfile has a variable base image: {path}")
        if reference.casefold() not in aliases:
            base_images.append(reference)
        if alias:
            aliases.add(alias.casefold())
    for match in re.finditer(r"(?im)^\s*COPY\s+--from=(\S+)", content):
        reference = match.group(1).casefold()
        if reference not in aliases and not reference.isdigit():
            raise ValueError(f"generated Dockerfile COPY --from must use a local stage: {path}")
    return tuple(base_images)


@dataclass(frozen=True)
class UnsafePolicyResult:
    service_ids: Tuple[str, ...]
    network_ids: Tuple[str, ...]
    base_images: Tuple[str, ...]
    sanitized_compose: Dict[str, Any]
    sanitized_compose_yaml: str
    bundle_bytes: int
    effective_limits: Dict[str, Any]
    risks: Tuple[Dict[str, str], ...]
    policy_fingerprint: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": True,
            "service_ids": list(self.service_ids),
            "network_ids": list(self.network_ids),
            "base_images": list(self.base_images),
            "sanitized_compose": self.sanitized_compose,
            "sanitized_compose_yaml": self.sanitized_compose_yaml,
            "bundle_bytes": self.bundle_bytes,
            "effective_limits": self.effective_limits,
            "risks": list(self.risks),
            "policy_fingerprint": self.policy_fingerprint,
        }


def policy_snapshot() -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "mode": "container_scoped_arbitrary_execution",
        "default": "plan_only",
        "prohibited": [
            "host bind mounts", "Docker socket", "privileged containers",
            "host network/PID/IPC/user namespaces", "host port publication",
            "devices", "external Compose networks", "automatic qualification",
            "automatic publication",
        ],
        "allowed_capabilities": sorted(ALLOWED_CAPABILITIES),
        "runtime_filesystem": "read-only root plus budgeted tmpfs /tmp and /run",
        "build_network": "none",
        "docker_scope": "unique Compose project and reserved session labels",
    }


def compile_unsafe_policy(
    plan: UnsafeScenarioPlan, *, session_label: str,
) -> UnsafePolicyResult:
    if not IDENTITY.fullmatch(session_label):
        raise ValueError("unsafe session label is invalid")
    if "${" in plan.compose_yaml:
        raise ValueError("unsafe Compose cannot interpolate host environment variables")
    if any(marker.casefold() in plan.compose_yaml.casefold() for marker in PROHIBITED_TEXT):
        raise ValueError("unsafe Compose references a prohibited host capability")
    try:
        document = yaml.safe_load(plan.compose_yaml)
    except yaml.YAMLError as exc:
        raise ValueError("unsafe Compose YAML is invalid") from exc
    if not isinstance(document, Mapping):
        raise ValueError("unsafe Compose must be a mapping")
    unknown_top = set(document) - ALLOWED_TOP_LEVEL
    if unknown_top:
        raise ValueError(f"unsafe Compose top-level keys are prohibited: {sorted(unknown_top)}")
    services = document.get("services")
    networks = document.get("networks")
    if not isinstance(services, Mapping) or not services:
        raise ValueError("unsafe Compose must declare services")
    if not isinstance(networks, Mapping) or not networks:
        raise ValueError("unsafe Compose must declare explicit isolated networks")
    service_ids = tuple(sorted(str(item) for item in services))
    network_ids = tuple(sorted(str(item) for item in networks))
    if len(service_ids) > plan.budget.max_services:
        raise ValueError("unsafe Compose exceeds the service budget")
    if any(not IDENTITY.fullmatch(item) for item in service_ids + network_ids):
        raise ValueError("unsafe Compose service or network identity is invalid")

    files = {item.path: item for item in plan.files}
    bundle_bytes = len(plan.compose_yaml.encode("utf-8")) + sum(
        len(item.content.encode("utf-8")) for item in plan.files
    )
    if bundle_bytes > plan.budget.max_disk_mb * 1024 * 1024:
        raise ValueError("unsafe generated bundle exceeds its disk budget")
    base_images = set()
    for item in plan.files:
        relative = _safe_relative(item.path, prefix="services")
        if relative.name.lower() == "dockerfile":
            base_images.update(_validate_dockerfile(item.path, item.content))
        if any(marker.casefold() in item.content.casefold() for marker in PROHIBITED_TEXT):
            raise ValueError(f"unsafe generated file references a prohibited host capability: {item.path}")

    sanitized = {"services": {}, "networks": {}}
    memory_each = plan.budget.max_memory_mb // len(service_ids)
    cpu_each = math.floor(
        plan.budget.max_cpu_cores / len(service_ids) * 1000
    ) / 1000
    disk_each = plan.budget.max_disk_mb // len(service_ids)
    if memory_each < 64 or cpu_each <= 0:
        raise ValueError("unsafe resource budget cannot cover every service")
    for service_id in service_ids:
        raw = services[service_id]
        if not isinstance(raw, Mapping):
            raise ValueError(f"unsafe Compose service must be a mapping: {service_id}")
        unknown = set(raw) - ALLOWED_SERVICE_KEYS
        if unknown:
            raise ValueError(f"unsafe service keys are prohibited for {service_id}: {sorted(unknown)}")
        build = raw.get("build")
        if isinstance(build, str):
            build = {"context": build, "dockerfile": "Dockerfile"}
        if not isinstance(build, Mapping):
            raise ValueError(f"unsafe service must use a generated build context: {service_id}")
        unknown_build = set(build) - ALLOWED_BUILD_KEYS
        if unknown_build:
            raise ValueError(f"unsafe build keys are prohibited for {service_id}: {sorted(unknown_build)}")
        expected_context = f"./services/{service_id}"
        context = str(build.get("context", ""))
        dockerfile = str(build.get("dockerfile", "Dockerfile"))
        if context != expected_context or dockerfile != "Dockerfile":
            raise ValueError(f"unsafe build context must be {expected_context}/Dockerfile")
        build_labels = _labels(build.get("labels"))
        build_labels.update({
            "benchmark.unsafe.generated": "true",
            "benchmark.unsafe.session": session_label,
            "benchmark.unsafe.request": plan.request_id,
        })
        dockerfile_path = f"services/{service_id}/Dockerfile"
        if dockerfile_path not in files:
            raise ValueError(f"unsafe build is missing generated file: {dockerfile_path}")
        declared_networks = raw.get("networks")
        if isinstance(declared_networks, Mapping):
            used_networks = set(str(item) for item in declared_networks)
        elif isinstance(declared_networks, list):
            used_networks = set(str(item) for item in declared_networks)
        else:
            raise ValueError(f"unsafe service must join explicit networks: {service_id}")
        if not used_networks or not used_networks <= set(network_ids):
            raise ValueError(f"unsafe service references undeclared networks: {service_id}")
        depends_on = raw.get("depends_on", [])
        dependency_ids = set(depends_on) if isinstance(depends_on, (list, Mapping)) else set()
        if not dependency_ids <= set(service_ids):
            raise ValueError(f"unsafe service references an unknown dependency: {service_id}")
        capabilities = raw.get("cap_add", []) or []
        if not isinstance(capabilities, list) or not set(capabilities) <= ALLOWED_CAPABILITIES:
            raise ValueError(f"unsafe service requests prohibited Linux capabilities: {service_id}")
        labels = _labels(raw.get("labels"))
        labels.update({
            "benchmark.unsafe.generated": "true",
            "benchmark.unsafe.session": session_label,
            "benchmark.unsafe.request": plan.request_id,
        })
        service = deepcopy(dict(raw))
        service["build"] = {
            **dict(build), "context": expected_context, "dockerfile": "Dockerfile",
            "network": "none", "labels": build_labels,
        }
        service["image"] = f"unsafe-local/{session_label}-{service_id}:{plan.fingerprint[:12]}"
        service["labels"] = labels
        service["privileged"] = False
        service["cap_drop"] = ["ALL"]
        service["cap_add"] = sorted(capabilities)
        service["read_only"] = True
        service["pids_limit"] = 256
        service["cpus"] = cpu_each
        service["mem_limit"] = f"{memory_each}m"
        run_mb = min(16, max(8, disk_each // 4))
        tmp_mb = disk_each - run_mb
        service["tmpfs"] = [
            f"/tmp:rw,nosuid,nodev,size={tmp_mb}m",
            f"/run:rw,nosuid,nodev,size={run_mb}m",
        ]
        service["restart"] = "no"
        service["stop_grace_period"] = "10s"
        sanitized["services"][service_id] = service

    for network_id in network_ids:
        raw = networks[network_id]
        if raw is None:
            raw = {}
        if not isinstance(raw, Mapping):
            raise ValueError(f"unsafe Compose network must be a mapping: {network_id}")
        unknown = set(raw) - ALLOWED_NETWORK_KEYS
        if unknown:
            raise ValueError(f"unsafe network keys are prohibited for {network_id}: {sorted(unknown)}")
        if raw.get("driver", "bridge") != "bridge":
            raise ValueError("unsafe networks must use the Docker bridge driver")
        network = deepcopy(dict(raw))
        network["driver"] = "bridge"
        network["internal"] = True
        labels = _labels(network.get("labels"))
        labels.update({
            "benchmark.unsafe.generated": "true",
            "benchmark.unsafe.session": session_label,
        })
        network["labels"] = labels
        sanitized["networks"][network_id] = network

    step_services = {item.service for item in plan.steps}
    if not step_services <= set(service_ids):
        raise ValueError("unsafe lifecycle step references an unknown service")
    phases = {item.phase for item in plan.steps}
    if phases != {"baseline", "exercise", "verify"}:
        raise ValueError("unsafe lifecycle must include baseline, exercise and verify phases")

    sanitized_yaml = yaml.safe_dump(sanitized, sort_keys=True, allow_unicode=True)
    effective_limits = {
        "service_count": len(service_ids),
        "cpu_per_service": cpu_each,
        "memory_mb_per_service": memory_each,
        "writable_tmpfs_mb_per_service": disk_each,
        "pids_per_service": 256,
        "build_seconds": plan.budget.max_build_seconds,
        "runtime_seconds": plan.budget.max_runtime_seconds,
        "step_seconds": plan.budget.max_step_seconds,
        "image_bytes_total": plan.budget.max_disk_mb * 1024 * 1024,
    }
    risks = (
        {"severity": "critical", "code": "arbitrary_container_shell", "mitigation": "shell runs only through Compose exec without Docker socket"},
        {"severity": "high", "code": "generated_dockerfiles", "mitigation": "isolated build context, network=none, time and image-size budgets"},
        {"severity": "high", "code": "linux_net_admin", "mitigation": "only NET_ADMIN/NET_RAW in private non-host namespaces"},
        {"severity": "high", "code": "untrusted_compose", "mitigation": "strict key policy plus deterministic hardening and project labels"},
        {"severity": "medium", "code": "no_automatic_qualification", "mitigation": "unsafe_generated plans are permanently promotion-ineligible"},
    )
    policy_fingerprint = _sha({
        "plan": plan.fingerprint,
        "session_label": session_label,
        "compose": sanitized,
        "limits": effective_limits,
        "policy": policy_snapshot(),
    })
    return UnsafePolicyResult(
        service_ids, network_ids, tuple(sorted(base_images)), sanitized,
        sanitized_yaml, bundle_bytes,
        effective_limits, risks, policy_fingerprint,
    )

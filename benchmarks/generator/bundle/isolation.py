"""Scoped Docker Compose lifecycle for one production Bundle execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Mapping, Sequence, Tuple
import uuid

import yaml


PROJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,62}$")
IPV4_PATTERN = re.compile(
    r"(?<![0-9.])(\d{1,3}(?:\.\d{1,3}){3})(/\d{1,2})?"
)
NETWORK_POOL = ipaddress.ip_network("10.128.0.0/9")
NETWORK_LOCK = Path("/tmp/seed-bundle-network-allocation.lock")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise


@dataclass
class BundleRunIsolator:
    """Own one Compose project and prove teardown before returning."""

    benchmarks_dir: Path
    topology_id: str
    request_id: str
    workspace: Path
    timeout_seconds: int = 600
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])

    def __post_init__(self) -> None:
        self.benchmarks_dir = self.benchmarks_dir.resolve()
        self.workspace = self.workspace.resolve()
        generated = (
            self.benchmarks_dir / "generated" / "declarative"
            / self.topology_id / "output"
        ).resolve()
        expected_root = (self.benchmarks_dir / "generated" / "declarative").resolve()
        if expected_root not in generated.parents:
            raise ValueError("isolated Compose path escaped generated/declarative")
        self.compose_file = generated / "docker-compose.yml"
        if not self.compose_file.is_file():
            raise ValueError("isolated Bundle requires a compiled Compose topology")
        compose = yaml.safe_load(self.compose_file.read_text(encoding="utf-8")) or {}
        self.source_compose = compose
        self.base_project = str(compose.get("name", f"decl_{self.topology_id}"))
        slug = re.sub(r"[^a-z0-9]+", "-", self.request_id.lower()).strip("-")[:38]
        self.project = f"bndl-{slug}-{self.session_id}"
        if not PROJECT_PATTERN.fullmatch(self.project):
            raise ValueError("invalid isolated Compose project identity")
        services = compose.get("services") or {}
        if not isinstance(services, Mapping) or not services:
            raise ValueError("isolated Bundle Compose file has no services")
        self.runtime_context = (self.workspace / "runtime_context").resolve()
        if self.runtime_context.parent != self.workspace:
            raise ValueError("runtime Compose context escaped Bundle workspace")
        if self.runtime_context.exists():
            raise FileExistsError("runtime Compose context already exists")
        self.runtime_compose_file = self.runtime_context / "docker-compose.yml"
        self.generated_context = generated
        self.fixed_container_names = sum(
            isinstance(service, Mapping) and "container_name" in service
            for service in services.values()
        )
        self.original_container_names = {
            str(service_name): str(service["container_name"])
            for service_name, service in services.items()
            if isinstance(service, Mapping) and service.get("container_name")
        }
        self.network_map: Dict[str, str] = {}
        self.service_containers: Dict[str, str] = {}
        self.report_path = self.workspace / "isolation.json"
        self.report: Dict[str, Any] = {
            "schema_version": 1,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "topology_id": self.topology_id,
            "compose_project": self.project,
            "base_compose_project": self.base_project,
            "compose_sha256": hashlib.sha256(self.compose_file.read_bytes()).hexdigest(),
            "runtime_compose_sha256": "",
            "runtime_compose_file": str(self.runtime_compose_file),
            "fixed_container_names_removed": self.fixed_container_names,
            "started_at": _now(),
            "status": "created",
            "commands": [],
            "containers": [],
            "cleanup_verified": False,
            "runtime_compose_removed": False,
            "runtime_context_removed": False,
            "network_rebindings": {},
        }
        _atomic_json(self.report_path, self.report)

    def _run(self, argv: Sequence[str], timeout: int | None = None) -> Tuple[int, str]:
        try:
            result = subprocess.run(
                list(argv), capture_output=True, text=True,
                timeout=timeout or self.timeout_seconds,
            )
            output = result.stdout + result.stderr
            self.report["commands"].append({
                "argv": list(argv), "exit_code": result.returncode,
                "output": output[-4000:], "finished_at": _now(),
            })
            _atomic_json(self.report_path, self.report)
            return result.returncode, output
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or "") + (exc.stderr or ""))[-4000:]
            self.report["commands"].append({
                "argv": list(argv), "exit_code": 124,
                "output": output, "finished_at": _now(),
            })
            _atomic_json(self.report_path, self.report)
            return 124, output

    def _compose(self, *args: str) -> Tuple[int, str]:
        return self._run((
            "docker", "compose", "--project-name", self.project,
            "--file", str(self.runtime_compose_file), *args,
        ))

    def _existing_networks(self) -> Tuple[ipaddress.IPv4Network, ...]:
        code, output = self._run(("docker", "network", "ls", "-q"), 30)
        if code != 0:
            raise RuntimeError("failed to inventory Docker networks")
        identifiers = tuple(line.strip() for line in output.splitlines() if line.strip())
        if not identifiers:
            return ()
        code, output = self._run(("docker", "network", "inspect", *identifiers), 60)
        if code != 0:
            raise RuntimeError("failed to inspect Docker network address pools")
        result = []
        for network in json.loads(output):
            for config in (network.get("IPAM") or {}).get("Config") or ():
                subnet = config.get("Subnet")
                if not subnet:
                    continue
                parsed = ipaddress.ip_network(str(subnet), strict=False)
                if isinstance(parsed, ipaddress.IPv4Network):
                    result.append(parsed)
        return tuple(result)

    def _source_networks(self) -> Tuple[ipaddress.IPv4Network, ...]:
        result = []
        for network in (self.source_compose.get("networks") or {}).values():
            if not isinstance(network, Mapping):
                continue
            for config in (network.get("ipam") or {}).get("config") or ():
                if not isinstance(config, Mapping) or not config.get("subnet"):
                    continue
                parsed = ipaddress.ip_network(str(config["subnet"]), strict=False)
                if not isinstance(parsed, ipaddress.IPv4Network):
                    raise ValueError("Bundle isolation supports IPv4 topology networks")
                result.append(parsed)
        return tuple(result)

    def _allocate_networks(self) -> Dict[str, str]:
        used = list(self._existing_networks())
        result: Dict[str, str] = {}
        for index, original in enumerate(self._source_networks()):
            if original.prefixlen < NETWORK_POOL.prefixlen:
                raise ValueError("topology subnet is larger than isolation address pool")
            candidates = tuple(NETWORK_POOL.subnets(new_prefix=original.prefixlen))
            seed = int(hashlib.sha256(
                f"{self.project}:{index}:{original}".encode("utf-8")
            ).hexdigest(), 16)
            selected = None
            for offset in range(len(candidates)):
                candidate = candidates[(seed + offset) % len(candidates)]
                if not any(candidate.overlaps(item) for item in used):
                    selected = candidate
                    break
            if selected is None:
                raise RuntimeError("isolation address pool is exhausted")
            result[str(original)] = str(selected)
            used.append(selected)
        return result

    def _rebind_text(self, value: str) -> str:
        networks = tuple(
            (ipaddress.ip_network(source), ipaddress.ip_network(target))
            for source, target in self.network_map.items()
        )

        def replace(match: re.Match[str]) -> str:
            try:
                address = ipaddress.ip_address(match.group(1))
            except ValueError:
                return match.group(0)
            for source, target in networks:
                if address in source:
                    rebound = target.network_address + (
                        int(address) - int(source.network_address)
                    )
                    suffix = match.group(2) or ""
                    return f"{rebound}{suffix}"
            return match.group(0)

        return IPV4_PATTERN.sub(replace, value)

    def _prepare_runtime_context(self) -> None:
        shutil.copytree(self.generated_context, self.runtime_context)
        self.network_map = self._allocate_networks()
        for path in self.runtime_context.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            rebound = self._rebind_text(content)
            if rebound != content:
                path.write_text(rebound, encoding="utf-8")

        compose = yaml.safe_load(
            self.runtime_compose_file.read_text(encoding="utf-8")
        ) or {}
        compose.pop("name", None)
        for service_name, service in (compose.get("services") or {}).items():
            if not isinstance(service, dict):
                continue
            original_name = self.original_container_names.get(str(service_name))
            service.pop("container_name", None)
            aliases = {
                str(service_name), f"{self.project}-{service_name}-1"
            }
            if original_name:
                aliases.add(original_name)
            attached = service.get("networks")
            if isinstance(attached, list):
                service["networks"] = {
                    str(name): {"aliases": sorted(aliases)} for name in attached
                }
            elif isinstance(attached, dict):
                for name, config in tuple(attached.items()):
                    if config is None:
                        config = {}
                        attached[name] = config
                    if not isinstance(config, dict):
                        raise ValueError("unsupported Compose service network definition")
                    config["aliases"] = sorted(
                        aliases | set(config.get("aliases") or ())
                    )
        self.runtime_compose_file.write_text(
            yaml.safe_dump(compose, sort_keys=False), encoding="utf-8"
        )
        self.report["runtime_compose_sha256"] = hashlib.sha256(
            self.runtime_compose_file.read_bytes()
        ).hexdigest()
        self.report["network_rebindings"] = dict(sorted(self.network_map.items()))
        _atomic_json(self.report_path, self.report)

    def _ids(self, *, all_containers: bool = True) -> Tuple[str, ...]:
        argv = ["docker", "ps"]
        if all_containers:
            argv.append("-a")
        argv += [
            "--filter", f"label=com.docker.compose.project={self.project}",
            "--format", "{{.ID}}",
        ]
        code, output = self._run(tuple(argv), 30)
        if code != 0:
            raise RuntimeError("failed to inventory isolated Compose containers")
        return tuple(line.strip() for line in output.splitlines() if line.strip())

    def capabilities(self, value: Mapping[str, Any]) -> Dict[str, Any]:
        """Bind every service-owned container and network to this session."""
        if not self.service_containers:
            raise RuntimeError("runtime service containers have not been discovered")
        original_assets = value.get("assets") or ()
        original_to_runtime = {}
        original_to_service = {}
        for asset in original_assets:
            service = str(asset.get("service", ""))
            original = str(asset.get("container", ""))
            runtime = self.service_containers.get(service)
            if not service or not original or not runtime:
                raise ValueError("asset cannot be rebound through a Compose service")
            original_to_runtime[original] = runtime
            original_to_service[original] = service

        def rebind(item, key=""):
            if isinstance(item, dict):
                return {child_key: rebind(child, str(child_key)) for child_key, child in item.items()}
            if isinstance(item, list):
                return [rebind(child, key) for child in item]
            if isinstance(item, str):
                return original_to_runtime.get(item, self._rebind_text(item))
            return item

        result = rebind(json.loads(json.dumps(value)))
        result["runtime_session"] = {
            "session_id": self.session_id,
            "compose_project": self.project,
            "isolation": "parallel",
            "service_containers": dict(sorted(self.service_containers.items())),
            "container_services": {
                container: service
                for service, container in sorted(self.service_containers.items())
            },
            "network_rebindings": dict(sorted(self.network_map.items())),
        }
        bindings = result.get("fault_component_bindings") or {}
        for binding in bindings.get("docker_network_disconnected") or ():
            network = str(binding.get("docker_network", ""))
            prefix = f"{self.base_project}_"
            if not network.startswith(prefix):
                raise ValueError("Docker network binding does not match Compose project")
            binding["docker_network"] = f"{self.project}_{network[len(prefix):]}"
        self.report["service_containers"] = dict(
            sorted(self.service_containers.items())
        )
        self.report["container_rebindings"] = dict(
            sorted(original_to_runtime.items())
        )
        self.report["peer_service_rebindings"] = {
            original_to_runtime[original]: service
            for original, service in sorted(original_to_service.items())
        }
        _atomic_json(self.report_path, self.report)
        return result

    def start(self) -> None:
        if self._ids():
            raise RuntimeError("isolated Compose project already owns containers")
        self.report["status"] = "starting"
        _atomic_json(self.report_path, self.report)
        NETWORK_LOCK.parent.mkdir(parents=True, exist_ok=True)
        with NETWORK_LOCK.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            self._prepare_runtime_context()
            code, output = self._compose("up", "-d", "--build", "--remove-orphans")
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
        if code != 0:
            self.report["status"] = "start_failed"
            self.report["error"] = output[-1000:]
            _atomic_json(self.report_path, self.report)
            raise RuntimeError("isolated Compose startup failed")
        ids = self._ids(all_containers=True)
        if not ids:
            raise RuntimeError("isolated Compose started no containers")
        for container_id in ids:
            code, details = self._run((
                "docker", "inspect", "--format",
                "{{.Name}}|{{.Image}}|"
                "{{index .Config.Labels \"com.docker.compose.project\"}}|"
                "{{index .Config.Labels \"com.docker.compose.service\"}}",
                container_id,
            ), 30)
            if code != 0:
                raise RuntimeError("container escaped isolated Compose ownership")
            name, image, project, service = (
                details.strip().lstrip("/").split("|", 3)
            )
            if project != self.project or not service:
                raise RuntimeError("container escaped isolated Compose ownership")
            if service in self.service_containers:
                raise RuntimeError("Compose service resolved to multiple containers")
            self.service_containers[service] = name
            self.report["containers"].append({
                "id": container_id, "name": name,
                "image_digest": image, "compose_project": project,
                "service": service,
            })
        self.report["status"] = "running"
        self.report["running_at"] = _now()
        _atomic_json(self.report_path, self.report)

    def stop(self) -> None:
        if self.report.get("status") == "cleaned" and self.report.get(
            "cleanup_verified"
        ) is True:
            return
        self.report["status"] = "cleaning"
        _atomic_json(self.report_path, self.report)
        if self.runtime_compose_file.is_file():
            code, output = self._compose("down", "--remove-orphans", "--volumes")
        else:
            code, output = 0, "runtime context was not created"
        remaining = self._ids()
        context_removed = False
        if code == 0 and not remaining and self.runtime_context.exists():
            if (
                self.runtime_context.parent != self.workspace
                or self.runtime_context.name != "runtime_context"
            ):
                raise RuntimeError("refusing to remove unexpected runtime context")
            shutil.rmtree(self.runtime_context)
            context_removed = not self.runtime_context.exists()
        elif code == 0 and not remaining:
            context_removed = True
        self.report["runtime_compose_removed"] = context_removed
        self.report["runtime_context_removed"] = context_removed
        self.report["cleanup_verified"] = (
            code == 0 and not remaining and context_removed
        )
        self.report["remaining_container_ids"] = list(remaining)
        self.report["finished_at"] = _now()
        self.report["status"] = (
            "cleaned" if self.report["cleanup_verified"] else "cleanup_failed"
        )
        if code != 0:
            self.report["cleanup_error"] = output[-1000:]
        _atomic_json(self.report_path, self.report)
        if not self.report["cleanup_verified"]:
            raise RuntimeError("isolated Compose cleanup could not be verified")

    def __enter__(self) -> "BundleRunIsolator":
        try:
            self.start()
        except Exception:
            try: self.stop()
            except Exception: pass
            raise
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        self.stop()
        return False

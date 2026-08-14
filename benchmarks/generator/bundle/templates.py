"""Versioned application semantics used by deterministic Agent workers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Dict, Mapping, Tuple

from generator.software import PACKAGE_PATTERN


TEMPLATE_SCHEMA_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
ARGV_PATTERN = re.compile(r"^[^\x00\r\n`$;&|<>]{1,256}$")
SUPPORTED_WORKLOADS = {"workload.http", "workload.dns", "workload.tcp"}
SUPPORTED_PROBES = {"probe.http", "probe.dns", "probe.tcp"}


@dataclass(frozen=True)
class ApplicationTemplate:
    template_id: str
    version: str
    software_id: str
    capability: str
    packages: Tuple[str, ...]
    port: int
    start_argv: Tuple[str, ...]
    health_argv: Tuple[str, ...]
    workload_driver: str
    probe_driver: str
    parameter_mode: str
    suggested_faults: Tuple[str, ...]
    source_mode: str = "observer"
    query_name: str = "service.benchmark.test"
    schema_version: int = TEMPLATE_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ApplicationTemplate":
        fields = set(cls.__dataclass_fields__)
        data = dict(value)
        required = fields - {"schema_version", "source_mode", "query_name"}
        if set(data) - fields or required - set(data):
            raise ValueError("invalid ApplicationTemplate schema keys")
        template = cls(
            template_id=str(data["template_id"]), version=str(data["version"]),
            software_id=str(data["software_id"]), capability=str(data["capability"]),
            packages=tuple(str(x) for x in data["packages"]),
            port=int(data["port"]), start_argv=tuple(str(x) for x in data["start_argv"]),
            health_argv=tuple(str(x) for x in data["health_argv"]),
            workload_driver=str(data["workload_driver"]),
            probe_driver=str(data["probe_driver"]),
            parameter_mode=str(data["parameter_mode"]),
            suggested_faults=tuple(str(x) for x in data["suggested_faults"]),
            source_mode=str(data.get("source_mode", "observer")),
            query_name=str(data.get("query_name", "service.benchmark.test")),
            schema_version=int(data.get("schema_version", 1)),
        )
        template.validate()
        return template

    def validate(self) -> None:
        if self.schema_version != 1 or any(
            not ID_PATTERN.fullmatch(item)
            for item in (self.template_id, self.software_id, self.capability)
        ):
            raise ValueError("invalid application template identity")
        if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", self.version):
            raise ValueError("application template version must be semver")
        if not self.packages or any(not PACKAGE_PATTERN.fullmatch(x) for x in self.packages):
            raise ValueError("application template packages are invalid")
        if not 1 <= self.port <= 65535:
            raise ValueError("application template port is invalid")
        for argv in (self.start_argv, self.health_argv):
            if not argv or any(not ARGV_PATTERN.fullmatch(item) for item in argv):
                raise ValueError("application template argv is unsafe")
        if self.workload_driver not in SUPPORTED_WORKLOADS or self.probe_driver not in SUPPORTED_PROBES:
            raise ValueError("application template driver is unsupported")
        if self.parameter_mode not in {"http", "dns", "tcp"}:
            raise ValueError("application template parameter mode is unsupported")
        if self.source_mode not in {"observer", "service"}:
            raise ValueError("application template source mode is invalid")
        if not re.fullmatch(
            r"(?=.{1,253}\.?$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
            self.query_name,
        ):
            raise ValueError("application template query_name is invalid")
        if not self.suggested_faults or any(not ID_PATTERN.fullmatch(x) for x in self.suggested_faults):
            raise ValueError("application template faults are invalid")

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ("packages", "start_argv", "health_argv", "suggested_faults"):
            value[key] = list(value[key])
        return value

    def parameters(self, address: str) -> Dict[str, Any]:
        if self.parameter_mode == "http":
            return {"url": f"http://{address}:{self.port}/"}
        if self.parameter_mode == "dns":
            return {"name": self.query_name, "server": address}
        return {"host": address, "port": self.port}


class ApplicationTemplateRegistry:
    def __init__(self):
        self._templates: Dict[str, ApplicationTemplate] = {}

    def register(self, template: ApplicationTemplate) -> None:
        template.validate()
        if template.template_id in self._templates:
            raise ValueError(f"duplicate application template={template.template_id}")
        self._templates[template.template_id] = template

    def require(self, template_id: str) -> ApplicationTemplate:
        try:
            return self._templates[template_id]
        except KeyError as exc:
            raise ValueError(f"unknown application template={template_id}") from exc

    def load_file(self, path: Path) -> ApplicationTemplate:
        template = ApplicationTemplate.from_dict(
            json.loads(path.resolve().read_text(encoding="utf-8"))
        )
        self.register(template)
        return template

    def inventory(self) -> Tuple[ApplicationTemplate, ...]:
        return tuple(self._templates[key] for key in sorted(self._templates))


def builtin_template_registry() -> ApplicationTemplateRegistry:
    registry = ApplicationTemplateRegistry()
    for value in (
        {
            "template_id": "nginx", "version": "1.0.0", "software_id": "nginx",
            "capability": "http.nginx.v1", "packages": ["nginx"], "port": 80,
            "start_argv": ["service", "nginx", "start"],
            "health_argv": ["curl", "-fsS", "http://127.0.0.1/"],
            "workload_driver": "workload.http", "probe_driver": "probe.http",
            "parameter_mode": "http", "suggested_faults": [
                "container.stopped", "network.netem"
            ],
        },
        {
            "template_id": "bind9", "version": "1.0.0", "software_id": "bind9",
            "capability": "dns.bind9.v1", "packages": ["bind9", "dnsutils"], "port": 53,
            "start_argv": ["service", "named", "start"],
            "health_argv": ["rndc", "status"],
            "workload_driver": "workload.dns", "probe_driver": "probe.dns",
            "parameter_mode": "dns", "query_name": "service.pilot.test",
            "suggested_faults": [
                "container.stopped", "network.netem"
            ],
        },
        {
            "template_id": "postgresql", "version": "1.0.0", "software_id": "postgresql",
            "capability": "database.postgresql.v1",
            "packages": ["postgresql", "postgresql-client"], "port": 5432,
            "start_argv": ["service", "postgresql", "start"],
            "health_argv": ["pg_isready"],
            "workload_driver": "workload.tcp", "probe_driver": "probe.tcp",
            "parameter_mode": "tcp", "source_mode": "service",
            "suggested_faults": [
                "container.stopped", "network.netem"
            ],
        },
        {
            "template_id": "network_observer", "version": "1.0.0",
            "software_id": "curl_tools", "capability": "observer.network.v1",
            "packages": ["curl", "dnsutils", "netcat-openbsd"], "port": 65535,
            "start_argv": ["true"], "health_argv": ["true"],
            "workload_driver": "workload.tcp", "probe_driver": "probe.tcp",
            "parameter_mode": "tcp", "source_mode": "service",
            "suggested_faults": ["container.stopped"],
        },
    ):
        registry.register(ApplicationTemplate.from_dict({"schema_version": 1, **value}))
    return registry

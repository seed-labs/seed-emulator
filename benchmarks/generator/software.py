"""Typed software installation and fault-profile contracts.

Software declarations are data, never shell fragments.  The topology compiler
translates package names and managed files into SEED APIs; fault drivers
translate audited profile kinds into runtime commands.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import re
from typing import Any, Dict, Mapping, Sequence, Tuple


SOFTWARE_SPEC_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{1,63}$")
PACKAGE_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9+.-]*(?::[a-z0-9][a-z0-9-]*)?"
    r"(?:=[0-9A-Za-z:+.~_-]+)?$"
)
CAPABILITY_PATTERN = re.compile(r"^[a-z][a-z0-9_.-]{2,95}$")
NODE_PATTERN = re.compile(r"^(?:router0|host(?:0|[1-9][0-9]{0,2}))$")
MODE_PATTERN = re.compile(r"^[0-7]{3,4}$")
ALLOWED_ROLES = {"router", "host"}
MANAGED_FILE_ROOTS = ("/etc/", "/opt/benchmark/", "/usr/local/etc/")
EXECUTABLE_ROOTS = ("/usr/bin/", "/usr/sbin/", "/usr/local/bin/", "/usr/local/sbin/")
PROTECTED_PATHS = {
    "/bin/sh", "/usr/bin/sh", "/usr/bin/env", "/usr/bin/python3",
    "/etc/passwd", "/etc/shadow", "/etc/group", "/etc/resolv.conf",
}


def _strict(value: Mapping[str, Any], required, optional=()) -> Dict[str, Any]:
    data = dict(value)
    missing = sorted(set(required) - set(data))
    extra = sorted(set(data) - set(required) - set(optional))
    if missing or extra:
        raise ValueError(
            f"invalid software schema keys: missing={missing}, extra={extra}"
        )
    return data


def _safe_absolute_path(path: str, roots: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    return (
        candidate.is_absolute()
        and ".." not in candidate.parts
        and str(candidate) == path
        and path not in PROTECTED_PATHS
        and any(path.startswith(root) for root in roots)
    )


@dataclass(frozen=True)
class ManagedFileSpec:
    path: str
    content: str
    mode: str = "0644"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ManagedFileSpec":
        data = _strict(value, ("path", "content"), ("mode",))
        return cls(path=str(data["path"]), content=str(data["content"]),
                   mode=str(data.get("mode", "0644")))


@dataclass(frozen=True)
class SoftwareFaultProfile:
    profile_id: str
    fault_type: str
    parameters: Dict[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SoftwareFaultProfile":
        data = _strict(value, ("profile_id", "fault_type", "parameters"))
        if not isinstance(data["parameters"], Mapping):
            raise ValueError("software fault profile parameters must be an object")
        return cls(
            profile_id=str(data["profile_id"]),
            fault_type=str(data["fault_type"]),
            parameters=dict(data["parameters"]),
        )


@dataclass(frozen=True)
class SoftwareSpec:
    """Install one logical software capability on a bounded asset selector."""

    software_id: str
    packages: Tuple[str, ...]
    target_roles: Tuple[str, ...] = ("host",)
    target_asns: Tuple[int, ...] = ()
    target_nodes: Tuple[str, ...] = ()
    capabilities: Tuple[str, ...] = ()
    managed_files: Tuple[ManagedFileSpec, ...] = ()
    fault_profiles: Tuple[SoftwareFaultProfile, ...] = ()
    schema_version: int = SOFTWARE_SPEC_VERSION

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        for key in ("packages", "target_roles", "target_asns", "target_nodes",
                    "capabilities", "managed_files", "fault_profiles"):
            value[key] = list(value[key])
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SoftwareSpec":
        required = ("software_id", "packages")
        optional = tuple(x for x in cls.__dataclass_fields__ if x not in required)
        data = _strict(value, required, optional)
        if int(data.get("schema_version", SOFTWARE_SPEC_VERSION)) != SOFTWARE_SPEC_VERSION:
            raise ValueError("unsupported SoftwareSpec schema_version")
        return cls(
            software_id=str(data["software_id"]),
            packages=tuple(str(x) for x in data["packages"]),
            target_roles=tuple(str(x) for x in data.get("target_roles", ("host",))),
            target_asns=tuple(int(x) for x in data.get("target_asns", ())),
            target_nodes=tuple(str(x) for x in data.get("target_nodes", ())),
            capabilities=tuple(str(x) for x in data.get("capabilities", ())),
            managed_files=tuple(
                ManagedFileSpec.from_dict(x) for x in data.get("managed_files", ())
            ),
            fault_profiles=tuple(
                SoftwareFaultProfile.from_dict(x)
                for x in data.get("fault_profiles", ())
            ),
            schema_version=SOFTWARE_SPEC_VERSION,
        )


BUILTIN_ROUTER_SOFTWARE = SoftwareSpec(
    software_id="iptables",
    packages=("iptables",),
    target_roles=("router",),
    capabilities=("firewall.iptables.v1",),
)


def validate_software_spec(spec: SoftwareSpec) -> None:
    if spec.schema_version != SOFTWARE_SPEC_VERSION or not ID_PATTERN.fullmatch(spec.software_id):
        raise ValueError("invalid SoftwareSpec identity")
    if not spec.packages or len(spec.packages) > 32:
        raise ValueError("SoftwareSpec requires 1-32 packages")
    if len(set(spec.packages)) != len(spec.packages) or any(
        not PACKAGE_PATTERN.fullmatch(item) for item in spec.packages
    ):
        raise ValueError("SoftwareSpec contains an invalid or duplicate apt package")
    if not spec.target_roles or not set(spec.target_roles) <= ALLOWED_ROLES:
        raise ValueError("SoftwareSpec target_roles must select router and/or host")
    if len(set(spec.target_roles)) != len(spec.target_roles):
        raise ValueError("SoftwareSpec target_roles must be unique")
    if len(set(spec.target_asns)) != len(spec.target_asns) or any(
        item < 1 or item > 4294967294 for item in spec.target_asns
    ):
        raise ValueError("SoftwareSpec target_asns are invalid")
    if len(set(spec.target_nodes)) != len(spec.target_nodes) or any(
        not NODE_PATTERN.fullmatch(item) for item in spec.target_nodes
    ):
        raise ValueError("SoftwareSpec target_nodes are invalid")
    if len(set(spec.capabilities)) != len(spec.capabilities) or any(
        not CAPABILITY_PATTERN.fullmatch(item) for item in spec.capabilities
    ):
        raise ValueError("SoftwareSpec capabilities are invalid")
    if len(spec.managed_files) > 16:
        raise ValueError("SoftwareSpec may manage at most 16 files")
    file_by_path = {}
    for item in spec.managed_files:
        if item.path in file_by_path or not _safe_absolute_path(item.path, MANAGED_FILE_ROOTS):
            raise ValueError("SoftwareSpec managed file path is unsafe or duplicated")
        if not MODE_PATTERN.fullmatch(item.mode) or len(item.content.encode("utf-8")) > 131072:
            raise ValueError("SoftwareSpec managed file mode/content is invalid")
        file_by_path[item.path] = item
    profile_ids = set()
    for profile in spec.fault_profiles:
        if (
            not ID_PATTERN.fullmatch(profile.profile_id)
            or profile.profile_id in profile_ids
            or not CAPABILITY_PATTERN.fullmatch(profile.fault_type)
            or not profile.fault_type.startswith("software.")
        ):
            raise ValueError("SoftwareSpec fault profile identity is invalid or duplicated")
        profile_ids.add(profile.profile_id)
        params = profile.parameters
        if profile.fault_type == "software.config.replace":
            if set(params) != {"path", "healthy_value", "faulty_value"}:
                raise ValueError("config.replace profile has invalid parameters")
            path = str(params["path"])
            healthy, faulty = str(params["healthy_value"]), str(params["faulty_value"])
            managed = file_by_path.get(path)
            if (
                not managed or not healthy or not faulty or healthy == faulty
                or managed.content.count(healthy) != 1 or faulty in managed.content
            ):
                raise ValueError("config.replace profile does not match one managed baseline")
        elif profile.fault_type == "software.executable.disabled":
            if set(params) != {"path", "expected_mode"}:
                raise ValueError("executable.disabled profile has invalid parameters")
            if (
                not _safe_absolute_path(str(params["path"]), EXECUTABLE_ROOTS)
                or not MODE_PATTERN.fullmatch(str(params["expected_mode"]))
                or str(params["expected_mode"]).endswith(("0", "2", "4", "6"))
            ):
                raise ValueError("executable.disabled profile path/mode is unsafe")


def validate_software_specs(
    specs: Sequence[SoftwareSpec], *, asns: Sequence[int], hosts_per_as: int
) -> None:
    if len(specs) > 32 or len({item.software_id for item in specs}) != len(specs):
        raise ValueError("topology software ids must be unique and limited to 32")
    allowed_asns = set(asns)
    assets = [
        (asn, role, node_name)
        for asn in asns
        for role, node_name in (
            [("router", "router0")]
            + [("host", f"host{index}") for index in range(hosts_per_as)]
        )
    ]
    managed_file_owner = {}
    for spec in specs:
        validate_software_spec(spec)
        if spec.target_asns and not set(spec.target_asns) <= allowed_asns:
            raise ValueError("SoftwareSpec targets an ASN outside the topology")
        for node in spec.target_nodes:
            if node.startswith("host") and int(node[4:]) >= hosts_per_as:
                raise ValueError("SoftwareSpec targets a host outside the topology")
        matched = [
            asset for asset in assets
            if node_matches(
                spec, role=asset[1], asn=asset[0], node_name=asset[2]
            )
        ]
        if not matched:
            raise ValueError("SoftwareSpec selector matches no topology assets")
        for asn, role, node_name in matched:
            for managed in spec.managed_files:
                key = (asn, role, node_name, managed.path)
                if key in managed_file_owner:
                    raise ValueError(
                        "SoftwareSpec managed file conflict between "
                        f"{managed_file_owner[key]} and {spec.software_id}"
                    )
                managed_file_owner[key] = spec.software_id


def node_matches(spec: SoftwareSpec, *, role: str, asn: int, node_name: str) -> bool:
    return (
        role in spec.target_roles
        and (not spec.target_asns or asn in spec.target_asns)
        and (not spec.target_nodes or node_name in spec.target_nodes)
    )


def resolved_packages(spec: SoftwareSpec) -> Tuple[str, ...]:
    support = ("python3-minimal",) if any(
        item.fault_type == "software.config.replace" for item in spec.fault_profiles
    ) else ()
    return tuple(dict.fromkeys((*spec.packages, *support)))


def capability_entry(spec: SoftwareSpec, *, source: str = "declared") -> Dict[str, Any]:
    return {
        "schema_version": SOFTWARE_SPEC_VERSION,
        "software_id": spec.software_id,
        "source": source,
        "packages": list(spec.packages),
        "resolved_packages": list(resolved_packages(spec)),
        "capabilities": list(spec.capabilities),
        "managed_files": [
            {"path": item.path, "mode": item.mode} for item in spec.managed_files
        ],
        "fault_profiles": [asdict(item) for item in spec.fault_profiles],
    }

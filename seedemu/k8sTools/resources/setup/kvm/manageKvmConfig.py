#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
from pathlib import Path
from typing import Any

import yaml


SETUP_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path.home() / "k8s"
SETUP_DATA_DIR = SETUP_DIR


def expand_path(value: str) -> str:
    return str(Path(os.path.expandvars(os.path.expanduser(value))).resolve())


def expand_path_list(value: Any) -> str:
    """Expand a YAML scalar/list into the shell path-list used by KVM scripts."""
    if value is None:
        return str((Path.home() / "k8s/output").resolve())
    if isinstance(value, list):
        return " ".join(expand_path(str(item)) for item in value if str(item).strip())
    text = str(value).strip()
    if not text:
        return ""
    return " ".join(expand_path(part) for part in text.split())


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid config root in {path}: expected mapping")
    normalize_config(data)
    return data


def normalize_config(data: dict[str, Any]) -> None:
    """Accept new camelCase YAML while preserving older internal lookups."""
    if "clusterName" in data and "cluster_name" not in data:
        data["cluster_name"] = data["clusterName"]
    for section in ("master", "workers"):
        value = data.get(section)
        if isinstance(value, dict):
            aliases = {"memoryMb": "memory_mb", "diskGb": "disk_gb", "namePrefix": "name_prefix"}
            for new_key, old_key in aliases.items():
                if new_key in value and old_key not in value:
                    value[old_key] = value[new_key]
    kvm = data.get("kvm")
    if isinstance(kvm, dict):
        aliases = {
            "storageDir": "storage_dir",
            "diskDir": "disk_dir",
            "cloudInitDir": "cloud_init_dir",
            "baseImagePath": "base_image_path",
            "legacyBaseImagePath": "legacy_base_image_path",
            "baseImageUrl": "base_image_url",
            "ubuntuSeries": "ubuntu_series",
            "bootTimeoutSeconds": "boot_timeout_seconds",
            "allowExisting": "allow_existing",
            "skipK3sConfig": "skip_k3s_config",
        }
        for new_key, old_key in aliases.items():
            if new_key in kvm and old_key not in kvm:
                kvm[old_key] = kvm[new_key]
    outputs = data.get("outputs")
    if isinstance(outputs, dict):
        aliases = {"tmpDir": "tmp_dir", "k3sConfig": "k3s_config", "kvmState": "kvm_state", "runningConfig": "running_config"}
        for new_key, old_key in aliases.items():
            if new_key in outputs and old_key not in outputs:
                outputs[old_key] = outputs[new_key]


def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        for candidate in (part, _snakeCase(part), _camelCase(part)):
            if candidate in cur:
                cur = cur[candidate]
                break
        else:
            return default
    return cur


def _snakeCase(value: str) -> str:
    """Return a snake_case spelling for one YAML path component."""
    return re.sub(r"(?<!^)([A-Z])", r"_\1", value).lower()


def _camelCase(value: str) -> str:
    """Return a camelCase spelling for one YAML path component."""
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def ubuntu_image_defaults(data: dict[str, Any]) -> tuple[str, str]:
    series = str(get_nested(data, "kvm.ubuntu_series", "jammy"))
    if series == "jammy":
        return (
            "https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img",
            str(SETUP_DIR / "base/jammy-server-cloudimg-amd64.img"),
        )
    if series == "noble":
        return (
            "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img",
            str(SETUP_DIR / "base/noble-server-cloudimg-amd64.img"),
        )
    raise SystemExit(f"Unsupported kvm.ubuntu_series: {series}")


def default_seedemu_docker_dir() -> str:
    """Return a likely source-tree path containing SeedEMU base/router images."""
    candidates = []
    for base in (SETUP_DIR, *SETUP_DIR.parents):
        candidates.append(base / "docker_images/multiarch")
    candidates.extend(
        [
            Path.home() / "seed-emulator/docker_images/multiarch",
            Path.home() / "seed-emulator-k8s-new/docker_images/multiarch",
            Path.home() / "k8s/seed-emulator/docker_images/multiarch",
        ]
    )
    for candidate in candidates:
        if (candidate / "seedemu-base").is_dir() and (candidate / "seedemu-router").is_dir():
            return str(candidate.resolve())
    return str(candidates[0].expanduser().resolve())


def normalize_node(node: dict[str, Any], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    out = dict(defaults)
    out.update(node)
    required = ["name", "role", "ip", "mac", "vcpus", "memory_mb", "disk_gb"]
    missing = [key for key in required if key not in out or out[key] in ("", None)]
    if missing:
        raise SystemExit(f"Node is missing required fields {missing}: {out}")
    out["role"] = "master" if str(out["role"]) in {"master", "control-plane"} else "worker"
    out["vcpus"] = int(out["vcpus"])
    out["memory_mb"] = int(out["memory_mb"])
    out["disk_gb"] = int(out["disk_gb"])
    return out


def read_existing_nodes(path: str | None) -> list[dict[str, str]]:
    if not path:
        return []
    existing_path = Path(path)
    if not existing_path.exists():
        return []
    out: list[dict[str, str]] = []
    with existing_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            while len(parts) < 3:
                parts.append("")
            name, ip, mac = [part.strip() for part in parts[:3]]
            if name or ip or mac:
                out.append({"name": name, "ip": ip, "mac": mac.lower()})
    return out


def split_ipv4(ip: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"(\d+\.\d+\.\d+)\.(\d+)", ip)
    if not match:
        return None
    octet = int(match.group(2))
    if octet < 1 or octet > 254:
        return None
    return match.group(1), octet


def mac_suffix(mac: str, prefix: str) -> int | None:
    mac = mac.lower()
    prefix = prefix.lower()
    if not mac.startswith(prefix + ":"):
        return None
    suffix = mac.rsplit(":", 1)[-1]
    try:
        value = int(suffix, 16)
    except ValueError:
        return None
    if value < 0 or value > 255:
        return None
    return value


def next_vm_name(base: str, used_names: set[str], first_number: int | None = None) -> str:
    if first_number is None and base not in used_names:
        used_names.add(base)
        return base
    number = first_number or 2
    while True:
        candidate = f"{base}{number}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        number += 1


def next_worker_number(name_prefix: str, used_names: set[str]) -> int:
    pattern = re.compile(rf"^{re.escape(name_prefix)}(\d+)$")
    highest = 0
    for name in used_names:
        match = pattern.fullmatch(name)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def next_ip(ip_prefix: str, start: int, used_ips: set[str]) -> str:
    highest = start - 1
    for ip in used_ips:
        parsed = split_ipv4(ip)
        if parsed and parsed[0] == ip_prefix and parsed[1] >= start:
            highest = max(highest, parsed[1])
    candidate = highest + 1
    while candidate <= 254:
        ip = f"{ip_prefix}.{candidate}"
        if ip not in used_ips:
            used_ips.add(ip)
            return ip
        candidate += 1
    raise SystemExit(f"No available IPv4 address left in {ip_prefix}.0/24 starting at {start}")


def next_mac(mac_prefix: str, start: int, used_macs: set[str]) -> str:
    highest = start - 1
    for mac in used_macs:
        suffix = mac_suffix(mac, mac_prefix)
        if suffix is not None and suffix >= start:
            highest = max(highest, suffix)
    candidate = highest + 1
    while candidate <= 255:
        mac = f"{mac_prefix.lower()}:{candidate:02x}"
        if mac not in used_macs:
            used_macs.add(mac)
            return mac
        candidate += 1
    raise SystemExit(f"No available MAC suffix left for prefix {mac_prefix} starting at {start:02x}")


def auto_node(
    role: str,
    cfg: dict[str, Any],
    used_names: set[str],
    used_ips: set[str],
    used_macs: set[str],
    *,
    default_name: str | None = None,
    default_name_prefix: str | None = None,
    worker_number: int | None = None,
    default_ip_prefix: str,
    default_ip_start: int,
    default_mac_prefix: str,
    default_mac_start: int,
) -> dict[str, Any]:
    required = ["vcpus", "memory_mb", "disk_gb"]
    missing = [key for key in required if cfg.get(key) in ("", None)]
    if missing:
        raise SystemExit(f"{role} config is missing required fields {missing}: {cfg}")

    if cfg.get("name"):
        name = str(cfg["name"])
        if name in used_names:
            raise SystemExit(f"Configured {role} name conflicts with existing/planned VM: {name}")
        used_names.add(name)
    elif role == "master":
        name = next_vm_name(str(default_name or "seed-k3s-master"), used_names)
    else:
        prefix = str(default_name_prefix or "seed-k3s-worker")
        number = worker_number or next_worker_number(prefix, used_names)
        name = next_vm_name(prefix, used_names, first_number=number)

    ip = str(cfg["ip"]) if cfg.get("ip") else next_ip(
        str(cfg.get("ip_prefix", default_ip_prefix)),
        int(cfg.get("ip_start", default_ip_start)),
        used_ips,
    )
    if cfg.get("ip") and ip in used_ips:
        raise SystemExit(f"Configured {role} IP conflicts with existing/planned VM: {ip}")
    used_ips.add(ip)

    mac = str(cfg["mac"]).lower() if cfg.get("mac") else next_mac(
        str(cfg.get("mac_prefix", default_mac_prefix)),
        int(cfg.get("mac_start", default_mac_start)),
        used_macs,
    )
    if cfg.get("mac") and mac in used_macs:
        raise SystemExit(f"Configured {role} MAC conflicts with existing/planned VM: {mac}")
    used_macs.add(mac)

    return normalize_node(
        {
            "name": name,
            "role": role,
            "ip": ip,
            "mac": mac,
            "vcpus": cfg["vcpus"],
            "memory_mb": cfg["memory_mb"],
            "disk_gb": cfg["disk_gb"],
        }
    )


def nodes(data: dict[str, Any], existing: list[dict[str, str]] | None = None) -> list[dict[str, Any]]:
    existing = existing or []
    used_names = {item["name"] for item in existing if item.get("name")}
    used_ips = {item["ip"] for item in existing if item.get("ip")}
    used_macs = {item["mac"].lower() for item in existing if item.get("mac")}
    explicit = data.get("nodes")
    if explicit:
        out = [normalize_node(item) for item in explicit]
    else:
        out = []
        master_cfg = data.get("master")
        if "master" in data and master_cfg is not None:
            out.append(
                auto_node(
                    "master",
                    master_cfg or {},
                    used_names,
                    used_ips,
                    used_macs,
                    default_name=str(get_nested(data, "defaults.master_name", "seed-k3s-master")),
                    default_ip_prefix=str(get_nested(data, "defaults.ip_prefix", "192.168.122")),
                    default_ip_start=int(get_nested(data, "defaults.master_ip_start", 110)),
                    default_mac_prefix=str(get_nested(data, "defaults.mac_prefix", "52:54:00:64:10")),
                    default_mac_start=int(get_nested(data, "defaults.master_mac_start", 0x10)),
                )
            )
        workers_cfg = data.get("workers") or {}
        if "workers" in data and data.get("workers") is not None and "count" not in workers_cfg:
            raise SystemExit("workers.count is required when workers is configured")
        count = int(workers_cfg.get("count", 0))
        if count < 0:
            raise SystemExit("workers.count must be >= 0")
        name_prefix = str(workers_cfg.get("name_prefix", get_nested(data, "defaults.worker_name_prefix", "seed-k3s-worker")))
        next_number = next_worker_number(name_prefix, used_names)
        for idx in range(1, count + 1):
            out.append(
                auto_node(
                    "worker",
                    workers_cfg,
                    used_names,
                    used_ips,
                    used_macs,
                    default_name_prefix=name_prefix,
                    worker_number=next_number + idx - 1,
                    default_ip_prefix=str(workers_cfg.get("ip_prefix", get_nested(data, "defaults.ip_prefix", "192.168.122"))),
                    default_ip_start=int(workers_cfg.get("ip_start", get_nested(data, "defaults.worker_ip_start", 111))),
                    default_mac_prefix=str(workers_cfg.get("mac_prefix", get_nested(data, "defaults.mac_prefix", "52:54:00:64:10"))),
                    default_mac_start=int(workers_cfg.get("mac_start", get_nested(data, "defaults.worker_mac_start", 0x11))),
                )
            )
        if not out:
            raise SystemExit("No VMs requested: provide master and/or workers.count > 0")

    masters = [node for node in out if node["role"] == "master"]
    if len(masters) > 1:
        raise SystemExit(f"Expected at most one master node, got {len(masters)}")
    names = [node["name"] for node in out]
    ips = [node["ip"] for node in out]
    macs = [node["mac"] for node in out]
    for label, values in (("name", names), ("ip", ips), ("mac", macs)):
        dup = sorted({value for value in values if values.count(value) > 1})
        if dup:
            raise SystemExit(f"Duplicate node {label}: {dup}")
    return out


def master_node(data: dict[str, Any]) -> dict[str, Any]:
    return [node for node in nodes(data) if node["role"] == "master"][0]


def optional_master_node(data: dict[str, Any], existing: list[dict[str, str]] | None = None) -> dict[str, Any] | None:
    masters = [node for node in nodes(data, existing) if node["role"] == "master"]
    return masters[0] if masters else None


def install_version(data: dict[str, Any]) -> str:
    version = str(get_nested(data, "k3s.version", "v1.28.5+k3s1"))
    artifact = str(get_nested(data, "k3s.artifact_url", "https://rancher-mirror.rancher.cn/k3s"))
    configured = get_nested(data, "k3s.install_version")
    if configured:
        return str(configured)
    if "rancher-mirror.rancher.cn/k3s" in artifact:
        return version.replace("+", "-")
    return version


def shell_env(args: argparse.Namespace) -> None:
    kvm_env(args)


def kvm_env(args: argparse.Namespace) -> None:
    data = load_config(args.config)
    base_url, base_path = ubuntu_image_defaults(data)
    existing = read_existing_nodes(args.existing_tsv)
    master = optional_master_node(data, existing)
    cluster_name = str(data.get("cluster_name", "seedemu-k3s"))
    legacy_base_image = get_nested(
        data,
        "kvm.legacy_base_image_path",
        REPO_ROOT / f"output/kvm_lab/base/{Path(base_path).name}",
    )
    storage_dir = expand_path(str(get_nested(data, "kvm.storage_dir", SETUP_DIR)))
    disk_dir = expand_path(str(get_nested(data, "kvm.disk_dir", SETUP_DATA_DIR / "disks")))
    cloud_init_dir = expand_path(str(get_nested(data, "kvm.cloud_init_dir", SETUP_DIR / "cloud-init")))
    values = {
        "clusterName": cluster_name,
        "kvmNetwork": get_nested(data, "kvm.network", "default"),
        "kvmStorageDir": storage_dir,
        "kvmDiskDir": disk_dir,
        "kvmCloudInitDir": cloud_init_dir,
        "kvmUbuntuSeries": get_nested(data, "kvm.ubuntu_series", "jammy"),
        "kvmBaseImageUrl": get_nested(data, "kvm.base_image_url", base_url),
        "kvmBaseImagePath": expand_path(str(get_nested(data, "kvm.base_image_path", base_path))),
        "kvmLegacyBaseImagePath": expand_path(str(legacy_base_image)) if legacy_base_image else "",
        "kvmBaseImageSearchDirs": expand_path_list(get_nested(data, "kvm.base_image_search_dirs")),
        "kvmBootTimeoutSeconds": get_nested(data, "kvm.boot_timeout_seconds", 300),
        "kvmAllowExisting": str(get_nested(data, "kvm.allow_existing", False)).lower(),
        "kvmSkipK3sConfig": str(get_nested(data, "kvm.skip_k3s_config", False)).lower(),
        "sshUser": get_nested(data, "ssh.user", "ubuntu"),
        "sshKey": expand_path(str(get_nested(data, "ssh.key", "~/.ssh/id_ed25519"))),
        "masterName": master["name"] if master else "",
        "masterIp": master["ip"] if master else "",
        "outputK3sConfig": expand_path(str(get_nested(data, "outputs.k3s_config", SETUP_DIR / "configK3s.yaml"))),
        "outputKvmState": expand_path(str(get_nested(data, "outputs.kvm_state", SETUP_DIR / "kvmState.yaml"))),
        "outputKubeconfig": expand_path(str(get_nested(data, "outputs.kubeconfig", SETUP_DIR / f"{cluster_name}.kubeconfig.yaml"))),
        "outputInventory": expand_path(str(get_nested(data, "outputs.inventory", SETUP_DIR / f"{cluster_name}.inventory.yaml"))),
        "seedEmulatorDockerDir": expand_path(
            str(
                get_nested(
                    data,
                    "seedemu.dockerImagesDir",
                    get_nested(data, "seedemu.docker_images_dir", default_seedemu_docker_dir()),
                )
            )
        ),
    }
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def nodes_tsv(args: argparse.Namespace) -> None:
    for node in nodes(load_config(args.config), read_existing_nodes(args.existing_tsv)):
        print(
            "\t".join(
                str(node[key])
                for key in ("name", "role", "ip", "mac", "vcpus", "memory_mb", "disk_gb")
            )
        )


def write_inventory(args: argparse.Namespace) -> None:
    data = load_config(args.config)
    cluster_name = str(data.get("cluster_name", "seedemu-k3s"))
    master = master_node(data)
    output = Path(args.output or expand_path(str(get_nested(data, "outputs.inventory", SETUP_DIR / f"{cluster_name}.inventory.yaml"))))
    payload = {
        "cluster_name": cluster_name,
        "reference_cluster": False,
        "runtime": "k3s",
        "max_validated_topology_size": int(get_nested(data, "max_validated_topology_size", 12000)),
        "k3s": {
            "cluster_cidr": get_nested(data, "k3s.cluster_cidr", "10.42.0.0/16"),
            "service_cidr": get_nested(data, "k3s.service_cidr", "10.43.0.0/16"),
            "node_cidr_mask_size_ipv4": int(get_nested(data, "k3s.node_cidr_mask_size_ipv4", 20)),
            "max_pods": int(get_nested(data, "k3s.max_pods", 4000)),
        },
        "network_tuning": {
            "cni0_hash_max": int(get_nested(data, "tuning.cni0_hash_max", 16384)),
            "user_max_net_namespaces": int(get_nested(data, "tuning.user_max_net_namespaces", 65536)),
            "neigh_gc_thresh1": int(get_nested(data, "tuning.neigh_gc_thresh1", 1048576)),
            "neigh_gc_thresh2": int(get_nested(data, "tuning.neigh_gc_thresh2", 4194304)),
            "neigh_gc_thresh3": int(get_nested(data, "tuning.neigh_gc_thresh3", 8388608)),
            "netdev_max_backlog": int(get_nested(data, "tuning.netdev_max_backlog", 1000000)),
            "optmem_max": int(get_nested(data, "tuning.optmem_max", 25165824)),
        },
        "ssh": {
            "user": get_nested(data, "ssh.user", "ubuntu"),
            "default_key_path": get_nested(data, "ssh.key", "~/.ssh/id_ed25519"),
        },
        "registry": {
            "host": get_nested(data, "registry.host", master["ip"]),
            "port": int(get_nested(data, "registry.port", 5000)),
        },
        "cni": {"default_master_interface": get_nested(data, "cni.default_master_interface", "ens2")},
        "nodes": [
            {
                "name": node["name"],
                "role": node["role"],
                "management_ip": node["ip"],
                "runtime": "k3s",
                "resources": {
                    "vcpus": node["vcpus"],
                    "memory_mb": node["memory_mb"],
                    "disk_gb": node["disk_gb"],
                },
                "labels": {"kubernetes.io/hostname": node["name"]},
            }
            for node in nodes(data)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(output)


def read_nodes_tsv(path: str) -> list[dict[str, Any]]:
    """Read a transient node TSV produced by nodes-tsv.

    Args:
        path: TSV path with name, role, ip, mac, vcpus, memory_mb, disk_gb.
    """
    out: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            parts = raw.split("\t")
            while len(parts) < 7:
                parts.append("")
            name, role, ip, mac, vcpus, memory_mb, disk_gb = parts[:7]
            out.append(
                {
                    "name": name,
                    "role": role,
                    "ip": ip,
                    "mac": mac,
                    "vcpus": int(vcpus or 0),
                    "memoryMb": int(memory_mb or 0),
                    "diskGb": int(disk_gb or 0),
                }
            )
    return out


def to_k3s_node_payload(node: dict[str, Any]) -> dict[str, Any]:
    """Normalize KVM node records to configK3s.yaml node shape.

    Args:
        node: Node mapping from kvm.yaml expansion or transient TSV.
    """
    return {
        "name": node["name"],
        "role": node["role"],
        "ip": node["ip"],
        "vcpus": int(node.get("vcpus") or 0),
        "memoryMb": int(node.get("memoryMb") or node.get("memory_mb") or 0),
        "diskGb": int(node.get("diskGb") or node.get("disk_gb") or 0),
        "ssh": {
            "user": node.get("sshUser", ""),
            "key": node.get("sshKey", ""),
        },
    }


def to_kvm_state_node_payload(node: dict[str, Any]) -> dict[str, Any]:
    """Normalize KVM node records to kvmState.yaml node shape.

    Args:
        node: Node mapping from kvm.yaml expansion or transient TSV.
    """
    return {
        "name": node["name"],
        "role": node["role"],
        "ip": node["ip"],
        "mac": node.get("mac", ""),
        "vcpus": int(node.get("vcpus") or 0),
        "memoryMb": int(node.get("memoryMb") or node.get("memory_mb") or 0),
        "diskGb": int(node.get("diskGb") or node.get("disk_gb") or 0),
    }


def k3s_passthrough_sections(data: dict[str, Any], cluster_name: str) -> dict[str, Any]:
    """Return kvm.yaml sections that must survive into configK3s.yaml.

    Args:
        data: Normalized kvm.yaml mapping.
        cluster_name: Effective cluster name used for default output paths.

    KVM creation owns VM resources, but the next K3s stage still needs backend
    selection and output paths. Keep only K3s-facing sections so configK3s.yaml
    stays simple for users and does not repeat CPU/memory/disk settings.
    """
    payload: dict[str, Any] = {}
    for section in ("registry", "k3s", "fabric", "ovn", "cni", "tuning", "seedemu"):
        value = data.get(section)
        if isinstance(value, dict) and value:
            payload[section] = value

    outputs = data.get("outputs")
    if isinstance(outputs, dict):
        output_payload: dict[str, Any] = {}
        tmp_dir = get_nested(data, "outputs.tmp_dir")
        kubeconfig = get_nested(data, "outputs.kubeconfig")
        inventory = get_nested(data, "outputs.inventory")
        if tmp_dir:
            output_payload["tmpDir"] = expand_path(str(tmp_dir))
        if kubeconfig:
            output_payload["kubeconfig"] = expand_path(str(kubeconfig))
        else:
            output_payload["kubeconfig"] = expand_path(str(SETUP_DIR / f"{cluster_name}.kubeconfig.yaml"))
        if inventory:
            output_payload["inventory"] = expand_path(str(inventory))
        else:
            output_payload["inventory"] = expand_path(str(SETUP_DIR / f"{cluster_name}.inventory.yaml"))
        payload["outputs"] = output_payload
    return payload


def write_k3s_config(args: argparse.Namespace) -> None:
    """Write configK3s.yaml after KVM node names/IPs are resolved.

    Args:
        args.config: Source kvm.yaml.
        args.nodes_tsv: Transient node TSV generated by createKvmVms.py.
        args.output: Destination configK3s.yaml path.
    """
    data = load_config(args.config)
    cluster_name = str(data.get("cluster_name", "seedemu-k3s"))
    ssh_user = str(get_nested(data, "ssh.user", "ubuntu"))
    ssh_key = expand_path(str(get_nested(data, "ssh.key", "~/.ssh/id_ed25519")))
    resolved_nodes = [
        to_k3s_node_payload({**node, "sshUser": ssh_user, "sshKey": ssh_key})
        for node in (read_nodes_tsv(args.nodes_tsv) if args.nodes_tsv else nodes(data))
    ]
    masters = [node for node in resolved_nodes if node["role"] == "master"]
    if len(masters) != 1:
        raise SystemExit(f"Expected exactly one master in configK3s.yaml nodes, got {len(masters)}")
    output = Path(args.output or expand_path(str(get_nested(data, "outputs.k3s_config", SETUP_DIR / "configK3s.yaml"))))
    payload = {
        "clusterName": cluster_name,
        "nodes": resolved_nodes,
    }
    payload.update(k3s_passthrough_sections(data, cluster_name))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(output)


def write_kvm_state(args: argparse.Namespace) -> None:
    """Write kvmState.yaml after KVM node names/IPs are resolved.

    Args:
        args.config: Source kvm.yaml.
        args.nodes_tsv: Transient node TSV generated by createKvmVms.py.
        args.output: Destination kvmState.yaml path.
    """
    data = load_config(args.config)
    cluster_name = str(data.get("cluster_name", "seedemu-k3s"))
    resolved_nodes = [
        to_kvm_state_node_payload(node)
        for node in (read_nodes_tsv(args.nodes_tsv) if args.nodes_tsv else nodes(data))
    ]
    output = Path(args.output or expand_path(str(get_nested(data, "outputs.kvm_state", SETUP_DIR / "kvmState.yaml"))))
    payload = {
        "clusterName": cluster_name,
        "kvm": {
            "network": get_nested(data, "kvm.network", "default"),
            "diskDir": expand_path(str(get_nested(data, "kvm.disk_dir", SETUP_DATA_DIR / "disks"))),
            "cloudInitDir": expand_path(str(get_nested(data, "kvm.cloud_init_dir", SETUP_DIR / "cloud-init"))),
        },
        "outputs": {
            "k3sConfig": expand_path(str(get_nested(data, "outputs.k3s_config", SETUP_DIR / "configK3s.yaml"))),
            "tmpDir": expand_path(str(get_nested(data, "outputs.tmp_dir", SETUP_DIR / "tmp"))),
            "kubeconfig": expand_path(str(get_nested(data, "outputs.kubeconfig", SETUP_DIR / f"{cluster_name}.kubeconfig.yaml"))),
            "inventory": expand_path(str(get_nested(data, "outputs.inventory", SETUP_DIR / f"{cluster_name}.inventory.yaml"))),
        },
        "nodes": resolved_nodes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(output)


def load_kvm_state(path: str) -> dict[str, Any]:
    """Load kvmState.yaml and validate its root mapping."""
    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid kvmState.yaml root: {path}")
    if not isinstance(data.get("nodes"), list):
        raise SystemExit(f"Invalid kvmState.yaml nodes list: {path}")
    return data


def kvm_state_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return normalized nodes from kvmState.yaml."""
    return [to_kvm_state_node_payload(node) for node in data["nodes"]]


def state_nodes_tsv(args: argparse.Namespace) -> None:
    """Print kvmState.yaml nodes as TSV."""
    for node in kvm_state_nodes(load_kvm_state(args.state)):
        print(
            "\t".join(
                str(node[key])
                for key in ("name", "role", "ip", "mac", "vcpus", "memoryMb", "diskGb")
            )
        )


def state_vars(args: argparse.Namespace) -> None:
    """Print shell assignments derived from kvmState.yaml."""
    data = load_kvm_state(args.state)
    cluster_name = str(data.get("clusterName") or data.get("cluster_name") or "seedemu-k3s")
    values = {
        "clusterName": cluster_name,
        "kvmNetwork": get_nested(data, "kvm.network", "default"),
        "kvmDiskDir": expand_path(str(get_nested(data, "kvm.diskDir", SETUP_DATA_DIR / "disks"))),
        "kvmCloudInitDir": expand_path(str(get_nested(data, "kvm.cloudInitDir", SETUP_DIR / "cloud-init"))),
        "outputK3sConfig": expand_path(str(get_nested(data, "outputs.k3sConfig", SETUP_DIR / "configK3s.yaml"))),
        "outputKubeconfig": expand_path(str(get_nested(data, "outputs.kubeconfig", SETUP_DIR / f"{cluster_name}.kubeconfig.yaml"))),
        "outputInventory": expand_path(str(get_nested(data, "outputs.inventory", SETUP_DIR / f"{cluster_name}.inventory.yaml"))),
    }
    for key, value in values.items():
        print(f"{key}={shlex.quote(str(value))}")


def validate_kvm_state(args: argparse.Namespace) -> None:
    """Validate that an existing kvmState.yaml still matches kvm.yaml.

    Args:
        args.config: Source kvm.yaml.
        args.state: Existing kvmState.yaml that createKvmVms.py may reuse.
    """
    data = load_config(args.config)
    expected = nodes(data)
    resolved = kvm_state_nodes(load_kvm_state(args.state))

    def signature(items: list[dict[str, Any]]) -> list[tuple[str, int, int, int]]:
        result = []
        for item in items:
            result.append(
                (
                    str(item["role"]),
                    int(item.get("vcpus") or 0),
                    int(item.get("memoryMb") or item.get("memory_mb") or 0),
                    int(item.get("diskGb") or item.get("disk_gb") or 0),
                )
            )
        return sorted(result)

    if signature(expected) != signature(resolved):
        raise SystemExit(
            "kvmState.yaml node plan does not match current kvm.yaml. "
            f"expected={signature(expected)} resolved={signature(resolved)}"
        )


def write_ansible_inventory(args: argparse.Namespace) -> None:
    data = load_config(args.config)
    all_nodes = nodes(data)
    master = [node for node in all_nodes if node["role"] == "master"][0]
    workers = [node for node in all_nodes if node["role"] == "worker"]
    payload = {
        "all": {
            "vars": {
                "ansible_user": get_nested(data, "ssh.user", "ubuntu"),
                "ansible_ssh_private_key_file": expand_path(str(get_nested(data, "ssh.key", "~/.ssh/id_ed25519"))),
                "k3s_version": get_nested(data, "k3s.version", "v1.28.5+k3s1"),
                "k3s_install_version": install_version(data),
                "seed_registry_host": get_nested(data, "registry.host", master["ip"]),
                "seed_registry_port": get_nested(data, "registry.port", 5000),
                "seed_docker_io_mirror_endpoint": get_nested(data, "registry.docker_io_mirror_endpoint", "https://docker.m.daocloud.io"),
                "seed_k3s_artifact_url": get_nested(data, "k3s.artifact_url", "https://rancher-mirror.rancher.cn/k3s"),
                "seed_cni_master_interface": get_nested(data, "cni.default_master_interface", "ens2"),
                "seed_k3s_cluster_cidr": get_nested(data, "k3s.cluster_cidr", "10.42.0.0/16"),
                "seed_k3s_service_cidr": get_nested(data, "k3s.service_cidr", "10.43.0.0/16"),
                "seed_k3s_node_cidr_mask_size_ipv4": get_nested(data, "k3s.node_cidr_mask_size_ipv4", 20),
                "seed_k3s_max_pods": get_nested(data, "k3s.max_pods", 4000),
                "seed_k3s_force_reinstall": bool(get_nested(data, "k3s.force_reinstall", False)),
            },
            "children": {
                "master": {
                    "hosts": {
                        master["name"]: {
                            "ansible_host": master["ip"],
                            "k3s_role": "server",
                            "seedemu_as_group": "master",
                        }
                    }
                },
                "workers": {
                    "hosts": {
                        node["name"]: {
                            "ansible_host": node["ip"],
                            "k3s_role": "agent",
                            "seedemu_as_group": f"worker-{idx}",
                        }
                        for idx, node in enumerate(workers, start=1)
                    }
                },
            },
        }
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("shell-vars").set_defaults(func=shell_env)
    kvm_env_parser = sub.add_parser("kvm-vars")
    kvm_env_parser.add_argument("--existing-tsv")
    kvm_env_parser.set_defaults(func=kvm_env)
    nodes_parser = sub.add_parser("nodes-tsv")
    nodes_parser.add_argument("--existing-tsv")
    nodes_parser.set_defaults(func=nodes_tsv)
    inv = sub.add_parser("write-inventory")
    inv.add_argument("--output")
    inv.set_defaults(func=write_inventory)
    k3s = sub.add_parser("write-k3s-config")
    k3s.add_argument("--nodes-tsv")
    k3s.add_argument("--output")
    k3s.set_defaults(func=write_k3s_config)
    state = sub.add_parser("write-kvm-state")
    state.add_argument("--nodes-tsv")
    state.add_argument("--output")
    state.set_defaults(func=write_kvm_state)
    state_nodes = sub.add_parser("state-nodes-tsv")
    state_nodes.add_argument("--state", required=True)
    state_nodes.set_defaults(func=state_nodes_tsv)
    state_env = sub.add_parser("state-vars")
    state_env.add_argument("--state", required=True)
    state_env.set_defaults(func=state_vars)
    validate = sub.add_parser("validate-kvm-state")
    validate.add_argument("--state", required=True)
    validate.set_defaults(func=validate_kvm_state)
    ansible = sub.add_parser("write-ansible-inventory")
    ansible.add_argument("--output", required=True)
    ansible.set_defaults(func=write_ansible_inventory)
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

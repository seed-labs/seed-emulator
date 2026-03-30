#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"cluster inventory must be a mapping: {path}")
    return loaded


def _expand_path(value: str) -> str:
    return str(Path(value).expanduser())


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _pick(nodes: list[dict[str, Any]], role_names: set[str], index: int = 0) -> dict[str, Any] | None:
    matches = [node for node in nodes if str(node.get("role", "")).lower() in role_names]
    if index >= len(matches):
        return None
    return matches[index]


def normalize_inventory(path: Path, name_override: str | None = None) -> dict[str, Any]:
    data = _load_yaml(path)
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        raise ValueError(f"cluster inventory missing nodes list: {path}")

    cluster_name = str(os.environ.get("SEED_K3S_CLUSTER_NAME") or name_override or data.get("cluster_name") or path.stem)
    registry = data.get("registry", {}) if isinstance(data.get("registry"), dict) else {}
    ssh_cfg = data.get("ssh", {}) if isinstance(data.get("ssh"), dict) else {}
    cni_cfg = data.get("cni", {}) if isinstance(data.get("cni"), dict) else {}
    k3s_cfg = data.get("k3s", {}) if isinstance(data.get("k3s"), dict) else {}

    normalized_nodes: list[dict[str, Any]] = []
    for item in nodes:
        if not isinstance(item, dict):
            continue
        normalized_nodes.append(
            {
                "name": str(item.get("name", "")),
                "role": str(item.get("role", "")),
                "management_ip": str(item.get("management_ip", "")),
                "runtime": str(item.get("runtime") or data.get("runtime") or ""),
                "labels": item.get("labels", {}) if isinstance(item.get("labels"), dict) else {},
            }
        )

    if not normalized_nodes:
        raise ValueError(f"cluster inventory has no valid nodes: {path}")

    master = _pick(normalized_nodes, {"master", "control-plane", "controlplane"})
    workers = [node for node in normalized_nodes if node is not master]
    if master is None:
        master = normalized_nodes[0]
        workers = normalized_nodes[1:]

    worker1 = workers[0] if len(workers) > 0 else None
    worker2 = workers[1] if len(workers) > 1 else None

    env_key_name = str(ssh_cfg.get("key_path_env") or "SEED_K3S_SSH_KEY")
    env_key_value = os.environ.get(env_key_name, "").strip()
    default_key_path = str(ssh_cfg.get("default_key_path") or "~/.ssh/id_ed25519")

    master_name = str(os.environ.get("SEED_K3S_MASTER_NAME") or master.get("name") or "")
    master_ip = str(os.environ.get("SEED_K3S_MASTER_IP") or master.get("management_ip") or "")
    worker1_name = str(os.environ.get("SEED_K3S_WORKER1_NAME") or (worker1 or {}).get("name") or "")
    worker1_ip = str(os.environ.get("SEED_K3S_WORKER1_IP") or (worker1 or {}).get("management_ip") or "")
    worker2_name = str(os.environ.get("SEED_K3S_WORKER2_NAME") or (worker2 or {}).get("name") or "")
    worker2_ip = str(os.environ.get("SEED_K3S_WORKER2_IP") or (worker2 or {}).get("management_ip") or "")

    return {
        "cluster_name": cluster_name,
        "inventory_name": path.stem,
        "inventory_path": str(path),
        "reference_cluster": bool(data.get("reference_cluster", False)),
        "runtime": str(data.get("runtime") or ""),
        "max_validated_topology_size": int(data.get("max_validated_topology_size") or 0),
        "registry_host": str(os.environ.get("SEED_REGISTRY_HOST") or registry.get("host") or master_ip or ""),
        "registry_port": int(os.environ.get("SEED_REGISTRY_PORT") or registry.get("port") or 5000),
        "ssh_user": str(os.environ.get("SEED_K3S_USER") or ssh_cfg.get("user") or "ubuntu"),
        "ssh_key_env": env_key_name,
        "ssh_key_path": _expand_path(env_key_value or default_key_path),
        "default_master_interface": str(os.environ.get("SEED_CNI_MASTER_INTERFACE") or cni_cfg.get("default_master_interface") or ""),
        "k3s_cluster_cidr": str(os.environ.get("SEED_K3S_CLUSTER_CIDR") or k3s_cfg.get("cluster_cidr") or ""),
        "k3s_service_cidr": str(os.environ.get("SEED_K3S_SERVICE_CIDR") or k3s_cfg.get("service_cidr") or ""),
        "k3s_node_cidr_mask_size_ipv4": _optional_int(
            os.environ.get("SEED_K3S_NODE_CIDR_MASK_SIZE_IPV4") or k3s_cfg.get("node_cidr_mask_size_ipv4")
        ),
        "k3s_max_pods": _optional_int(os.environ.get("SEED_K3S_MAX_PODS") or k3s_cfg.get("max_pods")),
        "master_name": master_name,
        "master_ip": master_ip,
        "worker1_name": worker1_name,
        "worker1_ip": worker1_ip,
        "worker2_name": worker2_name,
        "worker2_ip": worker2_ip,
        "nodes": normalized_nodes,
        "node_count": len(normalized_nodes),
    }


def export_shell(normalized: dict[str, Any]) -> str:
    exports = {
        "SEED_CLUSTER_INVENTORY_LOADED": "true",
        "SEED_CLUSTER_INVENTORY_PATH": normalized["inventory_path"],
        "SEED_CLUSTER_INVENTORY_NAME": normalized["inventory_name"],
        "SEED_K3S_CLUSTER_NAME": normalized["cluster_name"],
        "SEED_CLUSTER_REFERENCE": "true" if normalized["reference_cluster"] else "false",
        "SEED_CLUSTER_RUNTIME": normalized["runtime"],
        "SEED_CLUSTER_NODE_COUNT": str(normalized["node_count"]),
        "SEED_CLUSTER_MAX_VALIDATED_TOPOLOGY_SIZE": str(normalized["max_validated_topology_size"]),
        "SEED_CLUSTER_NODES_JSON": json.dumps(normalized["nodes"], sort_keys=True),
        "SEED_K3S_MASTER_NAME": normalized["master_name"],
        "SEED_K3S_MASTER_IP": normalized["master_ip"],
        "SEED_K3S_WORKER1_NAME": normalized["worker1_name"],
        "SEED_K3S_WORKER1_IP": normalized["worker1_ip"],
        "SEED_K3S_WORKER2_NAME": normalized["worker2_name"],
        "SEED_K3S_WORKER2_IP": normalized["worker2_ip"],
        "SEED_K3S_USER": normalized["ssh_user"],
        "SEED_K3S_SSH_KEY": normalized["ssh_key_path"],
        "SEED_REGISTRY_HOST": normalized["registry_host"],
        "SEED_REGISTRY_PORT": str(normalized["registry_port"]),
        "SEED_REGISTRY": f"{normalized['registry_host']}:{normalized['registry_port']}",
        "SEED_CNI_MASTER_INTERFACE": normalized["default_master_interface"],
        "SEED_K3S_CLUSTER_CIDR": normalized.get("k3s_cluster_cidr") or "",
        "SEED_K3S_SERVICE_CIDR": normalized.get("k3s_service_cidr") or "",
        "SEED_K3S_NODE_CIDR_MASK_SIZE_IPV4": (
            str(normalized["k3s_node_cidr_mask_size_ipv4"])
            if normalized.get("k3s_node_cidr_mask_size_ipv4") is not None
            else ""
        ),
        "SEED_K3S_MAX_PODS": (
            str(normalized["k3s_max_pods"])
            if normalized.get("k3s_max_pods") is not None
            else ""
        ),
    }
    return "\n".join(
        f"export {key}={shlex.quote(value)}"
        for key, value in exports.items()
        if value != ""
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize SEED K3s cluster inventory")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--name", default="")
    parser.add_argument("--export-shell", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    normalized = normalize_inventory(Path(args.inventory).expanduser().resolve(), args.name or None)
    if args.export_shell:
        print(export_shell(normalized))
        return 0
    if args.json or not args.export_shell:
        print(json.dumps(normalized, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

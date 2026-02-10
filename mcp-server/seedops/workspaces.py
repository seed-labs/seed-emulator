from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

import yaml

from .inventory import DEFAULT_LABEL_PREFIX, Inventory, InventoryBuilder
from .selectors import filter_nodes
from .store import EventRow, SeedOpsStore, WorkspaceRow


def extract_container_names_from_compose(output_dir: str) -> list[str]:
    compose_path = os.path.join(output_dir, "docker-compose.yml")
    with open(compose_path, "r") as f:
        data = yaml.safe_load(f) or {}
    services = data.get("services") or {}
    if not isinstance(services, dict):
        return []
    names: list[str] = []
    for svc in services.values():
        if not isinstance(svc, dict):
            continue
        cname = svc.get("container_name")
        if cname:
            names.append(str(cname))
    # stable order
    names.sort()
    return names


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    name: str
    attach_type: str
    attach_config: dict[str, Any]
    created_at: int
    updated_at: int


class WorkspaceManager:
    def __init__(self, *, store: SeedOpsStore, docker_client: Any | None = None):
        self._store = store
        self._docker_client = docker_client
        self._builder = InventoryBuilder()
        self._cache: dict[str, Inventory] = {}

    def get_docker_client(self):
        if self._docker_client is None:
            import docker

            self._docker_client = docker.from_env()
        return self._docker_client

    def _to_ws(self, row: WorkspaceRow) -> Workspace:
        return Workspace(
            workspace_id=row.workspace_id,
            name=row.name,
            attach_type=row.attach_type,
            attach_config=row.attach_config,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def create(self, name: str) -> Workspace:
        row = self._store.create_workspace(name)
        self._store.insert_event(
            row.workspace_id,
            level="info",
            event_type="workspace.created",
            message=f"Workspace created: {name}",
            data={"name": name},
        )
        return self._to_ws(row)

    def list(self) -> list[Workspace]:
        return [self._to_ws(r) for r in self._store.list_workspaces()]

    def get(self, workspace_id: str) -> Workspace | None:
        row = self._store.get_workspace(workspace_id)
        return self._to_ws(row) if row else None

    def attach_compose(self, workspace_id: str, output_dir: str) -> dict[str, Any]:
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")

        output_dir_abs = os.path.abspath(output_dir)
        container_names = extract_container_names_from_compose(output_dir_abs)

        attach_config = {
            "output_dir": output_dir_abs,
            "container_names": container_names,
            "label_prefix": DEFAULT_LABEL_PREFIX,
        }
        self._store.update_workspace_attach(workspace_id, "compose", attach_config)
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="workspace.attached",
            message=f"Attached workspace to compose output: {output_dir_abs}",
            data={"attach_type": "compose", "output_dir": output_dir_abs, "container_count": len(container_names)},
        )
        return self.refresh(workspace_id)

    def attach_labels(self, workspace_id: str, *, name_regex: str, label_prefix: str = DEFAULT_LABEL_PREFIX) -> dict[str, Any]:
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")

        attach_config = {
            "name_regex": name_regex,
            "label_prefix": label_prefix,
        }
        self._store.update_workspace_attach(workspace_id, "labels", attach_config)
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="workspace.attached",
            message=f"Attached workspace via labels scan: {name_regex}",
            data={"attach_type": "labels", "name_regex": name_regex, "label_prefix": label_prefix},
        )
        return self.refresh(workspace_id)

    def refresh(self, workspace_id: str) -> dict[str, Any]:
        ws_row = self._store.get_workspace(workspace_id)
        if not ws_row:
            raise ValueError("Workspace not found")

        attach_type = ws_row.attach_type
        attach_config = ws_row.attach_config or {}
        label_prefix = attach_config.get("label_prefix") or DEFAULT_LABEL_PREFIX

        docker_client = self.get_docker_client()
        containers: list[Any] = []
        containers_seen = 0
        missing_containers = 0

        if attach_type == "compose":
            names = attach_config.get("container_names") or []
            if not isinstance(names, list) or not names:
                raise ValueError("Workspace is not attached (missing container_names). Call workspace_attach_compose first.")
            containers_seen = len(names)
            for cname in names:
                try:
                    c = docker_client.containers.get(str(cname))
                    containers.append(c)
                except Exception:
                    missing_containers += 1

        elif attach_type == "labels":
            name_regex = attach_config.get("name_regex")
            if not name_regex:
                raise ValueError("Workspace is not attached (missing name_regex). Call workspace_attach_labels first.")
            rx = re.compile(str(name_regex))
            all_containers = docker_client.containers.list()
            for c in all_containers:
                if not rx.search(getattr(c, "name", "")):
                    continue
                labels = getattr(c, "labels", {}) or {}
                if not isinstance(labels, dict):
                    continue
                # Filter quickly by label prefix presence
                if not any(k.startswith(label_prefix) for k in labels.keys()):
                    continue
                containers.append(c)
            containers_seen = len(containers)

        else:
            raise ValueError(f"Unknown attach_type: {attach_type}")

        inv = self._builder.build(containers, label_prefix=label_prefix)
        self._cache[workspace_id] = inv

        # Summary
        roles: dict[str, int] = {}
        asn_set: set[int] = set()
        for n in inv.nodes:
            roles[str(n.get("role", "unknown"))] = roles.get(str(n.get("role", "unknown")), 0) + 1
            asn_set.add(int(n.get("asn", -1)))

        sample_nodes = [{"node_id": n["node_id"], "container_name": n["container_name"]} for n in inv.nodes[:10]]
        summary = {
            "workspace_id": workspace_id,
            "counts": {
                "containers_seen": containers_seen,
                "nodes_parsed": len(inv.nodes),
                "missing_containers": missing_containers,
            },
            "roles": roles,
            "asns": sorted([a for a in asn_set if a >= 0]),
            "sample_nodes": sample_nodes,
        }

        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="inventory.refreshed",
            message="Inventory refreshed",
            data=summary,
        )

        return summary

    def _ensure_inventory(self, workspace_id: str) -> Inventory:
        if workspace_id not in self._cache:
            self.refresh(workspace_id)
        inv = self._cache.get(workspace_id)
        if inv is None:
            raise ValueError("Inventory not available")
        return inv

    def list_nodes(self, workspace_id: str, *, selector: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        inv = self._ensure_inventory(workspace_id)
        nodes = inv.nodes
        if selector:
            nodes = filter_nodes(nodes, selector)
        nodes = sorted(nodes, key=lambda n: n.get("node_id", ""))
        return nodes

    def get_node(self, workspace_id: str, node_id: str) -> dict[str, Any] | None:
        inv = self._ensure_inventory(workspace_id)
        return inv.by_node_id.get(node_id)

    def list_events(self, workspace_id: str, *, since_ts: int = 0, limit: int = 200) -> list[EventRow]:
        return self._store.list_events(workspace_id, since_ts=since_ts, limit=limit)


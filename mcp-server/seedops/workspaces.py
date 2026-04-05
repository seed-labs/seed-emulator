from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .inventory import DEFAULT_LABEL_PREFIX, Inventory, InventoryBuilder
from .selectors import filter_nodes, match_selector
from .store import EventRow, SeedOpsStore, WorkspaceRow


DEFAULT_REDACTED_FIELDS = ["container_name", "node_id", "labels"]


def _seed_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_compose_output_dir(output_dir: str) -> str:
    output_dir_s = str(output_dir or "").strip()
    if not output_dir_s:
        raise ValueError("output_dir is required.")

    raw = Path(output_dir_s).expanduser()
    tried: list[str] = []

    def _normalize(candidate: Path) -> Path:
        resolved = candidate.resolve()
        if resolved.name == "docker-compose.yml":
            return resolved.parent
        return resolved

    def _maybe_accept(candidate: Path) -> Path | None:
        normalized = _normalize(candidate)
        tried.append(str(normalized))
        if normalized.is_dir():
            return normalized
        return None

    if raw.is_absolute():
        accepted = _maybe_accept(raw)
        if accepted is None:
            raise ValueError(f"output_dir not found or not a directory: {tried[-1]}")
        return str(accepted)

    roots: list[Path] = []
    env_root = (os.environ.get("SEED_REPO_ROOT") or "").strip()
    if env_root:
        roots.append(Path(env_root).expanduser())
    roots.extend(
        [
            _seed_repo_root(),
            Path.cwd(),
            Path(__file__).resolve().parents[1],
        ]
    )

    seen: set[str] = set()
    for root in roots:
        key = str(root.resolve())
        if key in seen:
            continue
        seen.add(key)
        accepted = _maybe_accept(root / raw)
        if accepted is not None:
            return str(accepted)

    tried_text = ", ".join(dict.fromkeys(tried))
    raise ValueError(
        "output_dir not found or not a directory. "
        f"input={output_dir_s!r}; tried: {tried_text}"
    )


def extract_container_names_from_compose(output_dir: str) -> list[str]:
    output_dir_abs = resolve_compose_output_dir(output_dir)

    compose_path = os.path.join(output_dir_abs, "docker-compose.yml")
    if not os.path.exists(compose_path):
        raise ValueError(f"docker-compose.yml not found at: {compose_path}")

    try:
        with open(compose_path, "r") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        raise ValueError(f"Failed to parse docker-compose.yml: {e}") from e

    services = data.get("services") or {}
    if not isinstance(services, dict):
        raise ValueError("docker-compose.yml: 'services' must be a mapping (dict).")

    total_services = 0
    with_container_name = 0
    names: list[str] = []
    for svc in services.values():
        total_services += 1
        if not isinstance(svc, dict):
            continue
        cname = svc.get("container_name")
        if cname:
            with_container_name += 1
            names.append(str(cname))

    if not names:
        raise ValueError(
            "No services.*.container_name found in docker-compose.yml "
            f"(services={total_services}, with_container_name={with_container_name}). "
            "SeedOps attach_compose requires container_name. "
            "Recompile with container_name or use workspace_attach_labels."
        )

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

    @staticmethod
    def _normalize_allowed_selector(value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return dict(value)

    @staticmethod
    def _normalize_redacted_fields(value: Any) -> list[str]:
        if value is None:
            return list(DEFAULT_REDACTED_FIELDS)
        if not isinstance(value, list):
            return list(DEFAULT_REDACTED_FIELDS)
        fields: list[str] = []
        for item in value:
            field = str(item or "").strip()
            if field and field not in fields:
                fields.append(field)
        return fields

    @classmethod
    def _get_visibility_config(cls, attach_config: dict[str, Any] | None) -> dict[str, Any]:
        cfg = dict(attach_config or {})
        return {
            "allowed_selector": cls._normalize_allowed_selector(cfg.get("allowed_selector")),
            "redacted_fields": cls._normalize_redacted_fields(cfg.get("redacted_fields")),
        }

    @classmethod
    def _apply_visibility_config(
        cls,
        attach_config: dict[str, Any] | None,
        *,
        allowed_selector: dict[str, Any] | None = None,
        redacted_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        cfg = dict(attach_config or {})
        if allowed_selector is not None:
            cfg["allowed_selector"] = cls._normalize_allowed_selector(allowed_selector)
        elif "allowed_selector" not in cfg:
            cfg["allowed_selector"] = {}

        if redacted_fields is not None:
            cfg["redacted_fields"] = cls._normalize_redacted_fields(redacted_fields)
        elif "redacted_fields" not in cfg:
            cfg["redacted_fields"] = list(DEFAULT_REDACTED_FIELDS)
        return cfg

    @classmethod
    def _redact_node(cls, node: dict[str, Any], redacted_fields: list[str]) -> dict[str, Any]:
        data = dict(node)
        for field in redacted_fields:
            data.pop(str(field), None)
        return data

    @classmethod
    def _redact_nodes(cls, nodes: list[dict[str, Any]], redacted_fields: list[str]) -> list[dict[str, Any]]:
        return [cls._redact_node(node, redacted_fields) for node in nodes]

    @classmethod
    def _apply_allowed_selector(
        cls,
        nodes: list[dict[str, Any]],
        allowed_selector: dict[str, Any],
        selector: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        scoped = filter_nodes(nodes, allowed_selector) if allowed_selector else list(nodes)
        if selector:
            scoped = filter_nodes(scoped, selector)
        return scoped

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

        output_dir_abs = resolve_compose_output_dir(output_dir)
        container_names = extract_container_names_from_compose(output_dir_abs)
        visibility = self._get_visibility_config(ws.attach_config)

        attach_config = {
            "output_dir": output_dir_abs,
            "container_names": container_names,
            "label_prefix": DEFAULT_LABEL_PREFIX,
            **visibility,
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

        # Validate regex at attach time for fast feedback.
        try:
            re.compile(str(name_regex))
        except re.error as e:
            raise ValueError(f"Invalid name_regex: {e}") from e
        visibility = self._get_visibility_config(ws.attach_config)

        attach_config = {
            "name_regex": name_regex,
            "label_prefix": label_prefix,
            **visibility,
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

    def get_visibility(self, workspace_id: str) -> dict[str, Any]:
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")
        return {"workspace_id": workspace_id, **self._get_visibility_config(ws.attach_config)}

    def set_visibility(
        self,
        workspace_id: str,
        *,
        allowed_selector: dict[str, Any] | None = None,
        redacted_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")

        attach_config = self._apply_visibility_config(
            ws.attach_config,
            allowed_selector=allowed_selector,
            redacted_fields=redacted_fields,
        )
        self._store.update_workspace_attach(workspace_id, ws.attach_type, attach_config)
        self._store.insert_event(
            workspace_id,
            level="info",
            event_type="workspace.visibility.updated",
            message="Workspace visibility updated",
            data={
                "allowed_selector": attach_config.get("allowed_selector") or {},
                "redacted_fields": attach_config.get("redacted_fields") or [],
            },
        )
        return self.get_visibility(workspace_id)

    def refresh(self, workspace_id: str, *, redacted: bool = False) -> dict[str, Any]:
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

        visibility = self._get_visibility_config(attach_config)
        visible_nodes = self._apply_allowed_selector(inv.nodes, visibility["allowed_selector"])

        # Summary
        roles: dict[str, int] = {}
        asn_set: set[int] = set()
        for n in visible_nodes:
            roles[str(n.get("role", "unknown"))] = roles.get(str(n.get("role", "unknown")), 0) + 1
            asn_set.add(int(n.get("asn", -1)))

        sample_nodes = [{"node_id": n["node_id"], "container_name": n["container_name"]} for n in visible_nodes[:10]]
        if redacted:
            sample_nodes = self._redact_nodes(sample_nodes, visibility["redacted_fields"])
            sample_nodes = [node for node in sample_nodes if node]
        summary = {
            "workspace_id": workspace_id,
            "counts": {
                "containers_seen": containers_seen,
                "nodes_parsed": len(visible_nodes),
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

    def list_nodes(
        self,
        workspace_id: str,
        *,
        selector: dict[str, Any] | None = None,
        redacted: bool = False,
    ) -> list[dict[str, Any]]:
        inv = self._ensure_inventory(workspace_id)
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")
        visibility = self._get_visibility_config(ws.attach_config)
        nodes = self._apply_allowed_selector(
            inv.nodes,
            visibility["allowed_selector"],
            selector,
        )
        nodes = sorted(nodes, key=lambda n: n.get("node_id", ""))
        if redacted:
            nodes = self._redact_nodes(nodes, visibility["redacted_fields"])
        return nodes

    def get_node(self, workspace_id: str, node_id: str, *, redacted: bool = False) -> dict[str, Any] | None:
        inv = self._ensure_inventory(workspace_id)
        node = inv.by_node_id.get(node_id)
        if node is None:
            return None
        ws = self._store.get_workspace(workspace_id)
        if not ws:
            raise ValueError("Workspace not found")
        visibility = self._get_visibility_config(ws.attach_config)
        allowed_selector = visibility["allowed_selector"]
        if allowed_selector and not match_selector(node, allowed_selector):
            return None
        if redacted:
            return self._redact_node(node, visibility["redacted_fields"])
        return node

    def list_events(self, workspace_id: str, *, since_ts: int = 0, limit: int = 200) -> list[EventRow]:
        return self._store.list_events(workspace_id, since_ts=since_ts, limit=limit)

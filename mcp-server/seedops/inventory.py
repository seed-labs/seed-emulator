from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any


DEFAULT_LABEL_PREFIX = "org.seedsecuritylabs.seedemu.meta."


def _get_labels(container: Any) -> dict[str, str]:
    labels = getattr(container, "labels", None)
    if isinstance(labels, dict):
        return labels
    # Fallback: docker SDK containers often have attrs
    attrs = getattr(container, "attrs", None)
    if isinstance(attrs, dict):
        cfg = attrs.get("Config", {})
        if isinstance(cfg, dict):
            raw = cfg.get("Labels", {})
            if isinstance(raw, dict):
                return raw
    return {}


def parse_node_from_labels(
    *,
    container_name: str,
    labels: dict[str, str],
    label_prefix: str = DEFAULT_LABEL_PREFIX,
) -> dict[str, Any] | None:
    """Parse a NodeRef from SEED Emulator docker labels.

    Returns None if required labels are missing.
    """
    asn_raw = labels.get(f"{label_prefix}asn")
    node_name = labels.get(f"{label_prefix}nodename")
    role = labels.get(f"{label_prefix}role")
    if not asn_raw or not node_name or not role:
        return None

    try:
        asn = int(asn_raw)
    except ValueError:
        return None

    classes: list[str] = []
    classes_raw = labels.get(f"{label_prefix}class")
    if classes_raw:
        try:
            parsed = json.loads(classes_raw)
            if isinstance(parsed, list):
                classes = [str(x) for x in parsed]
        except Exception:
            classes = []

    loopback = labels.get(f"{label_prefix}loopback_addr") or None

    # Interfaces: meta.net.{i}.name / meta.net.{i}.address
    iface_pat = re.compile(rf"^{re.escape(label_prefix)}net\.(\d+)\.(name|address)$")
    iface_map: dict[int, dict[str, str]] = {}
    for k, v in labels.items():
        m = iface_pat.match(k)
        if not m:
            continue
        idx = int(m.group(1))
        field = m.group(2)
        iface_map.setdefault(idx, {})[field] = v

    interfaces: list[dict[str, str]] = []
    for idx in sorted(iface_map.keys()):
        entry = iface_map[idx]
        name = entry.get("name")
        address = entry.get("address")
        if not name or not address:
            continue
        interfaces.append({"name": name, "address": address})

    return {
        "node_id": f"as{asn}/{node_name}",
        "asn": asn,
        "node_name": node_name,
        "role": role,
        "classes": classes,
        "container_name": container_name,
        "interfaces": interfaces,
        "loopback": loopback,
        "labels": labels,
    }


@dataclass(frozen=True)
class Inventory:
    nodes: list[dict[str, Any]]
    by_node_id: dict[str, dict[str, Any]]
    updated_at: int


class InventoryBuilder:
    def build(self, containers: list[Any], *, label_prefix: str = DEFAULT_LABEL_PREFIX) -> Inventory:
        nodes: list[dict[str, Any]] = []
        for c in containers:
            name = getattr(c, "name", "") or getattr(c, "Name", "")
            labels = _get_labels(c)
            node = parse_node_from_labels(container_name=name, labels=labels, label_prefix=label_prefix)
            if node:
                nodes.append(node)

        nodes.sort(key=lambda n: n.get("node_id", ""))
        by_id = {n["node_id"]: n for n in nodes}
        return Inventory(nodes=nodes, by_node_id=by_id, updated_at=int(time.time()))


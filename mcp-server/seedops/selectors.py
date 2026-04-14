from __future__ import annotations

from typing import Any


SUPPORTED_SELECTOR_KEYS = {
    "asn",
    "role",
    "node_id",
    "node_name",
    "class",
    "network",
    "container_name",
    "labels",
}


def _as_list(val: Any) -> list[Any]:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


def _as_int_list(val: Any) -> list[int]:
    out: list[int] = []
    for x in _as_list(val):
        try:
            out.append(int(x))
        except Exception:
            continue
    return out


def match_selector(node: dict[str, Any], selector: dict[str, Any]) -> bool:
    """Match a node against a selector.

    Semantics:
      - AND across provided keys
      - OR within list-valued fields
      - labels is an AND across k/v
    """
    if not selector:
        return True

    unknown = set(selector.keys()) - SUPPORTED_SELECTOR_KEYS
    if unknown:
        raise ValueError(f"Unsupported selector keys: {sorted(unknown)}")

    if "asn" in selector:
        allowed_list = _as_int_list(selector["asn"])
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        if int(node.get("asn", -1)) not in allowed:
            return False

    if "role" in selector:
        allowed_list = [str(x) for x in _as_list(selector["role"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        if str(node.get("role", "")) not in allowed:
            return False

    if "node_id" in selector:
        allowed_list = [str(x) for x in _as_list(selector["node_id"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        if str(node.get("node_id", "")) not in allowed:
            return False

    if "node_name" in selector:
        allowed_list = [str(x) for x in _as_list(selector["node_name"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        if str(node.get("node_name", "")) not in allowed:
            return False

    if "container_name" in selector:
        allowed_list = [str(x) for x in _as_list(selector["container_name"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        if str(node.get("container_name", "")) not in allowed:
            return False

    if "class" in selector:
        allowed_list = [str(x) for x in _as_list(selector["class"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        classes = set(node.get("classes") or [])
        if not (classes & allowed):
            return False

    if "network" in selector:
        allowed_list = [str(x) for x in _as_list(selector["network"]) if x is not None]
        if not allowed_list:
            return False
        allowed = set(allowed_list)
        ifaces = node.get("interfaces") or []
        iface_nets = {str(i.get("name")) for i in ifaces if isinstance(i, dict)}
        if not (iface_nets & allowed):
            return False

    if "labels" in selector:
        req = selector["labels"]
        if not isinstance(req, dict):
            raise ValueError("selector.labels must be a dict")
        labels = node.get("labels") or {}
        for k, v in req.items():
            if str(labels.get(k)) != str(v):
                return False

    return True


def filter_nodes(nodes: list[dict[str, Any]], selector: dict[str, Any]) -> list[dict[str, Any]]:
    if not selector:
        return nodes
    return [n for n in nodes if match_selector(n, selector)]

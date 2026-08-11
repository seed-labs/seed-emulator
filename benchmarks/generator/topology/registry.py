"""Benchmark-local persistence and lookup for declarative topologies."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile

from generator.topology.models import TopologyPlan, TopologyRequest
from generator.topology.planner import plan_topology, validate_topology_plan


BENCHMARKS_DIR = Path(__file__).resolve().parents[2]


def spec_dir(topology_id: str, root: Path = BENCHMARKS_DIR) -> Path:
    destination = (root / "topology_specs" / topology_id).resolve()
    destination.relative_to((root / "topology_specs").resolve())
    return destination


def output_dir(topology_id: str, root: Path = BENCHMARKS_DIR) -> Path:
    destination = (root / "generated" / "declarative" / topology_id / "output").resolve()
    destination.relative_to((root / "generated" / "declarative").resolve())
    return destination


def _atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def register_request(
    request: TopologyRequest,
    *,
    force: bool = False,
    root: Path = BENCHMARKS_DIR,
) -> TopologyPlan:
    plan = plan_topology(request)
    directory = spec_dir(request.topology_id, root)
    if directory.exists() and not force:
        raise FileExistsError(f"topology already registered: {request.topology_id}")
    _atomic_json(directory / "request.json", {
        **{key: value for key, value in request.__dict__.items() if key != "budget"},
        "budget": request.budget.__dict__,
    })
    _atomic_json(directory / "plan.json", plan.to_dict())
    return plan


def load_plan(topology_id: str, root: Path = BENCHMARKS_DIR) -> TopologyPlan:
    path = spec_dir(topology_id, root) / "plan.json"
    plan = TopologyPlan.from_dict(json.loads(path.read_text(encoding="utf-8")))
    validate_topology_plan(plan)
    return plan


def topology_id_from_name(topology_name: str) -> str:
    if not topology_name.startswith("DECLARATIVE_"):
        raise ValueError(f"not a declarative topology: {topology_name}")
    topology_id = topology_name[len("DECLARATIVE_"):]
    load_plan(topology_id)
    return topology_id


def is_declarative_topology(topology_name: str) -> bool:
    if not topology_name.startswith("DECLARATIVE_"):
        return False
    try:
        topology_id_from_name(topology_name)
        return True
    except (OSError, ValueError):
        return False


def list_plans(root: Path = BENCHMARKS_DIR):
    directory = root / "topology_specs"
    if not directory.is_dir():
        return ()
    return tuple(load_plan(path.parent.name, root) for path in sorted(directory.glob("*/plan.json")))

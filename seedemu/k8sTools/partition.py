"""Partition compiled SeedEMU workloads onto Ready Kubernetes nodes.

The module keeps the large scale workflow's placement boundary small and
reusable: compiler metadata supplies ASN groups, the Kubernetes API supplies
current node capacity, and the selected algorithm returns a complete mapping.
The default ``nodeByAs`` algorithm keeps every ASN on one node, matching the
large scale B62/B63 placement contract without importing experiment-local
files.
"""
from __future__ import annotations

from collections import defaultdict
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Callable

import yaml

YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
YAML_DUMPER = getattr(yaml, "CSafeDumper", yaml.SafeDumper)


WORKLOAD_KINDS = {"Deployment", "StatefulSet", "Job", "ReplicaSet", "Pod"}
SEED_ASN_LABEL = "seedemu.io/asn"
SEED_ASN_ANNOTATION = "org.seedsecuritylabs.seedemu.meta.asn"
SEED_WORKLOAD_LABEL = "seedemu.io/workload"


def runKubectl(kubeconfig: str | Path, *arguments: str) -> dict[str, Any]:
    """Read one JSON object from kubectl using the supplied kubeconfig."""
    command = ["kubectl", "--kubeconfig", str(kubeconfig), *arguments, "-o", "json"]
    raw = subprocess.check_output(command, text=True)
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("kubectl JSON output must be an object")
    return value


def loadManifest(path: str | Path) -> list[dict[str, Any]]:
    """Load non-empty Kubernetes YAML documents from a manifest path."""
    manifest = Path(path).expanduser().resolve()
    documents: list[dict[str, Any]] = []
    with manifest.open(encoding="utf-8") as handle:
        for document in yaml.load_all(handle, Loader=YAML_LOADER):
            if document is None:
                continue
            if not isinstance(document, dict):
                raise ValueError(f"Manifest document must be a mapping: {manifest}")
            documents.append(document)
    if not documents:
        raise ValueError(f"Manifest is empty: {manifest}")
    return documents


def readPodTemplate(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Return template metadata and Pod spec for one supported workload."""
    kind = str(document.get("kind") or "")
    if kind == "Pod":
        metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        spec = document.get("spec") if isinstance(document.get("spec"), dict) else {}
        return metadata, spec
    if kind not in WORKLOAD_KINDS - {"Pod"}:
        return None
    spec = document.get("spec") if isinstance(document.get("spec"), dict) else {}
    template = spec.get("template") if isinstance(spec.get("template"), dict) else {}
    metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
    pod_spec = template.get("spec") if isinstance(template.get("spec"), dict) else {}
    return metadata, pod_spec


def workloadAsn(document: dict[str, Any], template_metadata: dict[str, Any]) -> str:
    """Return a workload ASN from labels or annotations, rejecting omissions."""
    top_metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
    sources = [template_metadata, top_metadata]
    for metadata in sources:
        labels = metadata.get("labels") if isinstance(metadata.get("labels"), dict) else {}
        annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
        label = labels.get(SEED_ASN_LABEL)
        annotation = annotations.get(SEED_ASN_ANNOTATION)
        if label is not None and annotation is not None and str(label) != str(annotation):
            name = str(top_metadata.get("name") or "<unnamed>")
            raise ValueError(f"Conflicting ASN metadata for workload {name}")
        value = label if label is not None else annotation
        if value is not None and str(value).strip():
            asn = str(value).strip()
            if not asn.isdecimal():
                name = str(top_metadata.get("name") or "<unnamed>")
                raise ValueError(f"ASN metadata for workload {name} must be numeric")
            return asn
    name = str(top_metadata.get("name") or "<unnamed>")
    raise ValueError(f"Missing {SEED_ASN_LABEL} metadata for workload {name}")


def parseCpuQuantity(value: Any) -> int:
    """Convert a Kubernetes CPU quantity to integer millicores."""
    raw = str(value or "0").strip()
    if not raw:
        return 0
    if raw.endswith("n"):
        return max(0, math.ceil(float(raw[:-1]) / 1_000_000.0))
    if raw.endswith("u"):
        return max(0, math.ceil(float(raw[:-1]) / 1_000.0))
    if raw.endswith("m"):
        return max(0, int(float(raw[:-1])))
    return max(0, int(float(raw) * 1000.0))


def parseMemoryQuantity(value: Any) -> int:
    """Convert a Kubernetes memory quantity to integer bytes."""
    raw = str(value or "0").strip()
    if not raw:
        return 0
    units = {
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "Ti": 2**40,
        "Pi": 2**50,
        "K": 10**3,
        "M": 10**6,
        "G": 10**9,
        "T": 10**12,
        "P": 10**15,
    }
    for suffix, multiplier in units.items():
        if raw.endswith(suffix):
            return max(0, int(float(raw[: -len(suffix)]) * multiplier))
    return max(0, int(float(raw)))


def podRequest(pod_spec: dict[str, Any]) -> tuple[int, int]:
    """Sum CPU and memory requests for all regular and init containers."""
    cpu = 0
    memory = 0
    containers = [*(pod_spec.get("containers") or []), *(pod_spec.get("initContainers") or [])]
    for container in containers:
        if not isinstance(container, dict):
            continue
        resources = container.get("resources") if isinstance(container.get("resources"), dict) else {}
        requests = resources.get("requests") if isinstance(resources.get("requests"), dict) else {}
        if not isinstance(requests, dict):
            continue
        cpu += parseCpuQuantity(requests.get("cpu"))
        memory += parseMemoryQuantity(requests.get("memory"))
    overhead = pod_spec.get("overhead") if isinstance(pod_spec.get("overhead"), dict) else {}
    cpu += parseCpuQuantity(overhead.get("cpu"))
    memory += parseMemoryQuantity(overhead.get("memory"))
    return cpu, memory


def replicaCount(document: dict[str, Any]) -> int:
    """Return the number of Pods represented by one workload document."""
    if document.get("kind") == "Pod":
        return 1
    raw = (document.get("spec") or {}).get("replicas", 1)
    try:
        count = int(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid replicas for {document.get('metadata', {}).get('name', '<unnamed>')}") from error
    if count < 1:
        raise ValueError("Partitioned workloads must have at least one replica")
    return count


def workloadRecords(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract one record per supported workload, including ASN and requests."""
    records: list[dict[str, Any]] = []
    for index, document in enumerate(documents):
        kind = str(document.get("kind") or "")
        if kind == "DaemonSet":
            metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
            labels = metadata.get("labels") if isinstance(metadata.get("labels"), dict) else {}
            if labels.get(SEED_WORKLOAD_LABEL) == "seedemu":
                raise ValueError("DaemonSet workloads cannot be assigned by a single nodeName")
        template = readPodTemplate(document)
        if template is None:
            continue
        metadata, pod_spec = template
        top_metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        top_labels = top_metadata.get("labels") if isinstance(top_metadata.get("labels"), dict) else {}
        template_labels = metadata.get("labels") if isinstance(metadata.get("labels"), dict) else {}
        top_annotations = top_metadata.get("annotations") if isinstance(top_metadata.get("annotations"), dict) else {}
        template_annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
        workload_label = template_labels.get(SEED_WORKLOAD_LABEL, top_labels.get(SEED_WORKLOAD_LABEL))
        has_asn = any(
            key in template_labels
            or key in top_labels
            or SEED_ASN_ANNOTATION in template_annotations
            or SEED_ASN_ANNOTATION in top_annotations
            for key in (SEED_ASN_LABEL,)
        )
        if workload_label is not None and str(workload_label) != "seedemu":
            continue
        if workload_label is None and not has_asn:
            continue
        name = str(top_metadata.get("name") or f"workload-{index}")
        records.append({
            "name": name,
            "kind": kind,
            "docIndex": index,
            "asn": workloadAsn(document, metadata),
            "replicas": replicaCount(document),
            "cpuMillis": podRequest(pod_spec)[0],
            "memoryBytes": podRequest(pod_spec)[1],
        })
    return records


def isControlPlane(node: dict[str, Any]) -> bool:
    """Return whether a node has a Kubernetes control-plane role label."""
    labels = node.get("metadata", {}).get("labels", {}) or {}
    return any(key in labels for key in ("node-role.kubernetes.io/control-plane", "node-role.kubernetes.io/master"))


def quantityCapacity(value: Any, *, default: int = 0) -> int:
    """Parse an allocatable Pod quantity, accepting Kubernetes ``k`` suffixes."""
    raw = str(value or "").strip()
    if not raw:
        return default
    if raw.lower().endswith("k"):
        return int(float(raw[:-1]) * 1000)
    return int(float(raw))


def readyNodes(nodes_data: dict[str, Any], *, excludeControlPlane: bool = True) -> list[dict[str, Any]]:
    """Return Ready, schedulable nodes with normalized allocatable capacity."""
    nodes: list[dict[str, Any]] = []
    for node in nodes_data.get("items", []):
        if not isinstance(node, dict):
            continue
        metadata = node.get("metadata") if isinstance(node.get("metadata"), dict) else {}
        name = str(metadata.get("name") or "")
        conditions = node.get("status", {}).get("conditions", []) or []
        ready = any(item.get("type") == "Ready" and item.get("status") == "True" for item in conditions)
        if not name or not ready or node.get("spec", {}).get("unschedulable"):
            continue
        if any(taint.get("effect") in {"NoSchedule", "NoExecute"}
               for taint in node.get("spec", {}).get("taints", [])):
            continue
        if excludeControlPlane and isControlPlane(node):
            continue
        allocatable = node.get("status", {}).get("allocatable", {}) or {}
        nodes.append({
            "name": name,
            "cpuMillis": parseCpuQuantity(allocatable.get("cpu")),
            "memoryBytes": parseMemoryQuantity(allocatable.get("memory")),
            "podSlots": quantityCapacity(allocatable.get("pods"), default=110),
        })
    if not nodes and excludeControlPlane:
        return readyNodes(nodes_data, excludeControlPlane=False)
    return sorted(nodes, key=lambda item: item["name"])


def existingUsage(pods_data: dict[str, Any]) -> dict[str, dict[str, int]]:
    """Sum active Pod requests and counts by node for capacity admission."""
    result: dict[str, dict[str, int]] = defaultdict(lambda: {"cpuMillis": 0, "memoryBytes": 0, "podSlots": 0})
    for pod in pods_data.get("items", []):
        if not isinstance(pod, dict):
            continue
        if pod.get("status", {}).get("phase") in {"Succeeded", "Failed"}:
            continue
        node_name = str(pod.get("spec", {}).get("nodeName") or "")
        if not node_name:
            continue
        cpu, memory = podRequest(pod.get("spec") if isinstance(pod.get("spec"), dict) else {})
        result[node_name]["cpuMillis"] += cpu
        result[node_name]["memoryBytes"] += memory
        result[node_name]["podSlots"] += 1
    return dict(result)


def groupWorkloads(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Aggregate workload count and resource requests by ASN."""
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"replicas": 0, "cpuMillis": 0, "memoryBytes": 0})
    for record in records:
        group = groups[record["asn"]]
        group["replicas"] += record["replicas"]
        group["cpuMillis"] += record["replicas"] * record["cpuMillis"]
        group["memoryBytes"] += record["replicas"] * record["memoryBytes"]
    return dict(groups)


def networkName(item: Any) -> str:
    """Return a NAD name from one Multus network-selection item."""
    if isinstance(item, dict):
        value = str(item.get("name") or "")
    else:
        value = str(item or "")
    return value.rsplit("/", 1)[-1].strip()


def workloadNetworks(documents: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract LAN membership from compiler Multus annotations for algorithms."""
    network_members: dict[str, set[str]] = defaultdict(set)
    names = {record["name"] for record in records}
    for document in documents:
        name = str((document.get("metadata") or {}).get("name") or "")
        if name not in names:
            continue
        template = readPodTemplate(document)
        if template is None:
            continue
        metadata, _ = template
        annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
        raw = annotations.get("k8s.v1.cni.cncf.io/networks")
        items: Any = []
        if isinstance(raw, str) and raw.strip():
            try:
                items = json.loads(raw)
            except json.JSONDecodeError:
                items = [part.strip() for part in raw.split(",") if part.strip()]
        if not isinstance(items, list):
            continue
        for item in items:
            nad = networkName(item)
            if nad:
                network_members[nad].add(name)
    return [
        {"id": network_id, "members": sorted(members)}
        for network_id, members in sorted(network_members.items())
        if members
    ]


def placementMetrics(networks: list[dict[str, Any]], mapping: dict[str, str]) -> dict[str, Any]:
    """Recompute large-scale LAN span and pair-cut metrics."""
    counts = defaultdict(int)
    for node in mapping.values():
        counts[node] += 1
    spans = 0
    pair_cut = 0
    for network in networks:
        occupied = defaultdict(int)
        for name in network["members"]:
            if name in mapping:
                occupied[mapping[name]] += 1
        spans += max(0, len(occupied) - 1)
        total = sum(occupied.values())
        pair_cut += (total * total - sum(value * value for value in occupied.values())) // 2
    return {
        "counts": dict(counts),
        "S": spans,
        "R": pair_cut,
        "parentInterfaces": len(networks) + spans,
    }


def assignNodeByAs(
    records: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    usage: dict[str, dict[str, int]],
    *,
    podReserve: int = 0,
    maxNodesPerWorker: int = 900,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Assign whole ASN groups with live CPU, memory, and Pod-slot checks."""
    if not nodes:
        raise ValueError("No Ready schedulable Kubernetes nodes found")
    if maxNodesPerWorker < 1:
        raise ValueError("maxNodesPerWorker must be positive")
    groups = groupWorkloads(records)
    remaining = createRemainingCapacity(nodes, usage, podReserve, maxNodesPerWorker)
    assignments: dict[str, str] = {}
    plan: dict[str, Any] = {"groups": groups, "nodes": copy.deepcopy(remaining), "assignments": {}}
    ordered = sorted(groups.items(), key=lambda item: (-item[1]["replicas"], int(item[0])))
    for asn, demand in ordered:
        candidates = [
            (name, capacity)
            for name, capacity in remaining.items()
            if demand["replicas"] <= capacity["podSlots"]
            and demand["cpuMillis"] <= capacity["cpuMillis"]
            and demand["memoryBytes"] <= capacity["memoryBytes"]
        ]
        if not candidates:
            raise ValueError(f"ASN {asn} cannot fit on any eligible Kubernetes node")
        name, _ = min(
            candidates,
            key=lambda item: (
                -item[1]["podSlots"],
                plan["nodes"][item[0]]["podSlots"] - item[1]["podSlots"],
                item[0],
            ),
        )
        for key in ("podSlots", "cpuMillis", "memoryBytes"):
            remaining[name][key] -= demand["replicas"] if key == "podSlots" else demand[key]
        assignments[asn] = name
    plan["assignments"] = assignments
    plan["remaining"] = remaining
    return assignments, plan


def assignRoundRobin(records: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> dict[str, str]:
    """Provide a small extensibility example that balances individual workloads."""
    ordered = sorted(nodes, key=lambda item: item["name"])
    if not ordered:
        raise ValueError("No Ready schedulable Kubernetes nodes found")
    mapping: dict[str, str] = {}
    index = 0
    for record in records:
        mapping[record["name"]] = ordered[index % len(ordered)]["name"]
        index += 1
    return mapping


def runNodeByAsAlgorithm(
    records: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    usage: dict[str, dict[str, int]],
    *,
    podReserve: int,
    maxNodesPerWorker: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Adapt the ASN-to-node solver to the common workload mapping contract."""
    as_mapping, plan = assignNodeByAs(
        records,
        nodes,
        usage,
        podReserve=podReserve,
        maxNodesPerWorker=maxNodesPerWorker,
    )
    return {record["name"]: as_mapping[record["asn"]] for record in records}, plan


def runRoundRobinAlgorithm(
    records: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    usage: dict[str, dict[str, int]],
    *,
    podReserve: int,
    maxNodesPerWorker: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Adapt the simple round-robin solver to the common algorithm registry."""
    del usage, podReserve, maxNodesPerWorker
    mapping = assignRoundRobin(records, nodes)
    return mapping, {"assignments": mapping}


def runDefaultAlgorithm(
    records: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    usage: dict[str, dict[str, int]],
    *,
    podReserve: int,
    maxNodesPerWorker: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Return an empty mapping so Kubernetes' default scheduler remains active."""
    del records, nodes, usage, podReserve, maxNodesPerWorker
    return {}, {"mode": "kubernetes scheduler", "assignments": {}}


def normalizeAlgorithm(value: str | None) -> str:
    """Normalize CLI spellings while retaining the public algorithm names."""
    raw = str(value or "nodeByAs").strip()
    aliases = {
        "nodeas": "nodeByAs",
        "node-by-as": "nodeByAs",
        "nodebyas": "nodeByAs",
        "round-robin": "roundRobin",
        "roundrobin": "roundRobin",
        "default": "default",
        "scheduler": "default",
        "kubernetes-default-scheduler": "default",
    }
    return aliases.get(raw.lower(), raw)


def resolveAlgorithm(value: str | Path | None) -> str:
    """Resolve value as a built-in name or an existing .py script from cwd.

    Call this before entering the temporary running directory so user-relative
    script paths preserve the same meaning through the public up API.
    """
    raw = str(value) if value is not None else "nodeByAs"
    path = Path(raw).expanduser()
    if path.suffix.lower() == ".py":
        path = path.resolve()
        package_root = Path(__file__).resolve().parent
        if not path.is_relative_to(package_root):
            raise ValueError(f"Partition scripts must be inside {package_root}: {path}")
        if not path.is_file():
            raise FileNotFoundError(f"Partition script not found: {path}")
        return str(path)
    selected = normalizeAlgorithm(raw)
    if selected not in PARTITION_ALGORITHMS:
        raise ValueError(
            f"Unknown partition algorithm {raw!r}; use "
            f"{', '.join(PARTITION_ALGORITHMS)} or a .py script path"
        )
    return selected


def createRemainingCapacity(
    nodes: list[dict[str, Any]],
    usage: dict[str, dict[str, int]],
    podReserve: int,
    maxNodesPerWorker: int,
) -> dict[str, dict[str, int]]:
    """Subtract usage, Pod reserve and worker cap from nodes' allocatable data."""
    remaining = {}
    for node in nodes:
        used = usage.get(node["name"], {})
        remaining[node["name"]] = {
            "cpuMillis": max(0, node["cpuMillis"] - used.get("cpuMillis", 0)),
            "memoryBytes": max(0, node["memoryBytes"] - used.get("memoryBytes", 0)),
            "podSlots": max(0, min(maxNodesPerWorker,
                node["podSlots"] - used.get("podSlots", 0) - podReserve)),
        }
    return remaining


def validateMapping(
    records: list[dict[str, Any]],
    mapping: Any,
    remaining: dict[str, dict[str, int]],
) -> None:
    """Require mapping to cover records exactly and fit each remaining node budget."""
    if not isinstance(mapping, dict):
        raise ValueError("Partition output must contain a mapping object")
    names = [record["name"] for record in records]
    if len(set(names)) != len(names):
        raise ValueError("Partition requires unique workload names")
    missing = set(names) - set(mapping)
    extra = set(mapping) - set(names)
    if missing or extra:
        raise ValueError(f"Partition mapping coverage differs: missing={sorted(missing)}, extra={sorted(extra)}")
    planned = {name: dict(cpuMillis=0, memoryBytes=0, podSlots=0) for name in remaining}
    for record in records:
        target = mapping[record["name"]]
        if not isinstance(target, str) or target not in remaining:
            raise ValueError(f"Partition selected an ineligible node for {record['name']}: {target!r}")
        demand = planned[target]
        demand["podSlots"] += record["replicas"]
        for resource in ("cpuMillis", "memoryBytes"):
            demand[resource] += record["replicas"] * record[resource]
    for name, demand in planned.items():
        for resource, value in demand.items():
            if value > remaining[name][resource]:
                raise ValueError(
                    f"Partition exceeds {resource} capacity on {name}: "
                    f"planned={value}, available={remaining[name][resource]}"
                )


def executePartitionScript(script: Path, inputPath: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run script with --input inputPath / --output fresh JSON, recording its log.

    The script receives topology and capacity only; kubeconfig is not an input.
    A unique output path prevents successful exits from reusing stale results.
    """
    log_path = inputPath.with_name("partition.log")
    source_hash = hashlib.sha256(script.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix="partition-script-", dir=inputPath.parent) as temporary:
        output = Path(temporary) / "result.json"
        command = [sys.executable, str(script), "--input", str(inputPath), "--output", str(output)]
        with log_path.open("w", encoding="utf-8") as log:
            completed = subprocess.run(command, cwd=script.parent, stdout=log, stderr=subprocess.STDOUT, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"Partition script exited {completed.returncode}; see {log_path}")
        if not output.is_file():
            raise ValueError(f"Partition script did not write --output JSON; see {log_path}")
        raw = output.read_text(encoding="utf-8")
        inputPath.with_name("partitionScriptResult.json").write_text(raw, encoding="utf-8")
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"Partition script output is not valid JSON; see {log_path}") from error
        if not isinstance(result, dict):
            raise ValueError("Partition script output must be a JSON object with mapping")
    return result, {"path": str(script), "sha256": source_hash, "argv": command, "log": str(log_path)}


def applyPlacement(documents: list[dict[str, Any]], records: list[dict[str, Any]], mapping: dict[str, str]) -> None:
    """Mutate workload Pod specs with the selected fixed nodeName mapping."""
    for record in records:
        document = documents[record["docIndex"]]
        name = record["name"]
        target = mapping.get(name)
        if not target:
            raise ValueError(f"Partition result has no node for workload {name}")
        template = readPodTemplate(document)
        if template is None:
            continue
        _, pod_spec = template
        pod_spec["nodeName"] = target
        for key in ("nodeSelector", "affinity", "topologySpreadConstraints", "schedulerName"):
            pod_spec.pop(key, None)


def writeManifest(path: Path, documents: list[dict[str, Any]]) -> None:
    """Write mutated Kubernetes documents without sorting user fields."""
    path.write_text(yaml.dump_all(documents, Dumper=YAML_DUMPER, sort_keys=False), encoding="utf-8")


def partitionManifest(
    manifest: str | Path,
    kubeconfig: str | Path,
    *,
    algorithm: str | Path = "nodeByAs",
    nodesData: dict[str, Any] | None = None,
    podsData: dict[str, Any] | None = None,
    podReserve: int = 0,
    maxNodesPerWorker: int = 900,
) -> dict[str, Any]:
    """Restore the compiler source, apply one algorithm, and write evidence.

    The source snapshot is refreshed whenever the current manifest is not the
    last generated deployment manifest, which makes repeated ``clean``/``up``
    cycles deterministic and avoids retaining a stale placement after recompile.
    """
    selected = resolveAlgorithm(algorithm)
    if type(podReserve) is not int or podReserve < 0:
        raise ValueError("podReserve must be a nonnegative integer")
    if type(maxNodesPerWorker) is not int or maxNodesPerWorker < 1:
        raise ValueError("maxNodesPerWorker must be a positive integer")
    manifest_path = Path(manifest).expanduser().resolve()
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    source_path = manifest_path.with_name(f".{manifest_path.name}.k8sTools-source.yaml")
    state_path = manifest_path.with_name("partitionApplied.json")
    current_bytes = manifest_path.read_bytes()
    previous = {}
    if state_path.is_file():
        try:
            previous = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
    if source_path.is_file() and hashlib.sha256(current_bytes).hexdigest() == previous.get("deploymentManifestSha256"):
        source_bytes = source_path.read_bytes()
    else:
        source_bytes = current_bytes
        source_path.write_bytes(source_bytes)
    documents = loadManifestFromBytes(source_bytes)
    records = workloadRecords(documents)
    networks = workloadNetworks(documents, records)
    nodes_data = nodesData if nodesData is not None else runKubectl(kubeconfig, "get", "nodes")
    pods_data = podsData if podsData is not None else runKubectl(kubeconfig, "get", "pods", "-A")
    nodes = readyNodes(nodes_data)
    usage = existingUsage(pods_data)
    remaining = createRemainingCapacity(nodes, usage, podReserve, maxNodesPerWorker)
    input_path = manifest_path.with_name("partitionInput.json")
    input_value = {
        "schemaVersion": 1,
        "algorithm": selected,
        "topology": {"vertices": [record["name"] for record in records], "networks": networks},
        "asns": {record["name"]: record["asn"] for record in records},
        "workloads": records,
        "nodes": nodes,
        "existingUsage": usage,
        "remainingCapacity": remaining,
        "options": {"podReserve": podReserve, "maxNodesPerWorker": maxNodesPerWorker},
    }
    input_path.write_text(json.dumps(input_value, indent=2), encoding="utf-8")
    script_metadata = None
    if Path(selected).suffix.lower() == ".py":
        script_result, script_metadata = executePartitionScript(Path(selected), input_path)
        mapping = script_result.get("mapping")
        plan = script_result.get("details", {})
    elif records:
        handler = PARTITION_ALGORITHMS[selected]
        mapping, plan = handler(
            records,
            nodes,
            usage,
            podReserve=podReserve,
            maxNodesPerWorker=maxNodesPerWorker,
        )
    else:
        mapping = {}
        plan = {"mode": "no SeedEMU workloads to partition", "assignments": {}}
    if selected != "default":
        validateMapping(records, mapping, remaining)
        applyPlacement(documents, records, mapping)
    deployment_bytes = yaml.dump_all(documents, Dumper=YAML_DUMPER, sort_keys=False).encode("utf-8")
    manifest_path.write_bytes(deployment_bytes)
    result = {
        "algorithm": selected,
        "requestedAlgorithm": str(algorithm),
        "mapping": mapping,
        "plan": plan,
        "workloads": records,
        "networks": networks,
        "nodes": nodes,
        "existingUsage": usage,
        "metrics": placementMetrics(networks, mapping),
        "podReserve": podReserve,
        "maxNodesPerWorker": maxNodesPerWorker,
        "sourceManifestSha256": hashlib.sha256(source_bytes).hexdigest(),
        "deploymentManifestSha256": hashlib.sha256(deployment_bytes).hexdigest(),
        "placementBinding": "nodeName" if selected != "default" else "scheduler",
    }
    if script_metadata is not None:
        result["script"] = script_metadata
    state_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    # Keep the B63 evidence name as a compatibility artifact while the more
    # descriptive partitionApplied.json remains the authoritative state file.
    manifest_path.with_name("partitionResult.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def loadManifestFromBytes(value: bytes) -> list[dict[str, Any]]:
    """Load manifest documents from bytes for source-snapshot processing."""
    documents: list[dict[str, Any]] = []
    for document in yaml.load_all(value.decode("utf-8"), Loader=YAML_LOADER):
        if document is None:
            continue
        if not isinstance(document, dict):
            raise ValueError("Manifest document must be a mapping")
        documents.append(document)
    if not documents:
        raise ValueError("Manifest is empty")
    return documents


PARTITION_ALGORITHMS: dict[str, Callable[..., Any]] = {
    "nodeByAs": runNodeByAsAlgorithm,
    "roundRobin": runRoundRobinAlgorithm,
    "default": runDefaultAlgorithm,
}

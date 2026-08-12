"""Fail-closed promotion of live-validated generated scenarios."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import uuid
from typing import Dict, Iterable, Mapping, Sequence

from generator.contracts import inspect_contracts
from generator.models import ScenarioSpec, SuiteManifest
from generator.storage import suite_manifest_path, validate_manifest_file
from generator.validator import validate_manifest


RECEIPT_SCHEMA_VERSION = 1
PROMOTION_SCHEMA_VERSION = 1
MIN_LIFECYCLE_RUNS = 2
PROMOTABLE_TRACKS = {
    "container_stopped": "network_functional",
    "dns_nameserver": "network_functional",
    "bird_wrong_asn": "network_control_plane",
    "random_complex_transit_acl": "network_control_plane",
    "random_complex_dual_bgp_acl": "network_control_plane",
}


def _canonical_bytes(value: Mapping[str, object]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _signed_document(payload: Dict[str, object], field: str) -> Dict[str, object]:
    document = dict(payload)
    document[field] = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    return document


def _verify_document(document: Mapping[str, object], field: str) -> None:
    supplied = str(document.get(field, ""))
    payload = {key: value for key, value in document.items() if key != field}
    expected = hashlib.sha256(_canonical_bytes(payload)).hexdigest()
    if not supplied or supplied != expected:
        raise ValueError(f"{field} is missing or does not match document content")


def _atomic_json(path: Path, value: Mapping[str, object]) -> Path:
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
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
    return path


def write_lifecycle_receipt(
    path: Path,
    results: Sequence[Mapping[str, object]],
    *,
    agent_type: str,
    blind_mode: bool,
    validate_only: bool,
) -> Path:
    """Persist machine-readable evidence from one real benchmark CLI run."""
    if agent_type != "rule" or not validate_only:
        raise ValueError("promotion receipts require rule + validate-only (no AI)")
    if not blind_mode or not results:
        raise ValueError("promotion receipts require a non-empty blind run")
    contracts = {
        str(item.get("generation_contract_sha256", "")) for item in results
    }
    suites = {str(item.get("generated_suite_id", "")) for item in results}
    if "" in contracts or len(contracts) != 1 or "" in suites or len(suites) != 1:
        raise ValueError("receipt results must belong to one generated suite/contract")
    scenarios = []
    for item in results:
        scenarios.append({
            "name": item.get("scenario"),
            "fingerprint": item.get("generation_fingerprint"),
            "topology": item.get("topology"),
            "healthy_baseline_verified": item.get("healthy_baseline_verified") is True,
            "fault_injection_verified": item.get("fault_injection_verified") is True,
            "fix_verified": item.get("fix_verified") is True,
            "standard_cleanup_verified": item.get("standard_cleanup_verified") is True,
            "topology_tainted": item.get("topology_tainted") is True,
            "scenario_error": str(item.get("scenario_error", "")),
        })
    payload = {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "receipt_id": str(uuid.uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suite_id": suites.pop(),
        "contract_sha256": contracts.pop(),
        "execution": {
            "agent": agent_type,
            "ai_invoked": False,
            "blind_mode": True,
            "validate_only": True,
        },
        "scenarios": scenarios,
    }
    return _atomic_json(path, _signed_document(payload, "receipt_sha256"))


def _read_receipt(path: Path) -> Dict[str, object]:
    document = json.loads(path.resolve().read_text(encoding="utf-8"))
    _verify_document(document, "receipt_sha256")
    if document.get("schema_version") != RECEIPT_SCHEMA_VERSION:
        raise ValueError("unsupported lifecycle receipt schema")
    execution = document.get("execution") or {}
    if execution != {
        "agent": "rule",
        "ai_invoked": False,
        "blind_mode": True,
        "validate_only": True,
    }:
        raise ValueError("lifecycle receipt is not a blind no-AI validation")
    return document


def _validate_topology_evidence(
    manifest: SuiteManifest, topology_path: Path, observation_path: Path
) -> Dict[str, str]:
    topology = json.loads(topology_path.resolve().read_text(encoding="utf-8"))
    observation = json.loads(observation_path.resolve().read_text(encoding="utf-8"))
    topology_names = {item.topology for item in manifest.scenarios}
    if len(topology_names) != 1 or not next(iter(topology_names)).startswith("DECLARATIVE_"):
        raise ValueError("automatic promotion currently requires one declarative topology")
    topology_id = next(iter(topology_names)).removeprefix("DECLARATIVE_")
    from generator.topology.registry import load_plan

    registered_plan = load_plan(topology_id)
    if topology.get("topology_id") != topology_id or topology.get("connectivity_verified") is not True:
        raise ValueError("topology smoke evidence does not prove connectivity")
    if not topology.get("topology_fingerprint"):
        raise ValueError("topology evidence has no fingerprint")
    if topology.get("topology_fingerprint") != registered_plan.fingerprint:
        raise ValueError("topology evidence differs from the registered plan")
    if observation.get("capture_profile") not in {
        "declarative_capability_driven", "declarative_capability_sampled"
    }:
        raise ValueError("observation evidence is not capability-driven")
    if observation.get("topology_id") != topology_id:
        raise ValueError("observation evidence targets another topology")
    if observation.get("topology_fingerprint") != topology.get("topology_fingerprint"):
        raise ValueError("observation and topology fingerprints differ")
    if observation.get("scenario_metadata_included") is not False:
        raise ValueError("observation evidence does not prove blind metadata isolation")
    if int(observation.get("probe_count", 0)) <= 0 or not observation.get("observations"):
        raise ValueError("observation evidence contains no useful probes")
    return {
        "topology_evidence_sha256": _sha256_file(topology_path.resolve()),
        "observation_evidence_sha256": _sha256_file(observation_path.resolve()),
        "topology_fingerprint": str(topology["topology_fingerprint"]),
    }


def promotion_record_path(benchmarks_dir: Path, suite_id: str) -> Path:
    return suite_manifest_path(benchmarks_dir, suite_id).with_name("promotion.json")


def promote_suite(
    benchmarks_dir: Path,
    suite_id: str,
    receipt_paths: Iterable[Path],
    *,
    topology_evidence: Path,
    observation_evidence: Path,
) -> Path:
    """Promote every scenario in a suite after independent evidence checks."""
    root = benchmarks_dir.resolve()
    manifest_path = suite_manifest_path(root, suite_id)
    manifest = validate_manifest_file(manifest_path)
    if any(item.main_score_eligible for item in manifest.scenarios):
        raise ValueError("suite already contains promoted scenarios")
    current_contract = inspect_contracts(root).sha256
    if manifest.contract_sha256 != current_contract:
        raise ValueError("suite contract differs from current benchmark contract")
    topology_proof = _validate_topology_evidence(
        manifest, topology_evidence, observation_evidence
    )
    receipts = []
    receipt_ids = set()
    passes = {item.name: set() for item in manifest.scenarios}
    by_name = {item.name: item for item in manifest.scenarios}
    for path in receipt_paths:
        receipt = _read_receipt(path)
        receipt_id = str(receipt["receipt_id"])
        if receipt_id in receipt_ids:
            raise ValueError("duplicate lifecycle receipt id")
        receipt_ids.add(receipt_id)
        if receipt.get("suite_id") != suite_id or receipt.get("contract_sha256") != current_contract:
            raise ValueError("lifecycle receipt suite/contract differs")
        for result in receipt.get("scenarios") or []:
            name = str(result.get("name", ""))
            spec = by_name.get(name)
            if spec is None or result.get("fingerprint") != spec.fingerprint:
                raise ValueError("receipt scenario fingerprint differs")
            required = (
                result.get("healthy_baseline_verified") is True
                and result.get("fault_injection_verified") is True
                and result.get("fix_verified") is True
                and result.get("standard_cleanup_verified") is True
                and result.get("topology_tainted") is False
                and not result.get("scenario_error")
            )
            if not required:
                raise ValueError(f"scenario {name} lifecycle receipt is not clean")
            passes[name].add(receipt_id)
        receipts.append({
            "path": str(path.resolve().relative_to(root)),
            "sha256": _sha256_file(path.resolve()),
            "receipt_id": receipt_id,
        })
    insufficient = {
        name: len(ids) for name, ids in passes.items() if len(ids) < MIN_LIFECYCLE_RUNS
    }
    if insufficient:
        raise ValueError(f"scenarios lack {MIN_LIFECYCLE_RUNS} clean runs: {insufficient}")
    unsupported = sorted({
        item.template_id for item in manifest.scenarios
        if item.template_id not in PROMOTABLE_TRACKS
    })
    if unsupported:
        raise ValueError(f"suite contains templates without promotion policy: {unsupported}")
    promoted = tuple(
        replace(
            item,
            benchmark_track=PROMOTABLE_TRACKS[item.template_id],
            main_score_eligible=True,
            quarantine_reason="",
        )
        for item in manifest.scenarios
    )
    promoted_manifest = replace(manifest, scenarios=promoted)
    validate_manifest(promoted_manifest)
    manifest_document = promoted_manifest.to_dict()
    manifest_bytes = json.dumps(
        manifest_document, ensure_ascii=False, indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"
    record_payload = {
        "schema_version": PROMOTION_SCHEMA_VERSION,
        "suite_id": suite_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_sha256": current_contract,
        "policy": {"minimum_independent_lifecycle_runs": MIN_LIFECYCLE_RUNS},
        "promoted_scenarios": [
            {
                "name": item.name,
                "fingerprint": item.fingerprint,
                "benchmark_track": item.benchmark_track,
            }
            for item in promoted
        ],
        "receipts": receipts,
        "topology_evidence": str(topology_evidence.resolve().relative_to(root)),
        "observation_evidence": str(observation_evidence.resolve().relative_to(root)),
        **topology_proof,
        "promoted_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }
    record = _signed_document(record_payload, "promotion_sha256")
    # Publish proof first. An interrupted operation leaves a quarantined suite;
    # a promoted manifest is never visible without a matching proof record.
    record_path = _atomic_json(promotion_record_path(root, suite_id), record)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".manifest.promoted.", suffix=".tmp", dir=manifest_path.parent
    )
    original_manifest = manifest_path.read_bytes()
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(manifest_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, manifest_path)
        verify_promotion_record(root, validate_manifest_file(manifest_path))
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        manifest_path.write_bytes(original_manifest)
        raise
    return record_path


def verify_promotion_record(benchmarks_dir: Path, manifest: SuiteManifest) -> Dict[str, object]:
    """Revalidate proof every time a promoted generated suite is loaded."""
    root = benchmarks_dir.resolve()
    record_path = promotion_record_path(root, manifest.suite_id)
    if not record_path.is_file():
        raise ValueError(f"promoted suite {manifest.suite_id} has no promotion record")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    _verify_document(record, "promotion_sha256")
    if record.get("schema_version") != PROMOTION_SCHEMA_VERSION:
        raise ValueError("unsupported promotion record schema")
    if record.get("suite_id") != manifest.suite_id or record.get("contract_sha256") != manifest.contract_sha256:
        raise ValueError("promotion record suite/contract differs")
    manifest_path = suite_manifest_path(root, manifest.suite_id)
    if record.get("promoted_manifest_sha256") != _sha256_file(manifest_path):
        raise ValueError("promoted manifest differs from audited content")
    expected = {
        (item.name, item.fingerprint, item.benchmark_track)
        for item in manifest.scenarios if item.main_score_eligible
    }
    recorded = {
        (item["name"], item["fingerprint"], item["benchmark_track"])
        for item in record.get("promoted_scenarios") or []
    }
    if expected != recorded or len(expected) != len(manifest.scenarios):
        raise ValueError("promotion record scenario set differs")
    passes = {item.name: set() for item in manifest.scenarios}
    by_name = {item.name: item for item in manifest.scenarios}
    for item in record.get("receipts") or []:
        evidence = (root / item["path"]).resolve()
        evidence.relative_to(root)
        if _sha256_file(evidence) != item["sha256"]:
            raise ValueError("promoted lifecycle evidence was modified")
        receipt = _read_receipt(evidence)
        if receipt.get("suite_id") != manifest.suite_id or receipt.get("contract_sha256") != manifest.contract_sha256:
            raise ValueError("promoted lifecycle receipt suite/contract differs")
        receipt_id = str(receipt["receipt_id"])
        for result in receipt.get("scenarios") or []:
            spec = by_name.get(str(result.get("name", "")))
            if spec is None or result.get("fingerprint") != spec.fingerprint:
                raise ValueError("promoted receipt scenario fingerprint differs")
            if not (
                result.get("healthy_baseline_verified") is True
                and result.get("fault_injection_verified") is True
                and result.get("fix_verified") is True
                and result.get("standard_cleanup_verified") is True
                and result.get("topology_tainted") is False
                and not result.get("scenario_error")
            ):
                raise ValueError("promoted receipt contains a failed lifecycle")
            passes[spec.name].add(receipt_id)
    minimum = int((record.get("policy") or {}).get(
        "minimum_independent_lifecycle_runs", 0
    ))
    if minimum < MIN_LIFECYCLE_RUNS or any(
        len(ids) < minimum for ids in passes.values()
    ):
        raise ValueError("promotion record lacks independent clean lifecycle runs")
    for path_key, sha_key in (
        ("topology_evidence", "topology_evidence_sha256"),
        ("observation_evidence", "observation_evidence_sha256"),
    ):
        evidence = (root / str(record[path_key])).resolve()
        evidence.relative_to(root)
        if _sha256_file(evidence) != record[sha_key]:
            raise ValueError(f"{path_key} was modified")
    _validate_topology_evidence(
        manifest,
        (root / str(record["topology_evidence"])).resolve(),
        (root / str(record["observation_evidence"])).resolve(),
    )
    return record

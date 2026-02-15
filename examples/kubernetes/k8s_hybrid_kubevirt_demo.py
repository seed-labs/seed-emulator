#!/usr/bin/env python3

import json
import os
from typing import Dict, Tuple

from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import WebService
from seedemu.compiler import KubernetesCompiler, SchedulingStrategy
from seedemu.core import Emulator, Binding, Filter


VALID_RUNTIME_PROFILES = {"auto", "full", "degraded", "strict"}


def _normalize_arch(machine: str) -> str:
    machine_lower = machine.lower()
    if machine_lower in {"x86_64", "amd64"}:
        return "x86_64"
    if machine_lower in {"aarch64", "arm64"}:
        return "arm64"
    return machine_lower


def _parse_bool(value: str, default_value: bool) -> bool:
    if value is None:
        return default_value

    value_lower = value.strip().lower()
    if value_lower in {"1", "true", "yes", "on"}:
        return True
    if value_lower in {"0", "false", "no", "off"}:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def detect_host_capabilities() -> Dict[str, object]:
    detected_arch = _normalize_arch(os.uname().machine)
    detected_has_kvm = os.path.exists("/dev/kvm")

    return {
        "arch": _normalize_arch(os.environ.get("SEED_HOST_ARCH", detected_arch)),
        "has_kvm": _parse_bool(os.environ.get("SEED_HAS_KVM"), detected_has_kvm),
    }


def resolve_runtime_profile(requested_profile: str, capabilities: Dict[str, object]) -> Tuple[str, str]:
    normalized_requested = requested_profile.lower()
    if normalized_requested not in VALID_RUNTIME_PROFILES:
        raise ValueError(
            f"Invalid SEED_RUNTIME_PROFILE '{requested_profile}'. "
            f"Supported values: {sorted(VALID_RUNTIME_PROFILES)}"
        )

    arch = str(capabilities["arch"])
    has_kvm = bool(capabilities["has_kvm"])

    if normalized_requested == "auto":
        if arch == "arm64" and not has_kvm:
            return "degraded", "auto fallback: arm64 host without /dev/kvm"
        return "full", "auto selected full profile"

    if normalized_requested == "strict":
        if arch == "arm64" and not has_kvm:
            raise RuntimeError(
                "strict profile requires VM mode, but detected arm64 host without /dev/kvm"
            )
        return "full", "strict profile enforces VM mode"

    if normalized_requested == "full":
        return "full", "explicit full profile"

    return "degraded", "explicit degraded profile"


def apply_router_profile(as150_router, resolved_profile: str) -> str:
    virtualization_mode = "KubeVirt" if resolved_profile == "full" else "Container"
    as150_router.setVirtualizationMode(virtualization_mode)
    return virtualization_mode


def run():
    cluster_name = os.environ.get("SEED_CLUSTER_NAME", "seedemu-kvtest")
    namespace = os.environ.get("SEED_NAMESPACE", "seedemu-kvtest")
    registry_prefix = os.environ.get("SEED_REGISTRY", "localhost:5001")
    vm_node = os.environ.get("SEED_VM_NODE", f"{cluster_name}-control-plane")
    worker_a = os.environ.get("SEED_WORKER_A", f"{cluster_name}-worker")
    worker_b = os.environ.get("SEED_WORKER_B", f"{cluster_name}-worker2")

    requested_runtime_profile = os.environ.get("SEED_RUNTIME_PROFILE", "auto")
    host_capabilities = detect_host_capabilities()
    resolved_runtime_profile, profile_reason = resolve_runtime_profile(
        requested_runtime_profile,
        host_capabilities,
    )

    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    web = WebService()

    base.createInternetExchange(100)

    as150 = base.createAutonomousSystem(150)
    as150.createNetwork("net0")
    as150_router = as150.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    router_virtualization_mode = apply_router_profile(as150_router, resolved_runtime_profile)
    as150.createHost("web").joinNetwork("net0")
    web.install("web150")
    emu.addBinding(Binding("web150", filter=Filter(nodeName="web", asn=150)))

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork("net0")
    as151.createRouter("router0").joinNetwork("net0").joinNetwork("ix100")
    as151.createHost("web").joinNetwork("net0")
    web.install("web151")
    emu.addBinding(Binding("web151", filter=Filter(nodeName="web", asn=151)))

    ebgp.addRsPeer(100, 150)
    ebgp.addRsPeer(100, 151)

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(web)
    emu.render()

    node_labels = {
        "150_router0": {"kubernetes.io/hostname": vm_node},
        "150_web": {"kubernetes.io/hostname": worker_a},
        "151_router0": {"kubernetes.io/hostname": worker_b},
        "151_web": {"kubernetes.io/hostname": worker_b},
        "100_ix100": {"kubernetes.io/hostname": worker_a},
    }

    k8s = KubernetesCompiler(
        registry_prefix=registry_prefix,
        namespace=namespace,
        use_multus=True,
        internetMapEnabled=False,
        scheduling_strategy=SchedulingStrategy.CUSTOM,
        node_labels=node_labels,
        default_resources={
            "requests": {"cpu": "100m", "memory": "128Mi"},
            "limits": {"cpu": "500m", "memory": "1Gi"},
        },
        cni_type="bridge",
        generate_services=True,
        image_pull_policy="Always",
    )

    output_dir = os.path.join(os.path.dirname(__file__), "output_kubevirt_hybrid")
    emu.compile(k8s, output_dir, override=True)

    profile_summary = {
        "requested_profile": requested_runtime_profile.lower(),
        "resolved_profile": resolved_runtime_profile,
        "reason": profile_reason,
        "host": host_capabilities,
        "router_virtualization_mode": router_virtualization_mode,
        "cluster_name": cluster_name,
        "namespace": namespace,
    }

    profile_summary_path = os.path.join(output_dir, "runtime_profile.json")
    with open(profile_summary_path, "w", encoding="utf-8") as profile_file:
        json.dump(profile_summary, profile_file, indent=2, sort_keys=True)

    print(f"Output directory: {output_dir}")
    print(f"Namespace: {namespace}")
    print(f"Runtime profile: {requested_runtime_profile.lower()} -> {resolved_runtime_profile}")
    print(f"Profile reason: {profile_reason}")
    print(f"Router virtualization mode: {router_virtualization_mode}")
    print(f"Profile summary: {profile_summary_path}")
    print("Next steps:")
    print(f"  cd {output_dir}")
    print("  ./build_images.sh")
    print(f"  kubectl create ns {namespace} --dry-run=client -o yaml | kubectl apply -f -")
    print("  kubectl apply -f k8s.yaml")


if __name__ == "__main__":
    run()

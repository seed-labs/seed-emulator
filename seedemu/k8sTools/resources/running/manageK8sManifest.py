#!/usr/bin/env python3
"""Resolve running-stage configuration and render deploy helper artifacts.

Inputs:
- configRunning.yaml, which points to configK3s.yaml and compile output.
- configK3s.yaml, whose master node provides the default registry/SSH target.
- k8s.kube-ovn.yaml or k8s.yaml plus images.yaml from compile output.

Outputs:
- scalar values consumed by manageRunningStage.py,
- kustomization.yaml image mappings,
- manifest-derived namespace and deployment names.
"""
from __future__ import annotations

import argparse
import getpass
import hashlib
import ipaddress
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml


_LOCAL_IPS: set[str] | None = None
VLAN_ID_ANNOTATION = "org.seedsecuritylabs.seedemu.meta.vlan-id"
VLAN_BASE_ANNOTATION = "org.seedsecuritylabs.seedemu.meta.vlan-base-interface"
VLAN_MASTER_ANNOTATION = "org.seedsecuritylabs.seedemu.meta.vlan-master-interface"
VLAN_BRIDGE_ANNOTATION = "org.seedsecuritylabs.seedemu.meta.vlan-bridge-interface"


def load_yaml(path: str) -> dict[str, Any]:
    """Load a YAML mapping from path."""
    data = yaml.safe_load(Path(path).expanduser().read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid YAML root in {path}: expected mapping")
    return data


def readLocalIps() -> set[str]:
    """Return IP addresses assigned to the host running the running scripts."""
    global _LOCAL_IPS
    if _LOCAL_IPS is not None:
        return _LOCAL_IPS
    ips = {"127.0.0.1", "::1", "localhost"}
    try:
        output = subprocess.check_output(
            ["ip", "-o", "addr", "show"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        for line in output.splitlines():
            for token in line.split():
                if "/" not in token:
                    continue
                address = token.split("/", 1)[0]
                if address and (address[0].isdigit() or ":" in address):
                    ips.add(address)
    except Exception:
        pass
    _LOCAL_IPS = ips
    return ips


def get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Read a dotted path from YAML, accepting camelCase and snake_case keys."""
    cur: Any = data
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        candidates = [part, snake_case(part), camel_case(part)]
        found = False
        for candidate in candidates:
            if candidate in cur:
                cur = cur[candidate]
                found = True
                break
        if not found:
            return default
    return cur


def normalizeNetworkValue(value: Any) -> str:
    """Normalize a network backend or CNI value from YAML/compiler metadata."""
    return str(value or "").strip().lower().replace("_", "-")


def networkBackendForCni(value: Any) -> str:
    """Return the running backend implied by a compiler CNI value."""
    normalized = normalizeNetworkValue(value)
    if normalized in {"kube-ovn", "ovn"}:
        return "kube-ovn"
    return normalized or "macvlan"


def loadCompileNetworking(output_dir: Path) -> dict[str, Any]:
    """Read output/networking.yaml written by the compiler, if present."""
    metadata_path = output_dir / "networking.yaml"
    if not metadata_path.exists():
        return {}
    data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def resolveCompileNetworkBackend(
    compile_networking: dict[str, Any],
    fallback: str,
) -> str:
    """Resolve the backend, giving compile-time CNI metadata priority."""
    cni_type = normalizeNetworkValue(compile_networking.get("cniType"))
    network_backend = normalizeNetworkValue(compile_networking.get("networkBackend"))
    if cni_type:
        return networkBackendForCni(cni_type)
    if network_backend:
        return networkBackendForCni(network_backend)
    return networkBackendForCni(fallback)


def normalizeRole(role: Any) -> str:
    """Normalize a configK3s.yaml node role for master-node detection.

    Args:
        role: Raw YAML role value from one node item.
    """
    return str(role or "").strip().lower()


def getSetupNodes(setup: dict[str, Any]) -> list[dict[str, Any]]:
    """Return node mappings from configK3s.yaml.

    Args:
        setup: Parsed configK3s.yaml mapping.
    """
    nodes = setup.get("nodes") or []
    if not isinstance(nodes, list):
        raise SystemExit("configK3s.yaml field nodes must be a list")
    invalid = [node for node in nodes if not isinstance(node, dict)]
    if invalid:
        raise SystemExit(f"configK3s.yaml node item must be a mapping: {invalid[0]}")
    return nodes


def resolveNodeName(node: dict[str, Any], role: str, worker_index: int) -> str:
    """Return the Kubernetes node-name used by the setup stage.

    Args:
        node: Raw configK3s.yaml node mapping.
        role: Normalized node role.
        worker_index: 1-based worker index for unnamed worker nodes.
    """
    name = node.get("name")
    if name:
        return str(name)
    if role in {"master", "server", "control-plane", "control_plane"}:
        return "seed-k3s-master"
    return f"seed-k3s-worker{worker_index}"


def resolveNodeSshUser(setup: dict[str, Any], node: dict[str, Any]) -> str:
    """Return SSH user for one node, with top-level ssh.user fallback."""
    return str(get_nested(node, "ssh.user") or get_nested(setup, "ssh.user") or "ubuntu")


def resolveNodeSshKey(setup: dict[str, Any], node: dict[str, Any]) -> str:
    """Return SSH key for one node, with top-level ssh.key fallback."""
    return str(Path(str(get_nested(node, "ssh.key") or get_nested(setup, "ssh.key") or "~/.ssh/id_ed25519")).expanduser())


def resolveNodeConnection(node: dict[str, Any], ip: str, ssh_user: str) -> str:
    """Return local/ssh connection mode for one node.

    Args:
        node: Raw configK3s.yaml node mapping.
        ip: Node management IP.
        ssh_user: Resolved SSH user.
    """
    raw = node.get("connection") or node.get("connect")
    if raw:
        value = str(raw).strip().lower()
        if value in {"local", "localhost"}:
            return "local"
        if value in {"ssh", "remote"}:
            return "ssh"
        raise SystemExit(f"Unsupported node connection for {ip}: {raw}")
    if node.get("local") is True:
        return "local"
    if ip in readLocalIps() and ssh_user == getpass.getuser():
        return "local"
    return "ssh"


def resolvedSetupNodes(setup: dict[str, Any]) -> list[dict[str, str]]:
    """Return normalized node access records from configK3s.yaml."""
    records: list[dict[str, str]] = []
    worker_index = 0
    for node in getSetupNodes(setup):
        role = normalizeRole(node.get("role"))
        if role in {"worker", "agent"}:
            worker_index += 1
        name = resolveNodeName(node, role, worker_index)
        ip = str(node.get("ip") or node.get("managementIp") or node.get("management_ip") or "")
        if not ip:
            raise SystemExit(f"configK3s.yaml node requires ip: {node}")
        ssh_user = resolveNodeSshUser(setup, node)
        ssh_key = resolveNodeSshKey(setup, node)
        records.append(
            {
                "name": name,
                "role": role,
                "ip": ip,
                "sshUser": ssh_user,
                "sshKey": ssh_key,
                "connection": resolveNodeConnection(node, ip, ssh_user),
            }
        )
    return records


def findMasterNode(setup: dict[str, Any]) -> dict[str, Any] | None:
    """Find the single master node used as the registry and build SSH target.

    Args:
        setup: Parsed configK3s.yaml mapping.
    """
    masters = [
        node
        for node in resolvedSetupNodes(setup)
        if normalizeRole(node.get("role")) in {"master", "server", "control-plane", "control_plane"}
    ]
    if len(masters) > 1:
        names = ", ".join(str(node.get("name") or node.get("ip") or "<unnamed>") for node in masters)
        raise SystemExit(f"configK3s.yaml must contain exactly one master node, got {len(masters)}: {names}")
    return masters[0] if masters else None


def resolveRegistryHost(setup: dict[str, Any], master_node: dict[str, Any] | None) -> str:
    """Resolve registry host from explicit registry.host or master node IP.

    Args:
        setup: Parsed configK3s.yaml mapping.
        master_node: Master node mapping returned by findMasterNode().
    """
    explicit_host = get_nested(setup, "registry.host")
    if explicit_host:
        return str(explicit_host)
    if master_node and master_node.get("ip"):
        return str(master_node["ip"])
    raise SystemExit("Cannot resolve registry host: set registry.host or provide one role=master node with ip")


def resolveSshUser(setup: dict[str, Any], master_node: dict[str, Any] | None) -> str:
    """Resolve SSH user for the registry/build host.

    Args:
        setup: Parsed configK3s.yaml mapping.
        master_node: Master node mapping returned by findMasterNode().
    """
    explicit_user = get_nested(setup, "ssh.user")
    if explicit_user:
        return str(explicit_user)
    master_user = (master_node or {}).get("sshUser") or get_nested(master_node or {}, "ssh.user")
    if master_user:
        return str(master_user)
    return "ubuntu"


def resolveSshKey(setup: dict[str, Any], master_node: dict[str, Any] | None) -> str:
    """Resolve SSH private key path for the registry/build host.

    Args:
        setup: Parsed configK3s.yaml mapping.
        master_node: Master node mapping returned by findMasterNode().
    """
    explicit_key = get_nested(setup, "ssh.key")
    if explicit_key:
        return str(Path(str(explicit_key)).expanduser())
    master_key = (master_node or {}).get("sshKey") or get_nested(master_node or {}, "ssh.key")
    if master_key:
        return str(Path(str(master_key)).expanduser())
    return str(Path("~/.ssh/id_ed25519").expanduser())


def running_context(config_path: str) -> dict[str, str]:
    """Resolve all running-stage values from configRunning.yaml."""
    running_config_path = Path(config_path).expanduser().resolve()
    running = load_yaml(str(running_config_path))
    setup_config_path = Path(str(running.get("setupConfig") or running_config_path.parent / "../setup/configK3s.yaml")).expanduser()
    if not setup_config_path.is_absolute():
        setup_config_path = (running_config_path.parent / setup_config_path).resolve()
    setup = load_yaml(str(setup_config_path)) if setup_config_path.exists() else {}
    output_dir = Path(str(running.get("outputDir") or running_config_path.parent / "../output")).expanduser()
    if not output_dir.is_absolute():
        output_dir = (running_config_path.parent / output_dir).resolve()
    master_node = findMasterNode(setup) if setup else None
    cluster_name = str(setup.get("clusterName") or setup.get("cluster_name") or "seedemu-k3s")
    registry_host = resolveRegistryHost(setup, master_node)
    registry_port = str(get_nested(setup, "registry.port", "5000"))
    fabric_type = normalizeNetworkValue(get_nested(setup, "fabric.type", "none"))
    compile_networking = loadCompileNetworking(output_dir)
    default_network_backend = "kube-ovn" if fabric_type in {"ovn", "kube-ovn"} else "macvlan"
    network_backend = resolveCompileNetworkBackend(compile_networking, default_network_backend)
    manifest_path = resolveManifestPath(running, output_dir, network_backend)
    default_cni_master = (
        str(get_nested(setup, "fabric.bridgeName", "br-seedemu"))
        if fabric_type in {"linux-vxlan", "vxlan", "linux_vxlan"}
        else "ens2"
    )
    attached_cni_type = str(
        get_nested(
            setup,
            "cni.attachedCniType",
            get_nested(
                setup,
                "cni.localLinkCniType",
                get_nested(
                    setup,
                    "fabric.attachedCniType",
                    os.environ.get("SEED_LOCAL_LINK_CNI_TYPE", "kube-ovn"),
                ),
            ),
        )
    )
    compile_cni_type = normalizeNetworkValue(compile_networking.get("cniType"))
    if compile_cni_type and network_backend != "kube-ovn":
        attached_cni_type = compile_cni_type
    raw_cni_mtu = get_nested(
        setup,
        "cni.mtu",
        get_nested(setup, "fabric.mtu", compile_networking.get("cniMtu", 1400)),
    )
    try:
        cni_mtu = int(raw_cni_mtu or 1400)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"CNI MTU must be an integer, got {raw_cni_mtu!r}") from exc
    if cni_mtu < 576 or cni_mtu > 65535:
        raise SystemExit(f"CNI MTU must be in range 576..65535, got {cni_mtu}")
    return {
        "setupConfig": str(setup_config_path),
        "outputDir": str(output_dir),
        "manifest": str(manifest_path),
        "imagesYaml": str(resolveImagesPath(output_dir)),
        "kustomization": str(output_dir / "kustomization.yaml"),
        "imageRegistryPrefix": str(running.get("imageRegistryPrefix") or "seedemu"),
        "registryPrefix": f"{registry_host}:{registry_port}",
        "kubeconfig": str(
            Path(
                str(
                    get_nested(
                        setup,
                        "outputs.kubeconfig",
                        setup_config_path.parent / f"{cluster_name}.kubeconfig.yaml",
                    )
                )
            ).expanduser()
        ),
        "sshUser": resolveSshUser(setup, master_node),
        "sshKey": resolveSshKey(setup, master_node),
        "masterConnection": str((master_node or {}).get("connection") or "ssh"),
        "cniMasterInterface": str(get_nested(setup, "cni.defaultMasterInterface", default_cni_master)),
        "cniMtu": str(cni_mtu),
        "networkBackend": network_backend,
        "attachedCniType": attached_cni_type,
        "rolloutTimeoutSeconds": str(running.get("rolloutTimeoutSeconds") or "1800"),
    }


def resolveManifestPath(running: dict[str, Any], output_dir: Path, network_backend: str) -> Path:
    """Resolve the compile manifest consumed by the running stage.

    Args:
        running: Parsed configRunning.yaml mapping.
        output_dir: Compile output directory.
        network_backend: Resolved backend, for example macvlan or kube-ovn.

    Kube-OVN compiler output is allowed to skip the historical k8s.yaml
    intermediate and write k8s.kube-ovn.yaml directly. The fallback keeps older
    compile outputs working.
    """
    configured = running.get("manifest")
    if configured:
        manifest_path = Path(str(configured)).expanduser()
        if not manifest_path.is_absolute():
            manifest_path = (output_dir / manifest_path).resolve()
        return manifest_path

    kube_ovn_manifest = output_dir / "k8s.kube-ovn.yaml"
    default_manifest = output_dir / "k8s.yaml"
    if network_backend in {"kube-ovn", "ovn"} and kube_ovn_manifest.exists():
        return kube_ovn_manifest
    return default_manifest


def resolveImagesPath(output_dir: Path) -> Path:
    """Return the generated image metadata file for the compile output.

    Args:
        output_dir: Compile output directory.
    """
    images_yaml = output_dir / "images.yaml"
    if images_yaml.exists():
        return images_yaml
    return output_dir / "images.txt"


def config_value(args: argparse.Namespace) -> None:
    """Print one resolved value from configRunning.yaml."""
    values = running_context(args.config)
    if args.key not in values:
        raise SystemExit(f"Unknown config key: {args.key}")
    print(values[args.key])


def node_access(args: argparse.Namespace) -> None:
    """Print node access rows consumed by preflight/build scripts."""
    running_config_path = Path(args.config).expanduser().resolve()
    running = load_yaml(str(running_config_path))
    setup_config_path = Path(str(running.get("setupConfig") or running_config_path.parent / "../setup/configK3s.yaml")).expanduser()
    if not setup_config_path.is_absolute():
        setup_config_path = (running_config_path.parent / setup_config_path).resolve()
    setup = load_yaml(str(setup_config_path))
    records = resolvedSetupNodes(setup)
    if args.name:
        records = [record for record in records if record["name"] == args.name]
        if not records:
            raise SystemExit(f"node not found in configK3s.yaml: {args.name}")
    for record in records:
        print(
            "\t".join(
                [
                    record["name"],
                    record["ip"],
                    record["connection"],
                    record["sshUser"],
                    record["sshKey"],
                ]
            )
        )


def split_repo_tag(image: str) -> tuple[str, str]:
    tail = image.rsplit("/", 1)[-1]
    if ":" in tail:
        return image.rsplit(":", 1)
    return image, "latest"


def strip_prefix(image: str, prefix: str) -> str:
    prefix = prefix.rstrip("/")
    if image.startswith(prefix + "/"):
        return image[len(prefix) + 1 :]
    return image.split("/", 1)[-1]


def load_images(path: str) -> list[dict[str, str]]:
    """Load image metadata from images.yaml or legacy images.txt.

    Args:
        path: Compiler image metadata file.
    """
    image_path = Path(path)
    text = image_path.read_text(encoding="utf-8")
    if image_path.name == "images.txt":
        return imagesFromText(text)
    data = yaml.safe_load(text) or {}
    if isinstance(data, dict):
        images = data.get("images", [])
        if isinstance(images, list):
            return images
    return imagesFromText(text)


def imagesFromText(text: str) -> list[dict[str, str]]:
    """Parse one-image-reference-per-line metadata from KubernetesCompiler.

    Args:
        text: Contents of images.txt.
    """
    images: list[dict[str, str]] = []
    for line in text.splitlines():
        image = line.strip()
        if not image or image.startswith("#"):
            continue
        images.append({"name": image, "context": contextFromImage(image)})
    return images


def contextFromImage(image: str) -> str:
    """Infer a Docker build context directory from an image reference.

    Args:
        image: Full image reference generated by the compiler.
    """
    repo = image.rsplit("/", 1)[-1]
    if ":" in repo:
        repo = repo.rsplit(":", 1)[0]
    return repo


def mapped_images(args: argparse.Namespace) -> None:
    registry = args.registry_prefix.rstrip("/")
    logical_prefix = args.image_registry_prefix.rstrip("/")
    for item in load_images(args.images_yaml):
        logical = item["name"].strip()
        context = item["context"].strip()
        print(f"{registry}/{strip_prefix(logical, logical_prefix)}\t{context}")


def render_kustomization(args: argparse.Namespace) -> None:
    """Render kustomization.yaml for images and network backend adaptation.

    Args:
        args.images_yaml: images.yaml generated by compile.
        args.manifest: Manifest generated by compile.
        args.image_registry_prefix: Logical compiler image prefix.
        args.registry_prefix: Real registry host:port.
        args.network_backend: "macvlan" or "kube-ovn".
        args.cni_master_interface: Optional macvlan parent interface override.
        args.cni_mtu: Macvlan interface MTU selected by the deployment config.
        args.output: Destination kustomization.yaml.
    """
    registry = args.registry_prefix.rstrip("/")
    logical_prefix = args.image_registry_prefix.rstrip("/")
    images = []
    for item in load_images(args.images_yaml):
        logical = item["name"].strip()
        repo, tag = split_repo_tag(strip_prefix(logical, logical_prefix))
        logical_repo, _ = split_repo_tag(logical)
        images.append({"name": logical_repo, "newName": f"{registry}/{repo}", "newTag": tag})
    output_path = Path(args.output)
    manifest_path = Path(args.manifest)
    network_backend = str(args.network_backend or "macvlan").strip().lower()
    if network_backend in {"kube-ovn", "ovn"}:
        rendered_manifest = output_path.parent / "k8s.kube-ovn.yaml"
        if manifest_path.resolve() != rendered_manifest.resolve():
            renderKubeOvnManifest(
                args.manifest,
                rendered_manifest,
                attached_cni_type=args.attached_cni_type,
                cni_master_interface=args.cni_master_interface,
                cni_mtu=args.cni_mtu,
            )
        payload = {"resources": [rendered_manifest.name], "images": images}
    else:
        payload = {"resources": namespaceResources(manifest_path, output_path.parent) + ["k8s.yaml"], "images": images}
        patches = networkAttachmentPatches(
            args.manifest,
            args.cni_master_interface,
            args.cni_mtu,
        )
        if patches:
            payload["patches"] = patches
    output_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def renderKubeOvnManifest(
    manifest_path: str,
    output_path: Path,
    attached_cni_type: str | None = None,
    cni_master_interface: str | None = None,
    cni_mtu: int | None = None,
) -> None:
    """Render a SeedEMU manifest that uses Kube-OVN managed secondary networks.

    Args:
        manifest_path: Source k8s.yaml generated by the compiler.
        output_path: Destination manifest referenced by kustomization.yaml.
        attached_cni_type: Secondary CNI type. ``kube-ovn`` creates overlay
            attached NICs; ``macvlan`` keeps macvlan dataplane and uses
            Kube-OVN only for IPAM.
        cni_master_interface: Optional macvlan master interface override.
        cni_mtu: Optional macvlan interface MTU override.

    The compiler emits macvlan NADs plus Multus network-selection annotations
    with static `ips` values in CIDR form. The renderer creates matching
    Subnets and rewrites Pod template annotations without changing compiler
    output. In macvlan mode, Kube-OVN acts as the centralized IPAM plugin and
    avoids creating thousands of OVN logical switches/routes for scale tests.
    """
    docs = loadManifestDocs(Path(manifest_path))

    namespace_name = findNamespaceName(docs)
    attached_cni = resolveAttachedCniType(attached_cni_type)
    use_ovn_attached = isKubeOvnAttachedCni(attached_cni)
    vpc_name = kubeOvnResourceName("vpc", namespace_name)
    rendered: list[dict[str, Any]] = []
    vpc_written = False
    namespace_written = any(doc.get("kind") == "Namespace" for doc in docs)
    if not namespace_written:
        rendered.append(namespaceResource(namespace_name))

    for doc in docs:
        if use_ovn_attached and doc.get("kind") == "Namespace" and not vpc_written:
            rendered.append(doc)
            rendered.append(kubeOvnVpc(namespace_name, vpc_name))
            vpc_written = True
            continue
        if doc.get("kind") == "NetworkAttachmentDefinition":
            converted = convertNetworkAttachmentToKubeOvn(
                doc,
                namespace_name,
                vpc_name,
                attached_cni,
                cni_master_interface,
                cni_mtu,
            )
            rendered.extend(converted)
            continue
        convertWorkloadAnnotationsToKubeOvn(doc, namespace_name, attached_cni)
        rendered.append(doc)

    if use_ovn_attached and not vpc_written:
        insert_at = 1 if rendered and rendered[0].get("kind") == "Namespace" else 0
        rendered.insert(insert_at, kubeOvnVpc(namespace_name, vpc_name))

    output_path.write_text(yaml.safe_dump_all(rendered, sort_keys=False), encoding="utf-8")


def namespaceResource(namespace_name: str) -> dict[str, Any]:
    """Return a Kubernetes Namespace resource for compiler outputs without one."""
    return {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": namespace_name}}


def namespaceResources(manifest_path: Path, output_dir: Path) -> list[str]:
    """Write namespace.yaml when the manifest lacks an explicit Namespace.

    Args:
        manifest_path: Source manifest path.
        output_dir: Directory that will contain kustomization.yaml.
    """
    docs = loadManifestDocs(manifest_path)
    if any(doc.get("kind") == "Namespace" for doc in docs):
        return []
    namespace_name = findNamespaceName(docs)
    namespace_path = output_dir / "namespace.yaml"
    namespace_path.write_text(yaml.safe_dump(namespaceResource(namespace_name), sort_keys=False), encoding="utf-8")
    return [namespace_path.name]


def resolveAttachedCniType(attached_cni_type: str | None = None) -> str:
    """Return the configured secondary CNI type for Kube-OVN rendering."""
    value = (
        attached_cni_type
        or os.environ.get("SEED_LOCAL_LINK_CNI_TYPE")
        or os.environ.get("SEED_CNI_TYPE")
        or "kube-ovn"
    )
    return str(value).strip().lower().replace("_", "-")


def loadManifestDocs(manifest_path: Path) -> list[dict[str, Any]]:
    """Load Kubernetes documents from a manifest path.

    Args:
        manifest_path: YAML manifest path.
    """
    with open(manifest_path, "r", encoding="utf-8") as fh:
        return [doc for doc in yaml.safe_load_all(fh) if isinstance(doc, dict)]


def isKubeOvnAttachedCni(attached_cni_type: str) -> bool:
    """Return true when secondary NICs should use the Kube-OVN CNI directly."""
    return attached_cni_type in {"kube-ovn", "ovn"}


def findNamespaceName(docs: list[dict[str, Any]]) -> str:
    """Return the manifest namespace used by SeedEMU workload resources."""
    for doc in docs:
        if doc.get("kind") == "Namespace":
            name = (doc.get("metadata") or {}).get("name")
            if name:
                return str(name)
    for doc in docs:
        metadata = doc.get("metadata") or {}
        name = metadata.get("namespace")
        if name:
            return str(name)
    raise SystemExit("Cannot determine namespace for Kube-OVN manifest rendering")


def kubeOvnResourceName(prefix: str, value: str) -> str:
    """Return a DNS-safe Kube-OVN cluster-scoped resource name."""
    safe = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in value.lower()).strip("-")
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    base = f"{prefix}-{digest}-{safe}"
    return base[:63].rstrip("-")


def kubeOvnVpc(namespace_name: str, vpc_name: str) -> dict[str, Any]:
    """Return a Kube-OVN Vpc that isolates one SeedEMU namespace."""
    return {
        "apiVersion": "kubeovn.io/v1",
        "kind": "Vpc",
        "metadata": {"name": vpc_name},
        "spec": {"namespaces": [namespace_name]},
    }


def convertNetworkAttachmentToKubeOvn(
    doc: dict[str, Any],
    default_namespace: str,
    vpc_name: str,
    attached_cni_type: str,
    cni_master_interface: str | None,
    cni_mtu: int | None,
) -> list[dict[str, Any]]:
    """Return [Subnet, NAD] for one compiler-generated macvlan NAD.

    Args:
        doc: Original NetworkAttachmentDefinition document.
        default_namespace: Namespace to use when the NAD omits metadata.namespace.
        vpc_name: Namespace-scoped Kube-OVN VPC name.
        attached_cni_type: Secondary CNI type, for example kube-ovn or macvlan.
        cni_master_interface: Optional macvlan parent interface override.
        cni_mtu: Optional macvlan interface MTU override.
    """
    metadata = doc.get("metadata") or {}
    nad_name = str(metadata.get("name") or "")
    namespace_name = str(metadata.get("namespace") or default_namespace)
    if not nad_name:
        return [doc]
    annotations = metadata.get("annotations") or {}
    prefix = annotations.get("org.seedsecuritylabs.seedemu.meta.prefix")
    if not prefix:
        raise SystemExit(f"NAD {namespace_name}/{nad_name} lacks SeedEMU prefix annotation")

    use_ovn_attached = isKubeOvnAttachedCni(attached_cni_type)
    provider = kubeOvnProviderName(nad_name, namespace_name, attached_cni_type)
    subnet_name = kubeOvnResourceName("subnet", f"{namespace_name}-{nad_name}")
    subnet = {
        "apiVersion": "kubeovn.io/v1",
        "kind": "Subnet",
        "metadata": {"name": subnet_name},
        "spec": {
            "protocol": "IPv4",
            "provider": provider,
            "cidrBlock": str(prefix),
            "gateway": firstUsableIp(str(prefix)),
            "natOutgoing": False,
            "private": False,
        },
    }
    if use_ovn_attached:
        subnet["spec"]["vpc"] = vpc_name
        subnet["spec"]["gatewayType"] = "distributed"

    converted = dict(doc)
    converted["spec"] = {
        "config": renderConvertedNadConfig(
            doc,
            provider,
            attached_cni_type,
            cni_master_interface,
            cni_mtu,
        )
    }
    return [subnet, converted]


def renderConvertedNadConfig(
    doc: dict[str, Any],
    provider: str,
    attached_cni_type: str,
    cni_master_interface: str | None,
    cni_mtu: int | None,
) -> str:
    """Return NetworkAttachmentDefinition spec.config for the selected CNI.

    Args:
        doc: Original NetworkAttachmentDefinition document.
        provider: Kube-OVN provider string used to match the Subnet.
        attached_cni_type: Secondary CNI type, for example kube-ovn or macvlan.
        cni_master_interface: Optional macvlan parent interface override.
        cni_mtu: Optional macvlan interface MTU override.
    """
    if isKubeOvnAttachedCni(attached_cni_type):
        config = {
            "cniVersion": "0.3.1",
            "type": "kube-ovn",
            "server_socket": "/run/openvswitch/kube-ovn-daemon.sock",
            "provider": provider,
        }
        return json.dumps(config, separators=(",", ":"))

    spec = doc.get("spec") or {}
    raw_config = spec.get("config")
    try:
        config = json.loads(raw_config) if isinstance(raw_config, str) else {}
    except json.JSONDecodeError:
        config = {}
    if not isinstance(config, dict):
        config = {}
    metadata = doc.get("metadata") or {}
    config.setdefault("cniVersion", "0.3.1")
    config["type"] = attached_cni_type
    if attached_cni_type == "macvlan":
        annotations = (
            metadata.get("annotations")
            if isinstance(metadata.get("annotations"), dict)
            else {}
        )
        # The deployment YAML describes the selected cluster and therefore
        # overrides the compile-time placeholder stored in the manifest.
        base_interface = str(
            cni_master_interface or annotations.get(VLAN_BASE_ANNOTATION) or ""
        ).strip()
        if base_interface:
            config["master"] = macvlanMasterForVlan(
                base_interface,
                readNadVlanId(metadata),
            )
        if cni_mtu is not None:
            config["mtu"] = cni_mtu
        config.setdefault("mode", "bridge")
    config["ipam"] = {
        "type": "kube-ovn",
        "server_socket": "/run/openvswitch/kube-ovn-daemon.sock",
        "provider": provider,
    }
    return json.dumps(config, separators=(",", ":"))


def convertWorkloadAnnotationsToKubeOvn(
    doc: dict[str, Any],
    default_namespace: str,
    attached_cni_type: str,
) -> None:
    """Rewrite Multus static IP annotations for Kube-OVN attached NICs.

    Args:
        doc: Manifest document to mutate in place. Deployments and raw Pods are
            supported because both can contain Multus network annotations.
        default_namespace: Namespace to use when a network selection omits it.
        attached_cni_type: Secondary CNI type, for example kube-ovn or macvlan.

    SeedEMU's compiler writes Multus `ips: ["10.x.x.x/24"]`, which is correct
    for static CNI IPAM. Kube-OVN IPAM uses per-provider annotations and
    expects plain IP values. Raw Pods use `ip_address`; workload templates use
    `ip_pool`, otherwise kube-ovn-controller rejects Deployment pods during
    address allocation.
    """
    kind = str(doc.get("kind") or "")
    annotations = getPodTemplateAnnotations(doc)
    if not annotations:
        return
    raw_networks = annotations.get("k8s.v1.cni.cncf.io/networks")
    if not isinstance(raw_networks, str):
        return
    try:
        networks = json.loads(raw_networks)
    except json.JSONDecodeError:
        return
    if not isinstance(networks, list):
        return

    changed = False
    for item in networks:
        if not isinstance(item, dict):
            continue
        ips = item.pop("ips", None)
        if not ips:
            continue
        nad_name, nad_namespace = parseNetworkSelection(item, default_namespace)
        if not nad_name:
            continue
        ip_values = [stripCidr(str(ip_value)) for ip_value in ips if str(ip_value).strip()]
        if not ip_values:
            continue
        static_field = kubeOvnStaticAddressField(kind)
        provider = kubeOvnProviderName(nad_name, nad_namespace, attached_cni_type)
        subnet_name = kubeOvnResourceName("subnet", f"{nad_namespace}-{nad_name}")
        annotations[f"{provider}.kubernetes.io/{static_field}"] = ",".join(ip_values)
        annotations[f"{provider}.kubernetes.io/logical_switch"] = subnet_name
        changed = True

    if changed:
        annotations["k8s.v1.cni.cncf.io/networks"] = json.dumps(networks, separators=(",", ":"))


def kubeOvnProviderName(nad_name: str, namespace_name: str, attached_cni_type: str) -> str:
    """Return the provider name used by Kube-OVN for one NetworkAttachmentDefinition."""
    provider = f"{nad_name}.{namespace_name}"
    if isKubeOvnAttachedCni(attached_cni_type):
        provider = f"{provider}.ovn"
    return provider


def kubeOvnStaticAddressField(kind: str) -> str:
    """Return the Kube-OVN fixed-address annotation field for a resource kind.

    Args:
        kind: Kubernetes resource kind containing the Multus annotation.
    """
    if kind == "Pod":
        return "ip_address"
    return "ip_pool"


def getPodTemplateAnnotations(doc: dict[str, Any]) -> dict[str, str] | None:
    """Return pod-level annotations from a workload or Pod document.

    Args:
        doc: Kubernetes resource document.
    """
    kind = doc.get("kind")
    if kind == "Pod":
        metadata = doc.setdefault("metadata", {})
        annotations = metadata.setdefault("annotations", {})
        return annotations if isinstance(annotations, dict) else None
    if kind in {"Deployment", "DaemonSet", "StatefulSet", "Job"}:
        template = doc.setdefault("spec", {}).setdefault("template", {})
        metadata = template.setdefault("metadata", {})
        annotations = metadata.setdefault("annotations", {})
        return annotations if isinstance(annotations, dict) else None
    return None


def parseNetworkSelection(item: dict[str, Any], default_namespace: str) -> tuple[str, str]:
    """Return (nad_name, namespace) from one Multus network selection item.

    Args:
        item: One object from `k8s.v1.cni.cncf.io/networks`.
        default_namespace: Namespace fallback when the item omits namespace.
    """
    raw_name = str(item.get("name") or "")
    namespace = str(item.get("namespace") or default_namespace)
    if "/" in raw_name:
        namespace, raw_name = raw_name.split("/", 1)
    return raw_name, namespace


def stripCidr(ip_value: str) -> str:
    """Return the host IP part from a CIDR or plain IP string."""
    return ip_value.strip().split("/", 1)[0]


def firstUsableIp(cidr: str) -> str:
    """Return the first usable IPv4 address in a CIDR block."""
    network = ipaddress.ip_network(cidr, strict=False)
    if network.version != 4:
        raise SystemExit(f"Kube-OVN renderer currently supports IPv4 only: {cidr}")
    hosts = network.hosts()
    try:
        return str(next(hosts))
    except StopIteration:
        return str(network.network_address)


def networkAttachmentPatches(
    manifest_path: str,
    cni_master_interface: str,
    cni_mtu: int | None = None,
) -> list[dict[str, Any]]:
    """Return deployment-specific kustomize patches for macvlan NADs.

    Args:
        manifest_path: Source k8s.yaml path.
        cni_master_interface: Physical parent interface for macvlan networks.
        cni_mtu: Optional macvlan interface MTU override.

    Compile output is intentionally registry/fabric agnostic. The running
    stage rewrites the macvlan parent and MTU, leaving the original k8s.yaml
    untouched and making physical/KVM deployments selectable by YAML.
    """
    if not cni_master_interface and cni_mtu is None:
        return []
    patches: list[dict[str, Any]] = []
    with open(manifest_path, "r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if not isinstance(doc, dict) or doc.get("kind") != "NetworkAttachmentDefinition":
                continue
            metadata = doc.get("metadata") or {}
            name = metadata.get("name")
            if not name:
                continue
            spec = doc.get("spec") or {}
            raw_config = spec.get("config")
            if not isinstance(raw_config, str):
                continue
            try:
                cni_config = json.loads(raw_config)
            except json.JSONDecodeError:
                continue
            if not isinstance(cni_config, dict) or cni_config.get("type") != "macvlan":
                continue
            annotations = (
                metadata.get("annotations")
                if isinstance(metadata.get("annotations"), dict)
                else {}
            )
            vlan_id = readNadVlanId(metadata)
            # Prefer the deployment-stage value selected by configK3s.yaml.
            base_interface = str(
                cni_master_interface or annotations.get(VLAN_BASE_ANNOTATION) or ""
            ).strip()
            target_master = (
                macvlanMasterForVlan(base_interface, vlan_id)
                if vlan_id
                else base_interface
            )
            changed = False
            if target_master and cni_config.get("master") != target_master:
                cni_config["master"] = target_master
                changed = True
            if cni_mtu is not None and cni_config.get("mtu") != cni_mtu:
                cni_config["mtu"] = cni_mtu
                changed = True
            if not changed:
                continue
            target = {
                "group": "k8s.cni.cncf.io",
                "version": "v1",
                "kind": "NetworkAttachmentDefinition",
                "name": str(name),
            }
            namespace_name = metadata.get("namespace")
            if namespace_name:
                target["namespace"] = str(namespace_name)
            patch = [
                {
                    "op": "replace",
                    "path": "/spec/config",
                    "value": json.dumps(cni_config, separators=(",", ":")),
                }
            ]
            patches.append({"target": target, "patch": yaml.safe_dump(patch, sort_keys=False)})
    return patches


def readNadVlanId(metadata: dict[str, Any]) -> int | None:
    """Return the VLAN ID annotation from one NAD metadata block."""
    annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
    raw = annotations.get(VLAN_ID_ANNOTATION)
    if raw in (None, ""):
        return None
    try:
        vlan_id = int(str(raw))
    except ValueError as exc:
        name = metadata.get("name") or "<unknown>"
        raise SystemExit(f"NAD {name} has invalid VLAN ID annotation {raw!r}") from exc
    if vlan_id < 1 or vlan_id > 4094:
        name = metadata.get("name") or "<unknown>"
        raise SystemExit(f"NAD {name} VLAN ID must be in 1..4094, got {vlan_id}")
    return vlan_id


def macvlanMasterForVlan(base_interface: str, vlan_id: int | None) -> str:
    """Return the host interface name used by a macvlan NAD."""
    base = str(base_interface or "").strip()
    if vlan_id is None:
        return base
    if not base:
        raise SystemExit("macvlan VLAN mode requires cni.defaultMasterInterface or --cni-master-interface")
    return f"{base}.{vlan_id}"


def macvlan_vlan_interfaces(args: argparse.Namespace) -> None:
    """Print VLAN subinterfaces required by macvlan NADs as TSV rows."""
    records: dict[tuple[str, int], dict[str, str]] = {}
    with open(args.manifest, "r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if not isinstance(doc, dict) or doc.get("kind") != "NetworkAttachmentDefinition":
                continue
            metadata = doc.get("metadata") or {}
            vlan_id = readNadVlanId(metadata)
            if vlan_id is None:
                continue
            spec = doc.get("spec") or {}
            raw_config = spec.get("config")
            try:
                cni_config = json.loads(raw_config) if isinstance(raw_config, str) else {}
            except json.JSONDecodeError:
                cni_config = {}
            annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
            base_interface = str(args.cni_master_interface or annotations.get(VLAN_BASE_ANNOTATION) or "").strip()
            if not base_interface:
                master = str(cni_config.get("master") or annotations.get(VLAN_MASTER_ANNOTATION) or "")
                suffix = f".{vlan_id}"
                base_interface = master[: -len(suffix)] if master.endswith(suffix) else master
            interface_name = macvlanMasterForVlan(base_interface, vlan_id)
            key = (base_interface, vlan_id)
            records[key] = {
                "interface": interface_name,
                "base": base_interface,
                "vlan": str(vlan_id),
                "namespace": str(metadata.get("namespace") or ""),
                "name": str(metadata.get("name") or ""),
            }
    for _, record in sorted(records.items(), key=lambda item: (item[0][0], item[0][1])):
        print("\t".join([record["interface"], record["base"], record["vlan"], record["namespace"], record["name"]]))


def _macvlan_vlan_record_for_nad(doc: dict[str, Any], cni_master_interface: str) -> dict[str, str] | None:
    """Return one VLAN parent record for a VLAN-backed NAD, or None."""
    metadata = doc.get("metadata") or {}
    vlan_id = readNadVlanId(metadata)
    if vlan_id is None:
        return None
    spec = doc.get("spec") or {}
    raw_config = spec.get("config")
    try:
        cni_config = json.loads(raw_config) if isinstance(raw_config, str) else {}
    except json.JSONDecodeError:
        cni_config = {}
    annotations = metadata.get("annotations") if isinstance(metadata.get("annotations"), dict) else {}
    base_interface = str(cni_master_interface or annotations.get(VLAN_BASE_ANNOTATION) or "").strip()
    if not base_interface:
        master = str(cni_config.get("master") or annotations.get(VLAN_MASTER_ANNOTATION) or "")
        suffix = f".{vlan_id}"
        base_interface = master[: -len(suffix)] if master.endswith(suffix) else master
    interface_name = macvlanMasterForVlan(base_interface, vlan_id)
    bridge_interface = str(annotations.get(VLAN_BRIDGE_ANNOTATION) or cni_config.get("bridge") or "").strip()
    return {
        "interface": interface_name,
        "base": base_interface,
        "vlan": str(vlan_id),
        "bridge": bridge_interface,
        "namespace": str(metadata.get("namespace") or ""),
        "name": str(metadata.get("name") or ""),
    }


def _load_macvlan_vlan_nads(manifest: str, cni_master_interface: str) -> dict[tuple[str, str], dict[str, str]]:
    """Return VLAN-backed NAD records keyed by (namespace, name) and ("", name)."""
    records: dict[tuple[str, str], dict[str, str]] = {}
    with open(manifest, "r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if not isinstance(doc, dict) or doc.get("kind") != "NetworkAttachmentDefinition":
                continue
            record = _macvlan_vlan_record_for_nad(doc, cni_master_interface)
            if record is None:
                continue
            namespace_name = record["namespace"]
            name = record["name"]
            if not name:
                continue
            records[(namespace_name, name)] = record
            records[("", name)] = record
    return records


def _node_selector_hostname(spec: dict[str, Any]) -> str:
    """Return the fixed hostname selector or nodeName from a Pod spec."""
    node_name = spec.get("nodeName")
    if isinstance(node_name, str) and node_name.strip():
        return node_name.strip()
    selector = spec.get("nodeSelector")
    if isinstance(selector, dict):
        value = selector.get("kubernetes.io/hostname")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _workload_pod_template(doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return (template_metadata, pod_spec, namespace) for Pod-like workload docs."""
    kind = str(doc.get("kind") or "")
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    namespace_name = str(metadata.get("namespace") or "")
    if kind == "Pod":
        pod_spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
        return metadata, pod_spec, namespace_name
    if kind not in {"Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet"}:
        return {}, {}, namespace_name
    spec = doc.get("spec") if isinstance(doc.get("spec"), dict) else {}
    template = spec.get("template") if isinstance(spec.get("template"), dict) else {}
    template_metadata = template.get("metadata") if isinstance(template.get("metadata"), dict) else {}
    pod_spec = template.get("spec") if isinstance(template.get("spec"), dict) else {}
    return template_metadata, pod_spec, namespace_name


def _network_attachment_names(raw: str) -> list[tuple[str, str]]:
    """Parse a Multus networks annotation into (namespace, name) references."""
    value = raw.strip()
    if not value:
        return []
    refs: list[tuple[str, str]] = []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                namespace_name = str(item.get("namespace") or "").strip()
                if name:
                    refs.append((namespace_name, name))
            elif isinstance(item, str) and item.strip():
                refs.extend(_network_attachment_names(item))
        return refs
    if isinstance(parsed, dict):
        name = str(parsed.get("name") or "").strip()
        namespace_name = str(parsed.get("namespace") or "").strip()
        return [(namespace_name, name)] if name else []

    for token in value.split(","):
        item = token.strip()
        if not item:
            continue
        if "@" in item:
            item = item.split("@", 1)[0].strip()
        namespace_name = ""
        name = item
        if "/" in item:
            namespace_name, name = [part.strip() for part in item.split("/", 1)]
        if name:
            refs.append((namespace_name, name))
    return refs


def macvlan_vlan_interfaces_by_node(args: argparse.Namespace) -> None:
    """Print node-specific VLAN parent rows needed by scheduled workload Pods."""
    nodes = [node for node in args.nodes if node]
    all_nodes = set(nodes)
    nad_records = _load_macvlan_vlan_nads(args.manifest, args.cni_master_interface)
    if not nad_records:
        return

    by_node: dict[str, dict[tuple[str, int], dict[str, str]]] = {node: {} for node in nodes}
    saw_workload_network = False
    with open(args.manifest, "r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if not isinstance(doc, dict):
                continue
            template_metadata, pod_spec, workload_namespace = _workload_pod_template(doc)
            if not template_metadata and not pod_spec:
                continue
            annotations = template_metadata.get("annotations") if isinstance(template_metadata.get("annotations"), dict) else {}
            networks_raw = annotations.get("k8s.v1.cni.cncf.io/networks")
            if not isinstance(networks_raw, str) or not networks_raw.strip():
                continue
            refs = _network_attachment_names(networks_raw)
            records: list[dict[str, str]] = []
            for namespace_name, name in refs:
                key_namespace = namespace_name or workload_namespace
                record = nad_records.get((key_namespace, name)) or nad_records.get(("", name))
                if record is not None:
                    records.append(record)
            if not records:
                continue
            saw_workload_network = True
            fixed_node = _node_selector_hostname(pod_spec)
            target_nodes = [fixed_node] if fixed_node in all_nodes else nodes
            for node in target_nodes:
                node_records = by_node.setdefault(node, {})
                for record in records:
                    key = (record["base"], int(record["vlan"]))
                    node_records[key] = record

    if not saw_workload_network:
        # Safety fallback for non-standard manifests: create every VLAN parent
        # on every node rather than risking a missing CNI master link.
        unique_records = {
            (record["base"], int(record["vlan"]), record["namespace"], record["name"]): record
            for record in nad_records.values()
        }
        for node in nodes:
            node_records = by_node.setdefault(node, {})
            for record in unique_records.values():
                key = (record["base"], int(record["vlan"]))
                node_records[key] = record

    for node in sorted(by_node):
        for _, record in sorted(by_node[node].items(), key=lambda item: (item[0][0], item[0][1])):
            print(
                "\t".join(
                    [
                        node,
                        record["interface"],
                        record["base"],
                        record["vlan"],
                        record.get("bridge") or "-",
                        record["namespace"],
                        record["name"],
                    ]
                )
            )


def deployment_names(args: argparse.Namespace) -> None:
    with open(args.manifest, "r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if isinstance(doc, dict) and doc.get("kind") == "Deployment":
                name = (doc.get("metadata") or {}).get("name")
                if name:
                    print(name)


def namespace(args: argparse.Namespace) -> None:
    print(findNamespaceName(loadManifestDocs(Path(args.manifest))))


def validate_manifest(args: argparse.Namespace) -> None:
    seen = {}
    duplicate_errors = []
    with open(args.manifest, "r", encoding="utf-8") as fh:
        for index, doc in enumerate(yaml.safe_load_all(fh), 1):
            if not isinstance(doc, dict):
                continue
            kind = doc.get("kind")
            metadata = doc.get("metadata") or {}
            name = metadata.get("name")
            namespace_name = metadata.get("namespace") or ""
            if not kind or not name:
                continue
            key = (kind, namespace_name, name)
            if key in seen:
                duplicate_errors.append(
                    f"{kind}/{name} namespace={namespace_name or '<cluster>'} "
                    f"appears in docs {seen[key]} and {index}"
                )
            else:
                seen[key] = index

    if duplicate_errors:
        print(f"Duplicate Kubernetes resources in {args.manifest}:", flush=True)
        for error in duplicate_errors[:30]:
            print(f"  {error}", flush=True)
        if len(duplicate_errors) > 30:
            print(f"  ... {len(duplicate_errors) - 30} more", flush=True)
        raise SystemExit(1)


def snake_case(value: str) -> str:
    out = []
    for char in value:
        if char.isupper():
            out.append("_")
            out.append(char.lower())
        else:
            out.append(char)
    return "".join(out).lstrip("_")


def camel_case(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    config = subparsers.add_parser("config-value")
    config.add_argument("--config", required=True)
    config.add_argument("--key", required=True)
    config.set_defaults(func=config_value)

    access = subparsers.add_parser("node-access")
    access.add_argument("--config", required=True)
    access.add_argument("--name")
    access.set_defaults(func=node_access)

    mapped = subparsers.add_parser("mapped-images")
    mapped.add_argument("--images-yaml", required=True)
    mapped.add_argument("--image-registry-prefix", required=True)
    mapped.add_argument("--registry-prefix", required=True)
    mapped.set_defaults(func=mapped_images)

    kustomization = subparsers.add_parser("kustomization")
    kustomization.add_argument("--images-yaml", required=True)
    kustomization.add_argument("--manifest", required=True)
    kustomization.add_argument("--image-registry-prefix", required=True)
    kustomization.add_argument("--registry-prefix", required=True)
    kustomization.add_argument("--network-backend", default="macvlan")
    kustomization.add_argument("--cni-master-interface", default="")
    kustomization.add_argument("--cni-mtu", type=int, default=None)
    kustomization.add_argument("--attached-cni-type", default=None)
    kustomization.add_argument("--output", required=True)
    kustomization.set_defaults(func=render_kustomization)

    vlans = subparsers.add_parser("macvlan-vlan-interfaces")
    vlans.add_argument("--manifest", required=True)
    vlans.add_argument("--cni-master-interface", default="")
    vlans.set_defaults(func=macvlan_vlan_interfaces)

    vlans_by_node = subparsers.add_parser("macvlan-vlan-interfaces-by-node")
    vlans_by_node.add_argument("--manifest", required=True)
    vlans_by_node.add_argument("--cni-master-interface", default="")
    vlans_by_node.add_argument("--nodes", nargs="*", default=[])
    vlans_by_node.set_defaults(func=macvlan_vlan_interfaces_by_node)

    deployments = subparsers.add_parser("deployment-names")
    deployments.add_argument("--manifest", required=True)
    deployments.set_defaults(func=deployment_names)

    ns = subparsers.add_parser("namespace")
    ns.add_argument("--manifest", required=True)
    ns.set_defaults(func=namespace)

    validate = subparsers.add_parser("validate-manifest")
    validate.add_argument("--manifest", required=True)
    validate.set_defaults(func=validate_manifest)

    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

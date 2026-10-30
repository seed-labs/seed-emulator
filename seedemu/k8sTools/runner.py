from __future__ import annotations

from contextlib import contextmanager
import shlex
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Any, Iterator

from .config import (
    addK8sToolsMetadata,
    detectKind,
    loadYaml,
    makeKvmConfig,
    makeMultiHostKvmConfig,
    resolvePath,
    setOutputPaths,
    writeYaml,
)
from .utils import chmodScripts, copyTree


def runCommand(args: list[str], *, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    """Run one external command and fail immediately on errors.

    Args:
        args: Command argv. Shell expansion is intentionally avoided.
        cwd: Optional working directory.
    """
    print("+ " + shlex.join(args))
    return subprocess.run(args, cwd=str(cwd) if cwd is not None else None, check=True)


@contextmanager
def temporaryWorkDir(prefix: str, keep_temp: bool = False) -> Iterator[Path]:
    """Create a temporary k8sTools work directory.

    Args:
        prefix: Prefix passed to tempfile.
        keep_temp: Leave the directory on disk for debugging when true.
    """
    if keep_temp:
        root = Path(tempfile.mkdtemp(prefix=prefix))
        print(f"[k8sTools] keeping temporary work directory: {root}")
        yield root
        return
    with tempfile.TemporaryDirectory(prefix=prefix) as tmp:
        yield Path(tmp)


def inferImageRegistryPrefix(output_dir: Path) -> str:
    """Infer the compiler image prefix from generated image metadata.

    Args:
        output_dir: Compile output directory containing images.yaml or images.txt.
    """
    images_path = output_dir / "images.yaml"
    if images_path.exists():
        data = loadYaml(images_path)
        images = data.get("images") if isinstance(data.get("images"), list) else []
        for item in images:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if "/" in name:
                return name.rsplit("/", 1)[0]
        return "seedemu"

    images_txt = output_dir / "images.txt"
    if images_txt.exists():
        for line in images_txt.read_text(encoding="utf-8").splitlines():
            name = line.strip()
            if not name or name.startswith("#"):
                continue
            if "/" in name:
                return name.rsplit("/", 1)[0]
            return "seedemu"
    return "seedemu"


def buildCluster(
    input_config: str | Path,
    config_k3s: str | Path,
    kubeconfig: str | Path,
    *,
    inventory: str | Path | None = None,
    keep_temp: bool = False,
) -> None:
    """Build KVM/physical infrastructure and write final config outputs.

    Args:
        input_config: User YAML with explicit `kind`.
        config_k3s: Final configK3s.yaml path requested by the user.
        kubeconfig: Final kubeconfig path requested by the user.
        inventory: Optional final cluster inventory YAML path requested by the user.
        keep_temp: Keep temporary setup resources for debugging.

    The first-phase implementation expands bundled setup resources into a
    temporary directory, reuses the existing resource scripts there, copies the
    resulting config back to the requested paths, and removes the temporary
    directory. No persistent setup/running directory is created.
    """
    input_path = resolvePath(input_config)
    config_path = resolvePath(config_k3s)
    kubeconfig_path = resolvePath(kubeconfig)
    inventory_path = resolvePath(inventory) if inventory is not None else None
    source = loadYaml(input_path)
    kind = detectKind(source, input_path)

    with temporaryWorkDir("seedemu-k8s-tools-build-", keep_temp) as root:
        setup_dir = copyTree("setup", root / "setup", overwrite=True)
        chmodScripts(setup_dir)
        if kind == "kvmOvn":
            _buildKvmOvn(setup_dir, input_path, config_path, kubeconfig_path, inventory_path)
        elif kind == "multiHostKvmOvn":
            _buildMultiHostKvmOvn(setup_dir, input_path, config_path, kubeconfig_path, inventory_path)
        elif kind == "physicalOvn":
            _buildPhysicalOvn(setup_dir, input_path, config_path, kubeconfig_path, inventory_path)
        else:
            raise ValueError(f"unsupported kind: {kind}")


def deployWorkload(
    output_dir: str | Path,
    kubeconfig: str | Path,
    config_k3s: str | Path,
    *,
    image_registry_prefix: str | None = None,
    keep_temp: bool = False,
) -> None:
    """Run preflight, image build/push, deploy, and wait for workload readiness.

    Args:
        output_dir: Compile output directory containing images.yaml and k8s.yaml.
        kubeconfig: Kubeconfig used by kubectl.
        config_k3s: configK3s.yaml used to resolve registry and network backend.
        image_registry_prefix: Logical compiler image prefix. If omitted, it
            is inferred from images.yaml.
        keep_temp: Keep temporary running resources for debugging.
    """
    output_path = resolvePath(output_dir)
    kubeconfig_path = resolvePath(kubeconfig)
    config_path = resolvePath(config_k3s)
    logical_image_prefix = image_registry_prefix or inferImageRegistryPrefix(output_path)
    with temporaryWorkDir("seedemu-k8s-tools-running-", keep_temp) as root:
        running_dir = copyTree("running", root / "running", overwrite=True)
        chmodScripts(running_dir)
        config_copy = root / "configK3s.yaml"
        setup_config = loadYaml(config_path)
        setup_config.setdefault("outputs", {})["kubeconfig"] = str(kubeconfig_path)
        writeYaml(config_copy, setup_config)
        writeYaml(
            running_dir / "configRunning.yaml",
            {
                "setupConfig": str(config_copy),
                "outputDir": str(output_path),
                "imageRegistryPrefix": logical_image_prefix,
                "rolloutTimeoutSeconds": 1800,
            },
        )
        stage = running_dir / "manageRunningStage.py"
        running_config = running_dir / "configRunning.yaml"
        runCommand(["python3", str(stage), "--config", str(running_config), "preflight"], cwd=running_dir)
        runCommand(["python3", str(stage), "--config", str(running_config), "build"], cwd=running_dir)
        runCommand(["python3", str(stage), "--config", str(running_config), "up"], cwd=running_dir)


def cleanWorkload(output_dir: str | Path, kubeconfig: str | Path, *, keep_temp: bool = False) -> None:
    """Delete workload resources without requiring configK3s.yaml.

    Args:
        output_dir: Compile output directory.
        kubeconfig: Kubeconfig used by kubectl.
        keep_temp: Keep temporary cleanup resources for debugging.
    """
    output_path = resolvePath(output_dir)
    kubeconfig_path = resolvePath(kubeconfig)
    with temporaryWorkDir("seedemu-k8s-tools-clean-", keep_temp) as root:
        running_dir = copyTree("running", root / "running", overwrite=True)
        chmodScripts(running_dir)
        helper = running_dir / "manageK8sManifest.py"
        manifest = output_path / "k8s.kube-ovn.yaml"
        if not manifest.exists():
            manifest = output_path / "k8s.yaml"
        namespace = subprocess.check_output(
            ["python3", str(helper), "namespace", "--manifest", str(manifest)],
            text=True,
        ).strip()
        if (output_path / "kustomization.yaml").exists():
            runCommand(
                [
                    "kubectl",
                    "--kubeconfig",
                    str(kubeconfig_path),
                    "delete",
                    "-k",
                    str(output_path),
                    "--ignore-not-found=true",
                    "--wait=false",
                ]
            )
        runCommand(
            [
                "kubectl",
                "--kubeconfig",
                str(kubeconfig_path),
                "delete",
                "namespace",
                namespace,
                "--ignore-not-found=true",
                "--wait=false",
            ]
        )


def destroyCluster(config_k3s: str | Path, *, keep_temp: bool = False) -> None:
    """Destroy K3s/OVN and optional KVM resources recorded in configK3s.yaml.

    Args:
        config_k3s: configK3s.yaml produced by buildCluster().
        keep_temp: Keep temporary destroy resources for debugging.
    """
    config_path = resolvePath(config_k3s)
    config = loadYaml(config_path)
    destroy = config.get("k8sTools", {}).get("destroy", {})
    destroy_type = str(destroy.get("type") or config.get("kind") or "")
    if not destroy_type:
        raise ValueError(f"{config_path} does not contain k8sTools.destroy metadata")
    with temporaryWorkDir("seedemu-k8s-tools-destroy-", keep_temp) as root:
        setup_dir = copyTree("setup", root / "setup", overwrite=True)
        chmodScripts(setup_dir)
        temp_config = setup_dir / "configK3s.yaml"
        writeYaml(temp_config, config)
        try:
            runCommand(["python3", str(setup_dir / "destroyPhysicalCluster.py"), str(temp_config)], cwd=setup_dir)
        except subprocess.CalledProcessError:
            if destroy_type == "physicalOvn":
                raise
            print("[k8sTools] warning: K3s/OVN cleanup failed; continuing with KVM cleanup")
        if destroy_type == "kvmOvn":
            state = destroy.get("state")
            setup_config = destroy.get("config")
            if not isinstance(state, dict) or not isinstance(setup_config, dict):
                raise ValueError("kvmOvn destroy requires embedded kvm state and config")
            writeYaml(setup_dir / "kvm.yaml", setup_config)
            writeYaml(setup_dir / "kvmState.yaml", state)
            runCommand(["python3", str(setup_dir / "kvm" / "destroyKvmVms.py"), str(setup_dir / "kvmState.yaml")], cwd=setup_dir)
            _removeManagedKvmDataDir(state)
        elif destroy_type == "multiHostKvmOvn":
            state = destroy.get("state")
            if not isinstance(state, dict):
                raise ValueError("multiHostKvmOvn destroy requires embedded multi-host state")
            writeYaml(setup_dir / "multiHostKvmState.yaml", state)
            runCommand(
                [
                    "python3",
                    str(setup_dir / "multiHostKvm" / "destroyMultiHostKvmVms.py"),
                    str(setup_dir / "multiHostKvmState.yaml"),
                ],
                cwd=setup_dir,
            )
        elif destroy_type == "physicalOvn":
            return
        else:
            raise ValueError(f"unsupported destroy type: {destroy_type}")


def _buildKvmOvn(
    setup_dir: Path,
    input_path: Path,
    config_path: Path,
    kubeconfig_path: Path,
    inventory_path: Path | None,
) -> None:
    """Build a single-hypervisor KVM cluster with Kube-OVN."""
    kvm_config = makeKvmConfig(
        config=input_path,
        setup_dir=setup_dir,
        k3s_config_path=setup_dir / "configK3s.yaml",
        kubeconfig_path=kubeconfig_path,
        inventory_path=inventory_path or setup_dir / "cluster.inventory.yaml",
        tmp_dir=setup_dir / "tmp",
    )
    kvm_config.setdefault("fabric", {})["type"] = "ovn"
    _applyOvnK3sDefaults(kvm_config)
    writeYaml(setup_dir / "kvm.yaml", kvm_config)
    runCommand(["python3", str(setup_dir / "kvm" / "prepareHostAssets.py"), str(setup_dir / "kvm.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "kvm" / "createKvmVms.py"), str(setup_dir / "kvm.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "kvm" / "tuneVmLimits.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "applyK3sCluster.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    final_config = loadYaml(setup_dir / "configK3s.yaml")
    addK8sToolsMetadata(
        final_config,
        kind="kvmOvn",
        source_config=input_path,
        kubeconfig=kubeconfig_path,
        destroy_type="kvmOvn",
        destroy_state=loadYaml(setup_dir / "kvmState.yaml"),
        destroy_config=kvm_config,
    )
    writeYaml(config_path, final_config)


def _buildMultiHostKvmOvn(
    setup_dir: Path,
    input_path: Path,
    config_path: Path,
    kubeconfig_path: Path,
    inventory_path: Path | None,
) -> None:
    """Build a multi-hypervisor KVM cluster with routed VM subnets and Kube-OVN."""
    source = loadYaml(input_path)
    source.setdefault("fabric", {})["type"] = "ovn"
    _applyOvnK3sDefaults(source)
    outputs = source.setdefault("outputs", {})
    outputs["k3sConfig"] = str(setup_dir / "configK3s.yaml")
    outputs["multiHostKvmState"] = str(setup_dir / "multiHostKvmState.yaml")
    setOutputPaths(
        source,
        kubeconfig=kubeconfig_path,
        tmp_dir=setup_dir / "tmp",
        inventory=inventory_path or setup_dir / "cluster.inventory.yaml",
    )
    temp_input = setup_dir / "multiHostInput.yaml"
    writeYaml(temp_input, source)
    kvm_config = makeMultiHostKvmConfig(config=temp_input, setup_dir=setup_dir)
    writeYaml(setup_dir / "kvm.yaml", kvm_config)
    runCommand(["python3", str(setup_dir / "multiHostKvm" / "prepareKvmHypervisors.py"), str(setup_dir / "kvm.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "multiHostKvm" / "createMultiHostKvmVms.py"), str(setup_dir / "kvm.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "kvm" / "tuneVmLimits.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "applyK3sCluster.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    final_config = loadYaml(setup_dir / "configK3s.yaml")
    addK8sToolsMetadata(
        final_config,
        kind="multiHostKvmOvn",
        source_config=input_path,
        kubeconfig=kubeconfig_path,
        destroy_type="multiHostKvmOvn",
        destroy_state=loadYaml(setup_dir / "multiHostKvmState.yaml"),
        destroy_config=kvm_config,
    )
    writeYaml(config_path, final_config)


def _buildPhysicalOvn(
    setup_dir: Path,
    input_path: Path,
    config_path: Path,
    kubeconfig_path: Path,
    inventory_path: Path | None,
) -> None:
    """Build a K3s + Kube-OVN cluster on existing physical nodes."""
    config = loadYaml(input_path)
    config["kind"] = "physicalOvn"
    config.setdefault("fabric", {})["type"] = "ovn"
    _applyOvnK3sDefaults(config)
    setOutputPaths(
        config,
        kubeconfig=kubeconfig_path,
        tmp_dir=setup_dir / "tmp",
        inventory=inventory_path or setup_dir / "cluster.inventory.yaml",
    )
    writeYaml(setup_dir / "configK3s.yaml", config)
    runCommand(["python3", str(setup_dir / "preparePhysicalNodes.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    runCommand(["python3", str(setup_dir / "applyK3sCluster.py"), str(setup_dir / "configK3s.yaml")], cwd=setup_dir)
    final_config = loadYaml(setup_dir / "configK3s.yaml")
    addK8sToolsMetadata(
        final_config,
        kind="physicalOvn",
        source_config=input_path,
        kubeconfig=kubeconfig_path,
        destroy_type="physicalOvn",
    )
    writeYaml(config_path, final_config)


def _applyOvnK3sDefaults(config: dict[str, Any]) -> None:
    """Set K3s defaults required by the bundled Kube-OVN chart.

    Args:
        config: User input or generated setup config mapping.
    """
    fabric_type = str(config.get("fabric", {}).get("type") if isinstance(config.get("fabric"), dict) else "").lower()
    if fabric_type not in {"ovn", "kube-ovn", "kube_ovn"}:
        return
    k3s = config.setdefault("k3s", {})
    if isinstance(k3s, dict):
        k3s.setdefault("version", "v1.29.15+k3s1")


def _removeManagedKvmDataDir(state: dict[str, Any]) -> None:
    """Remove the k8sTools-managed /data work directory after VM destruction.

    Args:
        state: Embedded kvmState.yaml mapping produced by createKvmVms.py.

    Only directories created from the k8sTools temporary-build naming pattern
    are removed. User-provided KVM storage paths are intentionally preserved.
    """
    kvm = state.get("kvm") if isinstance(state.get("kvm"), dict) else {}
    disk_dir = kvm.get("diskDir")
    if not disk_dir:
        return
    data_dir = Path(str(disk_dir)).expanduser().resolve().parent
    parts = data_dir.parts
    if len(parts) < 4 or parts[1] != "data" or parts[-1].startswith("seedemu-k8s-tools-build-") is False:
        return
    print(f"[k8sTools] removing managed KVM data dir: {data_dir}")
    shutil.rmtree(data_dir, ignore_errors=True)

#!/usr/bin/env python3
"""Run the native Kubernetes workload stage without a Makefile.

The setup stage writes a small ``configRunning.yaml`` that points at:

- ``configK3s.yaml`` for kubeconfig, registry, SSH, and fabric settings.
- the compiler output directory for ``k8s.yaml``/``k8s.kube-ovn.yaml`` and
  ``images.yaml``.

This script intentionally keeps the old Makefile target names as subcommands
(``preflight``, ``build``, ``up``, ``clean``) while implementing the orchestration
in Python. Low-level tools such as ``kubectl``, ``ssh``, ``tar``, and ``docker``
are still executed as external commands because they are the actual system
interfaces for Kubernetes and image builds.
"""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
HELPER = SCRIPT_DIR / "manageK8sManifest.py"


def runCommand(args: list[str], *, cwd: str | Path | None = None, stdin=None) -> subprocess.CompletedProcess:
    """Run one command and fail immediately on non-zero exit.

    Args:
        args: Command argv. Shell expansion is avoided unless the caller
            explicitly invokes a shell program such as ``ssh`` remote command.
        cwd: Optional working directory.
        stdin: Optional stdin pipe for streaming tar data to SSH.
    """
    print("+ " + " ".join(str(arg) for arg in args))
    return subprocess.run(args, cwd=str(cwd) if cwd is not None else None, stdin=stdin, check=True)


def helperOutput(args: list[str]) -> str:
    """Run ``manageK8sManifest.py`` and return stripped stdout.

    Args:
        args: Helper subcommand arguments without the Python executable.
    """
    return subprocess.check_output(["python3", str(HELPER), *args], text=True).strip()


def context(config: Path) -> dict[str, str]:
    """Resolve all running-stage settings from configRunning.yaml.

    Args:
        config: Path to configRunning.yaml.
    """
    keys = [
        "outputDir",
        "manifest",
        "imagesYaml",
        "kustomization",
        "imageRegistryPrefix",
        "registryPrefix",
        "kubeconfig",
        "sshUser",
        "sshKey",
        "masterConnection",
        "cniMasterInterface",
        "networkBackend",
        "attachedCniType",
        "rolloutTimeoutSeconds",
    ]
    return {key: helperOutput(["config-value", "--config", str(config), "--key", key]) for key in keys}


def checkOutput(config: Path) -> dict[str, str]:
    """Validate compiler output and return the resolved running context.

    Args:
        config: Path to configRunning.yaml.
    """
    values = context(config)
    manifest = Path(values["manifest"])
    images_yaml = Path(values["imagesYaml"])
    if not manifest.is_file():
        raise SystemExit(f"Missing {manifest}. Run compile first.")
    if not images_yaml.is_file():
        raise SystemExit(f"Missing {images_yaml}. Run compile first.")
    runCommand(["python3", str(HELPER), "validate-manifest", "--manifest", str(manifest)])
    return values


def preflight(config: Path) -> None:
    """Validate cluster readiness before image build or deployment.

    Args:
        config: Path to configRunning.yaml.
    """
    checkOutput(config)
    runCommand(["python3", str(SCRIPT_DIR / "validateClusterPreflight.py"), "--config", str(config)])


def copyTreeContents(source: Path, target: Path) -> None:
    """Copy one directory's contents into a clean target directory.

    Args:
        source: Existing source directory.
        target: Destination directory to create.
    """
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def streamTarToRemote(source: Path, ssh_command: list[str], remote_extract_command: str) -> None:
    """Stream a local directory to a remote extraction command over SSH.

    Args:
        source: Directory whose contents should be archived.
        ssh_command: Base SSH argv including target host.
        remote_extract_command: Remote shell command that extracts stdin tar.
    """
    print("+ " + " ".join(["tar", "-C", str(source), "-czf", "-", "."]) + " | " + " ".join(ssh_command + [remote_extract_command]))
    producer = subprocess.Popen(["tar", "-C", str(source), "-czf", "-", "."], stdout=subprocess.PIPE)
    try:
        assert producer.stdout is not None
        subprocess.run([*ssh_command, remote_extract_command], stdin=producer.stdout, check=True)
    finally:
        if producer.stdout is not None:
            producer.stdout.close()
    return_code = producer.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, ["tar", "-C", str(source), "-czf", "-", "."])


def firstFromImage(dockerfile: Path) -> str | None:
    """Return the first Dockerfile FROM image, handling optional flags.

    Args:
        dockerfile: Dockerfile to inspect.
    """
    for raw_line in dockerfile.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if not parts or parts[0].upper() != "FROM":
            continue
        index = 1
        while index < len(parts) and parts[index].startswith("--"):
            index += 1
        if index < len(parts):
            return parts[index]
    return None


def isCompilerHashBaseTag(image: str) -> bool:
    """Return true for generated compiler hash base tags.

    Args:
        image: Docker image reference from a FROM line.
    """
    tag = image.removesuffix(":latest")
    return len(tag) == 32 and all(char in "0123456789abcdef" for char in tag)


def externalBuildBaseImages(output_dir: Path) -> list[str]:
    """Collect non-generated Docker FROM images needed by remote buildx.

    Args:
        output_dir: Compiler output directory containing Docker build contexts.
    """
    images: list[str] = []
    seen: set[str] = set()
    for dockerfile in sorted(output_dir.rglob("Dockerfile")):
        image = firstFromImage(dockerfile)
        if not image:
            continue
        if image == "scratch" or image.startswith("$") or "${" in image:
            continue
        if isCompilerHashBaseTag(image):
            continue
        if image not in seen:
            seen.add(image)
            images.append(image)
    return images


def dockerImageExists(image: str) -> bool:
    """Return true when the local Docker daemon has one image reference.

    Args:
        image: Docker image reference.
    """
    return subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def dockerIoMirrorRef(image: str) -> str | None:
    """Return a Docker Hub mirror reference for unqualified Docker Hub images.

    Args:
        image: Docker image reference.
    """
    if "/" in image:
        first = image.split("/", 1)[0]
        if "." in first or ":" in first or first == "localhost":
            return None
        return f"docker.m.daocloud.io/{image}"
    return f"docker.m.daocloud.io/library/{image}"


def ensureLocalDockerImage(image: str) -> None:
    """Ensure the local Docker daemon has one image, pulling if required.

    Args:
        image: Docker image reference.
    """
    if dockerImageExists(image):
        print(f"[k8s_build] local Docker already has {image}")
        return

    print(f"[k8s_build] pulling build base image on local host: {image}")
    result = subprocess.run(["docker", "pull", image], check=False)
    if result.returncode == 0:
        return

    mirror_image = dockerIoMirrorRef(image)
    if mirror_image is None:
        raise subprocess.CalledProcessError(result.returncode, ["docker", "pull", image])

    print(f"[k8s_build] pulling build base image from mirror: {mirror_image}")
    runCommand(["docker", "pull", mirror_image])
    runCommand(["docker", "tag", mirror_image, image])


def remoteDockerImageExists(image: str, ssh_command: list[str]) -> bool:
    """Return true when the remote Docker daemon has one image reference.

    Args:
        image: Docker image reference.
        ssh_command: Base SSH argv including target host.
    """
    return subprocess.run(
        [*ssh_command, f"sudo -n docker image inspect {shlex.quote(image)} >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def streamDockerImageToRemote(image: str, ssh_command: list[str]) -> None:
    """Load one local Docker image into the remote Docker daemon over SSH.

    Args:
        image: Docker image reference.
        ssh_command: Base SSH argv including target host.
    """
    if remoteDockerImageExists(image, ssh_command):
        print(f"[k8s_build] registry host Docker already has {image}")
        return

    ensureLocalDockerImage(image)
    print("+ " + " ".join(["docker", "save", image]) + " | " + " ".join(ssh_command + ["sudo -n docker load"]))
    producer = subprocess.Popen(["docker", "save", image], stdout=subprocess.PIPE)
    try:
        assert producer.stdout is not None
        subprocess.run([*ssh_command, "sudo -n docker load"], stdin=producer.stdout, check=True)
    finally:
        if producer.stdout is not None:
            producer.stdout.close()
    return_code = producer.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, ["docker", "save", image])


def ensureBuildBaseImages(output_dir: Path, ssh_command: list[str] | None) -> None:
    """Ensure Dockerfile FROM images are available where buildx will run.

    Args:
        output_dir: Compiler output directory containing Docker build contexts.
        ssh_command: Base SSH argv for a remote registry host, or None when the
            registry/build host is local.
    """
    images = externalBuildBaseImages(output_dir)
    if not images:
        return
    print("[k8s_build] ensuring Docker build base images: " + ", ".join(images))
    if ssh_command is None:
        for image in images:
            ensureLocalDockerImage(image)
        return
    for image in images:
        streamDockerImageToRemote(image, ssh_command)


def buildImages(config: Path) -> None:
    """Stage compiler output on the registry node and build/push images.

    Args:
        config: Path to configRunning.yaml.
    """
    values = checkOutput(config)
    output_dir = Path(values["outputDir"])
    registry_prefix = values["registryPrefix"].rstrip("/")
    registry_host = registry_prefix.split("/", 1)[0].split(":", 1)[0]
    remote_dir = f"/tmp/seedemu-native-build-{time.strftime('%Y%m%d_%H%M%S')}-{os.getpid()}"
    build_command = [
        "python3",
        "./buildRegistryImages.py",
        "--output-dir",
        f"{remote_dir}/output",
        "--registry-prefix",
        registry_prefix,
        "--image-registry-prefix",
        values["imageRegistryPrefix"],
    ]

    if values["masterConnection"] == "local":
        print(f"[k8s_build] master is local; staging compile output in {remote_dir}/output")
        remote_root = Path(remote_dir)
        if remote_root.exists():
            shutil.rmtree(remote_root)
        (remote_root / "output").mkdir(parents=True)
        (remote_root / "running").mkdir(parents=True)
        copyTreeContents(output_dir, remote_root / "output")
        copyTreeContents(SCRIPT_DIR, remote_root / "running")
        ensureBuildBaseImages(output_dir, None)
        print("[k8s_build] running local build")
        runCommand(["sudo", "-n", *build_command], cwd=remote_root / "running")
        return

    ssh_target = f"{values['sshUser']}@{registry_host}"
    ssh_command = [
        "ssh",
        "-i",
        values["sshKey"],
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        "-o",
        "LogLevel=ERROR",
        "-o",
        "BatchMode=yes",
        ssh_target,
    ]
    print(f"[k8s_build] uploading compile output to {ssh_target}:{remote_dir}/output")
    ensureBuildBaseImages(output_dir, ssh_command)
    runCommand(
        [
            *ssh_command,
            f"rm -rf {shlex.quote(remote_dir)} && mkdir -p {shlex.quote(remote_dir + '/output')} {shlex.quote(remote_dir + '/running')}",
        ]
    )
    streamTarToRemote(output_dir, ssh_command, f"tar -C {shlex.quote(remote_dir + '/output')} -xzf -")
    streamTarToRemote(SCRIPT_DIR, ssh_command, f"tar -C {shlex.quote(remote_dir + '/running')} -xzf -")
    remote_build = " ".join(shlex.quote(part) for part in build_command)
    print(f"[k8s_build] running build on {ssh_target}")
    runCommand([*ssh_command, f"cd {shlex.quote(remote_dir + '/running')} && sudo -n {remote_build}"])


def renderKustomization(config: Path) -> dict[str, str]:
    """Render kustomization.yaml and return the resolved running context.

    Args:
        config: Path to configRunning.yaml.
    """
    values = checkOutput(config)
    runCommand(
        [
            "python3",
            str(HELPER),
            "kustomization",
            "--images-yaml",
            values["imagesYaml"],
            "--manifest",
            values["manifest"],
            "--image-registry-prefix",
            values["imageRegistryPrefix"],
            "--registry-prefix",
            values["registryPrefix"],
            "--network-backend",
            values["networkBackend"],
            "--cni-master-interface",
            values["cniMasterInterface"],
            "--attached-cni-type",
            values["attachedCniType"],
            "--output",
            values["kustomization"],
        ]
    )
    print(f"[k8s_up] wrote {values['kustomization']}")
    return values


def namespaceForManifest(manifest: str) -> str:
    """Return namespace from one Kubernetes manifest path."""
    return helperOutput(["namespace", "--manifest", manifest])


def deploy(config: Path) -> None:
    """Apply workload resources and wait for all SeedEMU pods to become ready.

    Args:
        config: Path to configRunning.yaml.
    """
    values = renderKustomization(config)
    namespace = namespaceForManifest(values["manifest"])
    print("=== native-k8s deploy ===")
    print(f"output_dir={values['outputDir']}")
    print(f"manifest={values['manifest']}")
    print(f"kustomization={values['kustomization']}")
    print(f"network_backend={values['networkBackend']}")
    print(f"kubeconfig={values['kubeconfig']}")
    print(f"namespace={namespace}")
    runCommand(["kubectl", "--kubeconfig", values["kubeconfig"], "apply", "-k", values["outputDir"]])
    waitReady(config)


def waitReady(config: Path) -> None:
    """Wait for deployment rollouts and SeedEMU pods.

    Args:
        config: Path to configRunning.yaml.
    """
    values = checkOutput(config)
    namespace = namespaceForManifest(values["manifest"])
    names = helperOutput(["deployment-names", "--manifest", values["manifest"]]).splitlines()
    for name in names:
        if not name:
            continue
        print(f"[rollout] deployment/{name}")
        runCommand(
            [
                "kubectl",
                "--kubeconfig",
                values["kubeconfig"],
                "-n",
                namespace,
                "rollout",
                "status",
                f"deployment/{name}",
                f"--timeout={values['rolloutTimeoutSeconds']}s",
            ]
        )
    runCommand(
        [
            "kubectl",
            "--kubeconfig",
            values["kubeconfig"],
            "-n",
            namespace,
            "wait",
            "--for=condition=Ready",
            "pod",
            "-l",
            "seedemu.io/workload=seedemu",
            f"--timeout={values['rolloutTimeoutSeconds']}s",
        ]
    )
    print("Deploy completed successfully.")


def clean(config: Path) -> None:
    """Delete workload resources and namespace.

    Args:
        config: Path to configRunning.yaml.
    """
    values = checkOutput(config)
    namespace = namespaceForManifest(values["manifest"])
    if Path(values["kustomization"]).is_file():
        print(f"[clean] deleting resources from {values['kustomization']}")
        subprocess.run(
            [
                "kubectl",
                "--kubeconfig",
                values["kubeconfig"],
                "delete",
                "-k",
                values["outputDir"],
                "--ignore-not-found=true",
                "--wait=false",
            ],
            check=False,
        )
    else:
        print("[clean] kustomization not found; deleting namespace only")
    exists = subprocess.run(
        ["kubectl", "--kubeconfig", values["kubeconfig"], "get", "namespace", namespace],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0
    if exists:
        print(f"[clean] deleting namespace {namespace}")
        runCommand(["kubectl", "--kubeconfig", values["kubeconfig"], "delete", "namespace", namespace, "--wait=false"])
    else:
        print(f"[clean] namespace {namespace} does not exist")


def parseArgs(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for the running-stage replacement.

    Args:
        argv: Optional argv override for tests.
    """
    parser = argparse.ArgumentParser(prog="manageRunningStage.py")
    parser.add_argument(
        "--config",
        default=str(SCRIPT_DIR / "configRunning.yaml"),
        help="Path to configRunning.yaml.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ["check-output", "preflight", "build", "render-kustomization", "up", "wait", "clean"]:
        sub.add_parser(name)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run one running-stage command."""
    args = parseArgs(argv)
    config = Path(args.config).expanduser().resolve()
    if args.command == "check-output":
        checkOutput(config)
    elif args.command == "preflight":
        preflight(config)
    elif args.command == "build":
        buildImages(config)
    elif args.command == "render-kustomization":
        renderKustomization(config)
    elif args.command == "up":
        deploy(config)
    elif args.command == "wait":
        waitReady(config)
    elif args.command == "clean":
        clean(config)
    else:
        raise SystemExit(f"unsupported command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Build per-node Docker archives for compiled SeedEMU K8s images.

Compiler workloads share a few software base images and differ mainly
by small runtime configuration files. Each distinct FROM is preserved. Building and pushing thousands of nearly
identical Dockerfiles is slow, so this tool creates Docker-compatible archives
directly: each archive contains the shared base layers once and one small layer
per target image. K3s/containerd can import these archives with
`k3s ctr images import`.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import io
import json
import os
import posixpath
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile
import time
from typing import Dict, Iterable, List, Tuple


BUILD_RE = re.compile(r"^seedemu_build_and_push\s+(\S+)\s+(\S+)\s*$")
COMPILER_HASH_RE = re.compile(r"^[0-9a-f]{32}(:latest)?$")

EXECUTABLE_DEST_MODES = {
    "start.sh": 0o755,
    "seedemu_sniffer": 0o755,
    "seedemu_worker": 0o755,
}

EMULATED_RUN_COMMANDS = {
    "mkdir -p /usr/share/doc/bird2/examples/",
    "touch /usr/share/doc/bird2/examples/bird.conf",
    "chmod +x /start.sh",
    "chmod +x /seedemu_sniffer",
    "chmod +x /seedemu_worker",
}


@dataclass
class BaseVariant:
    """One shared base image/archive for a Dockerfile build-instruction set."""

    image: str
    instructions: Tuple[str, ...]
    archive_dir: Path
    config: dict
    layers: List[str]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_build_images(path: Path) -> Dict[str, Path]:
    mapping: Dict[str, Path] = {}
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            match = BUILD_RE.match(line.strip())
            if not match:
                continue
            image, context = match.groups()
            mapping[image] = Path(context)
    if not mapping:
        raise RuntimeError(f"no seedemu_build_and_push entries found in {path}")
    return mapping


def run(cmd: List[str], *, stdout=None) -> None:
    subprocess.run(cmd, check=True, stdout=stdout)


def docker_image_exists(image: str) -> bool:
    return subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0


def mirror_image_name(image: str) -> str:
    mirror = os.environ.get("SEED_DOCKER_IO_MIRROR_ENDPOINT", "https://docker.m.daocloud.io")
    if not mirror:
        return image
    mirror_host = mirror.removeprefix("https://").removeprefix("http://").rstrip("/")
    if "/" in image:
        return f"{mirror_host}/{image}"
    return f"{mirror_host}/library/{image}"


def compiler_base_context(work_dir: Path, image: str) -> Path:
    """Return the compiler-staged base-image context for one source image."""
    tag = hashlib.md5(image.encode("utf-8")).hexdigest()
    return work_dir / "base_images" / tag


def ensure_source_image(image: str, work_dir: Path | None = None) -> None:
    """Ensure a Docker image exists, preferring compiler-staged local contexts."""
    if docker_image_exists(image):
        return
    if work_dir is not None:
        context_dir = compiler_base_context(work_dir, image)
        dockerfile = context_dir / "Dockerfile"
        if dockerfile.exists():
            for source in dockerfile_from_images(dockerfile):
                ensure_source_image(source, work_dir)
            print(f"[fast-archive] building source image {image} from {context_dir}", flush=True)
            run(["docker", "build", "-t", image, str(context_dir)])
            return
    mirror = mirror_image_name(image)
    if mirror != image:
        if subprocess.run(["docker", "pull", mirror], check=False).returncode == 0:
            run(["docker", "tag", mirror, image])
            return
    run(["docker", "pull", image])


def dockerfile_from_images(path: Path) -> Iterable[str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0].upper() == "FROM":
            yield fields[1]


def dockerfile_logical_lines(path: Path) -> Iterable[str]:
    """Yield normalized Dockerfile instructions, joining backslash lines."""
    pending = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or (line.startswith("#") and not pending):
            continue
        pending = f"{pending} {line}".strip() if pending else line
        if pending.endswith("\\"):
            pending = pending[:-1].rstrip()
            continue
        yield pending
        pending = ""
    if pending:
        raise RuntimeError(f"unterminated Dockerfile continuation in {path}")


def dockerfile_build_instructions(path: Path) -> Tuple[str, ...]:
    """Return pre-COPY instructions that require a real shared image build.

    The fast runtime layer explicitly implements SeedEMU's standard mkdir,
    touch, COPY, chmod, and CMD operations. Other RUN commands, such as
    installing iperf3, must be executed in a shared base variant. A nonstandard
    RUN after COPY may depend on per-context files and therefore cannot be
    folded into a shared base safely.
    """
    prefix: List[str] = []
    has_required_run = False
    seen_copy = False
    for line in dockerfile_logical_lines(path):
        fields = line.split(maxsplit=1)
        operation = fields[0].upper()
        argument = fields[1].strip() if len(fields) > 1 else ""
        if operation not in {"FROM", "ARG", "ENV", "SHELL", "USER", "WORKDIR", "COPY", "RUN", "CMD"}:
            raise RuntimeError(f"unsupported {operation} in {path}; use imageBuildMode: registry")
        if operation == "CMD" and json.loads(argument) != ["/start.sh"]:
            raise RuntimeError(f"unsupported CMD in {path}; use imageBuildMode: registry")
        if seen_copy and operation in {"ENV", "SHELL", "USER", "WORKDIR"}:
            raise RuntimeError(f"unsupported {operation} after COPY in {path}; use imageBuildMode: registry")
        if operation in {"COPY", "ADD"}:
            seen_copy = True
            continue
        if operation == "RUN":
            if argument in EMULATED_RUN_COMMANDS:
                continue
            if seen_copy:
                raise RuntimeError(
                    f"unsupported RUN after COPY in {path}: {line}; "
                    "disable fast archive mode or move the software install before COPY"
                )
            prefix.append(line)
            has_required_run = True
            continue
        if not seen_copy and operation in {"ARG", "ENV", "SHELL", "USER", "WORKDIR"}:
            prefix.append(line)
    return tuple(prefix) if has_required_run or any(not line.startswith("ARG ") for line in prefix) else ()


def dockerfile_copy_entries(path: Path) -> Iterable[Tuple[str, str, int | None]]:
    """Yield Dockerfile COPY source/destination pairs used by SeedEMU contexts."""
    for line in dockerfile_logical_lines(path):
        try:
            fields = shlex.split(line)
        except ValueError as exc:
            raise RuntimeError(f"cannot parse Dockerfile line in {path}: {line}") from exc
        if not fields or fields[0].upper() != "COPY":
            continue

        args = fields[1:]
        if args and args[0].startswith("--"):
            raise RuntimeError(f"unsupported COPY flag in {path}: {line}")
        if len(args) < 2:
            raise RuntimeError(f"unsupported COPY line in {path}: {line}")

        dest = args[-1].lstrip("/")
        sources = args[:-1]
        multiple_sources = len(sources) > 1
        for source in sources:
            if multiple_sources or dest.endswith("/"):
                target = posixpath.join(dest.rstrip("/"), posixpath.basename(source))
            else:
                target = dest
            target = target.lstrip("/")
            mode = EXECUTABLE_DEST_MODES.get(target)
            yield source, target, mode


def ensure_base_image(base_image: str, work_dir: Path) -> None:
    if docker_image_exists(base_image):
        return
    context_dir = work_dir / "base_images" / base_image
    dockerfile = context_dir / "Dockerfile"
    if not dockerfile.exists():
        if COMPILER_HASH_RE.match(base_image):
            raise RuntimeError(f"missing compiler base image context: {dockerfile}")
        ensure_source_image(base_image, work_dir)
        return
    for source in dockerfile_from_images(dockerfile):
        ensure_source_image(source, work_dir)
    print(f"[fast-archive] building base image {base_image} from {context_dir}", flush=True)
    run(["docker", "build", "-t", base_image, str(context_dir)])


def docker_image_id(image: str) -> str:
    """Return the immutable local Docker image ID for cache keys."""
    response = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True,
        capture_output=True,
        check=True,
    )
    image_id = response.stdout.strip()
    if not image_id:
        raise RuntimeError(f"docker returned an empty image ID for {image}")
    return image_id


def ensure_base_variant(
    base_image: str,
    instructions: Tuple[str, ...],
    work_dir: Path,
) -> str:
    """Build and return one deterministic shared software-base image."""
    if not instructions:
        return base_image
    payload = "\n".join((docker_image_id(base_image), *instructions)).encode("utf-8")
    digest = sha256_bytes(payload)
    image = f"seedemu-fast-base:{digest[:24]}"
    if docker_image_exists(image):
        return image

    context_dir = work_dir / ".fast_base_variant_build" / digest
    context_dir.mkdir(parents=True, exist_ok=True)
    dockerfile = context_dir / "Dockerfile"
    dockerfile.write_text(
        "\n".join((f"FROM {base_image}", *instructions, "")),
        encoding="utf-8",
    )
    print(
        f"[fast-archive] building software base {image} "
        f"with {len(instructions)} instruction(s)",
        flush=True,
    )
    run(["docker", "build", "-t", image, str(context_dir)])
    return image


def extract_base_archive(base_image: str, base_dir: Path) -> None:
    marker = base_dir / ".ready"
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == base_image:
        return
    if base_dir.exists():
        shutil.rmtree(base_dir)
    base_dir.mkdir(parents=True)
    proc = subprocess.Popen(["docker", "save", base_image], stdout=subprocess.PIPE)
    assert proc.stdout is not None
    try:
        with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
            archive.extractall(base_dir)
    finally:
        rc = proc.wait()
    if rc != 0:
        raise RuntimeError(f"docker save failed for {base_image} with exit code {rc}")
    marker.write_text(f"{base_image}\n", encoding="utf-8")


def load_base(base_dir: Path) -> Tuple[dict, List[str]]:
    manifest_path = base_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest:
        raise RuntimeError(f"empty base manifest: {manifest_path}")
    entry = manifest[0]
    config_path = base_dir / entry["Config"]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    layers = list(entry["Layers"])
    for layer in layers:
        if not (base_dir / layer).exists():
            raise RuntimeError(f"base layer listed in manifest is missing: {layer}")
    return config, layers


def add_dir(archive: tarfile.TarFile, name: str, mode: int = 0o755) -> None:
    info = tarfile.TarInfo(name.rstrip("/") + "/")
    info.type = tarfile.DIRTYPE
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    archive.addfile(info)


def add_bytes(
    archive: tarfile.TarFile,
    name: str,
    data: bytes,
    mode: int,
) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = mode
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mtime = 0
    archive.addfile(info, io.BytesIO(data))


def add_context_file(
    archive: tarfile.TarFile,
    src: Path,
    dest: str,
    mode_override: int | None,
) -> None:
    mode = mode_override
    if mode is None:
        mode = src.stat().st_mode & 0o777
        if mode == 0:
            mode = 0o644
    add_bytes(archive, dest, src.read_bytes(), mode)


def make_layer(context_dir: Path) -> Tuple[str, bytes]:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        added_dirs = set()
        def add_dir_once(dirname: str) -> None:
            dirname = dirname.strip("/")
            if not dirname or dirname in added_dirs:
                return
            add_dir(archive, dirname)
            added_dirs.add(dirname)

        for dirname in (
            "usr",
            "usr/share",
            "usr/share/doc",
            "usr/share/doc/bird2",
            "usr/share/doc/bird2/examples",
            "etc",
            "etc/bird",
            "etc/bird/conf",
            "root",
        ):
            add_dir_once(dirname)
        add_bytes(archive, "usr/share/doc/bird2/examples/bird.conf", b"", 0o644)
        dockerfile = context_dir / "Dockerfile"
        if not dockerfile.exists():
            raise RuntimeError(f"missing Dockerfile in context {context_dir}")
        for src_name, dest, mode in dockerfile_copy_entries(dockerfile):
            dirname = posixpath.dirname(dest)
            while dirname and dirname != ".":
                add_dir_once(dirname)
                dirname = posixpath.dirname(dirname)
            src = context_dir / src_name
            if not src.exists():
                raise RuntimeError(f"missing context file {src}")
            add_context_file(archive, src, dest, mode)
    data = buffer.getvalue()
    return sha256_bytes(data), data


def make_config(base_config: dict, layer_diff_id: str) -> Tuple[str, bytes]:
    config = copy.deepcopy(base_config)
    config.setdefault("config", {})
    config["config"]["Cmd"] = ["/start.sh"]
    config.setdefault("rootfs", {}).setdefault("diff_ids", [])
    config["rootfs"]["diff_ids"] = list(config["rootfs"]["diff_ids"]) + [
        f"sha256:{layer_diff_id}"
    ]
    history = list(config.get("history", []))
    history.append(
        {
            "created_by": "seedemu buildImageArchives.py",
            "comment": "SeedEMU runtime configuration layer",
        }
    )
    config["history"] = history
    data = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_bytes(data), data


def image_context(work_dir: Path, context_ref: Path) -> Path:
    if context_ref.is_absolute():
        return context_ref
    return (work_dir / context_ref).resolve()


def prepare_base_variants(
    *,
    base_image: str,
    work_dir: Path,
    image_to_context: Dict[str, Path],
    cache_root: Path,
) -> Tuple[Dict[Tuple[str, ...], BaseVariant], Dict[str, Tuple[str, ...]], Dict[Tuple[str, ...], int]]:
    """Build/extract all software-base variants used by workload contexts."""
    context_instructions: Dict[str, Tuple[str, ...]] = {}
    variant_counts: Dict[Tuple[str, ...], int] = {}
    for context_ref in image_to_context.values():
        context_dir = image_context(work_dir, context_ref)
        key = str(context_dir)
        instructions = context_instructions.get(key)
        if instructions is None:
            dockerfile = context_dir / "Dockerfile"
            sources = list(dockerfile_from_images(dockerfile))
            if len(sources) != 1:
                raise ValueError(f"fast archive requires a single FROM: {dockerfile}")
            instructions = (f"FROM {base_image or sources[0]}", *dockerfile_build_instructions(dockerfile))
            context_instructions[key] = instructions
        variant_counts[instructions] = variant_counts.get(instructions, 0) + 1

    variants: Dict[Tuple[str, ...], BaseVariant] = {}
    for instructions in sorted(variant_counts, key=lambda item: (len(item), item)):
        source = instructions[0].split(maxsplit=1)[1]
        ensure_base_image(source, work_dir)
        image = ensure_base_variant(source, instructions[1:], work_dir)
        cache_key = sha256_bytes(
            "\n".join((docker_image_id(image), *instructions)).encode("utf-8")
        )
        archive_dir = cache_root / cache_key
        extract_base_archive(image, archive_dir)
        config, layers = load_base(archive_dir)
        variants[instructions] = BaseVariant(
            image=image,
            instructions=instructions,
            archive_dir=archive_dir,
            config=config,
            layers=layers,
        )
    return variants, context_instructions, variant_counts


def infer_base_image(work_dir: Path, image_to_context: Dict[str, Path]) -> str:
    for context_ref in image_to_context.values():
        dockerfile = image_context(work_dir, context_ref) / "Dockerfile"
        if not dockerfile.exists():
            continue
        for source in dockerfile_from_images(dockerfile):
            return source
    raise RuntimeError("cannot infer base image from workload Dockerfiles")


def read_images(path: Path) -> List[str]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_file_to_archive(archive: tarfile.TarFile, src: Path, arcname: str) -> None:
    archive.add(src, arcname=arcname, recursive=False)


def write_node_archive(
    *,
    node_name: str,
    images: List[str],
    work_dir: Path,
    base_variants: Dict[Tuple[str, ...], BaseVariant],
    context_instructions: Dict[str, Tuple[str, ...]],
    image_to_context: Dict[str, Path],
    archive_dir: Path,
) -> dict:
    start = time.monotonic()
    archive_path = archive_dir / f"images_{node_name}.tar"
    manifest_entries = []
    layer_cache: Dict[str, Tuple[str, bytes]] = {}
    config_blobs: Dict[str, bytes] = {}
    archived_paths = set()

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="w") as output:
        for image in images:
            context_ref = image_to_context.get(image)
            if context_ref is None:
                raise RuntimeError(f"image {image} is missing from build_images.sh")
            context_dir = image_context(work_dir, context_ref)
            instructions = context_instructions[str(context_dir)]
            base_variant = base_variants[instructions]
            for layer in base_variant.layers:
                if layer in archived_paths:
                    continue
                add_file_to_archive(output, base_variant.archive_dir / layer, layer)
                archived_paths.add(layer)
            layer_diff_id, layer_data = layer_cache.get(str(context_dir), (None, None))  # type: ignore[arg-type]
            if layer_diff_id is None or layer_data is None:
                layer_diff_id, layer_data = make_layer(context_dir)
                layer_cache[str(context_dir)] = (layer_diff_id, layer_data)
            layer_path = f"blobs/sha256/{layer_diff_id}"
            if layer_path not in archived_paths:
                add_bytes(output, layer_path, layer_data, 0o444)
                archived_paths.add(layer_path)

            config_digest, config_data = make_config(base_variant.config, layer_diff_id)
            config_path = f"blobs/sha256/{config_digest}"
            if config_digest not in config_blobs:
                config_blobs[config_digest] = config_data
                add_bytes(output, config_path, config_data, 0o444)
                archived_paths.add(config_path)
            manifest_entries.append(
                {
                    "Config": config_path,
                    "RepoTags": [image],
                    "Layers": base_variant.layers + [layer_path],
                }
            )
        add_bytes(
            output,
            "manifest.json",
            json.dumps(manifest_entries, indent=2).encode("utf-8"),
            0o644,
        )
    duration = time.monotonic() - start
    return {
        "node": node_name,
        "imageCount": len(images),
        "archive": str(archive_path),
        "archiveBytes": archive_path.stat().st_size,
        "durationSeconds": round(duration, 2),
    }


def iter_node_lists(node_image_dir: Path) -> Iterable[Tuple[str, Path]]:
    for path in sorted(node_image_dir.glob("images_*.txt")):
        node = path.name[len("images_") : -len(".txt")]
        yield node, path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--node-image-dir", required=True, type=Path)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--base-image", default="")
    parser.add_argument("--image-plan", type=Path, help="JSON image-to-context mapping from compiler metadata")
    parser.add_argument("--base-cache-dir", type=Path)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()

    work_dir = args.work_dir.resolve()
    node_image_dir = args.node_image_dir.resolve()
    archive_dir = args.archive_dir.resolve()
    base_cache_root = (args.base_cache_dir or (work_dir / ".fast_base_archives")).resolve()

    build_images = work_dir / "build_images.sh"
    if not args.image_plan and not build_images.exists():
        raise RuntimeError(f"missing build_images.sh: {build_images}")
    if not node_image_dir.exists():
        raise RuntimeError(f"missing node image directory: {node_image_dir}")

    started = time.monotonic()
    image_to_context = ({item["name"]: Path(item["context"]) for item in json.loads(args.image_plan.read_text())}
                        if args.image_plan else parse_build_images(build_images))
    base_image = args.base_image
    base_variants, context_instructions, variant_counts = prepare_base_variants(
        base_image=base_image,
        work_dir=work_dir,
        image_to_context=image_to_context,
        cache_root=base_cache_root,
    )

    results = []
    total_images = 0
    for node_name, list_path in iter_node_lists(node_image_dir):
        images = read_images(list_path)
        if not images:
            results.append(
                {
                    "node": node_name,
                    "imageCount": 0,
                    "archive": "",
                    "archiveBytes": 0,
                    "durationSeconds": 0,
                }
            )
            continue
        result = write_node_archive(
            node_name=node_name,
            images=images,
            work_dir=work_dir,
            base_variants=base_variants,
            context_instructions=context_instructions,
            image_to_context=image_to_context,
            archive_dir=archive_dir,
        )
        total_images += len(images)
        results.append(result)
        print(
            f"[fast-archive] {node_name}: {len(images)} images, "
            f"{result['archiveBytes']} bytes, {result['durationSeconds']}s",
            flush=True,
        )

    summary = {
        "status": "PASS",
        "workDir": str(work_dir),
        "nodeImageDir": str(node_image_dir),
        "archiveDir": str(archive_dir),
        "baseImage": base_image,
        "baseVariants": [
            {
                "image": base_variants[instructions].image,
                "imageCount": variant_counts[instructions],
                "instructions": list(instructions),
            }
            for instructions in sorted(variant_counts, key=lambda item: (len(item), item))
        ],
        "nodeCount": len(results),
        "imageCount": total_images,
        "durationSeconds": round(time.monotonic() - started, 2),
        "nodes": results,
    }
    if args.summary:
        args.summary.parent.mkdir(parents=True, exist_ok=True)
        args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

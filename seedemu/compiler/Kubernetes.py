from __future__ import annotations
from seedemu.core.Emulator import Emulator
from seedemu.core import Node, Network, Compiler, Scope, OptionHandling, BaseVolume
from seedemu.core.enums import NodeRole, NetworkType
from .Docker import Docker, DockerCompilerFileTemplates
from .DockerImage import DockerImage
from typing import Dict, Generator, List, Set, Tuple, Optional, Any
from hashlib import md5
from os import mkdir, chdir
import json
import os
import shutil
import shlex
import yaml


class SchedulingStrategy:
    """Scheduling strategy constants for Kubernetes node placement."""
    NONE = "none"           # No scheduling constraints
    AUTO = "auto"           # Automatic soft grouping + soft spreading
    BY_AS = "by_as"         # Schedule pods by AS number (soft affinity)
    BY_AS_HARD = "by_as_hard"  # Same ASN must land on one explicit Kubernetes node
    BY_ROLE = "by_role"     # Schedule pods by node role (router, host, etc.)
    CUSTOM = "custom"       # Use custom labels provided by user


class KubernetesCompiler(Docker):
    """!
    @brief The Kubernetes compiler class.

    Compiles the emulation to Kubernetes manifests with support for:
    - Multi-node scheduling (nodeSelector, nodeAffinity)
    - Resource management (requests/limits)
    - Service generation (ClusterIP, NodePort)
    - Configurable CNI types for cross-node networking
    """

    __registry_prefix: str
    __namespace: str
    __use_multus: bool
    __manifests: List[str]
    __build_commands: List[str]
    _current_node: Node
    
    # New fields for multi-node support
    __scheduling_strategy: str
    __node_labels: Dict[str, Dict[str, str]]
    __default_resources: Dict[str, Dict[str, str]]
    __cni_type: str
    __local_link_cni_type: Optional[str]
    __cni_master_interface: str
    __generate_services: bool
    __service_type: str
    __image_pull_policy: str

    def __init__(
        self,
        registry_prefix: str = "localhost:5000",
        namespace: str = "seedemu",
        use_multus: bool = True,
        internetMapEnabled: bool = True,
        # New parameters for multi-node deployment
        scheduling_strategy: str = SchedulingStrategy.NONE,
        node_labels: Dict[str, Dict[str, str]] = None,
        default_resources: Dict[str, Dict[str, str]] = None,
        cni_type: str = "bridge",
        local_link_cni_type: Optional[str] = None,
        cni_master_interface: str = "eth0",
        generate_services: bool = False,
        service_type: str = "ClusterIP",
        image_pull_policy: str = "Always",
        **kwargs
    ):
        """!
        @brief Kubernetes compiler constructor.

        @param registry_prefix (optional) Registry prefix for docker images. Default "localhost:5000".
        @param namespace (optional) Kubernetes namespace. Default "seedemu".
        @param use_multus (optional) Use Multus CNI for multiple interfaces. Default True.
        @param internetMapEnabled (optional) Enable Internet Map visualization service. Default True.
        @param scheduling_strategy (optional) How to schedule pods across nodes. Options:
            - "none": No scheduling constraints (default)
            - "auto": Let scheduler auto-balance with soft AS/role affinity
            - "by_as": Prefer pods with same AS on same node (no node pre-labeling needed)
            - "by_role": Prefer same role on same node (no node pre-labeling needed)
            - "custom": Use custom node_labels mapping
        @param node_labels (optional) Custom node labels for scheduling. Dict mapping AS numbers or
            node names to label dicts. Example: {"150": {"kubernetes.io/hostname": "node1"}}
        @param default_resources (optional) Default resource requests/limits for all pods.
            Example: {"requests": {"cpu": "100m", "memory": "128Mi"}, 
                      "limits": {"cpu": "500m", "memory": "512Mi"}}
        @param cni_type (optional) CNI plugin type for NetworkAttachmentDefinition. Options:
            - "bridge": Local bridge (default, single-node only)
            - "macvlan": macvlan for cross-node with L2 access
            - "ipvlan": ipvlan for cross-node networking
            - "host-local": Use host-local IPAM
        @param local_link_cni_type (optional) Override CNI type for node-local internal links.
            When left unset, `by_as_hard` + `macvlan/ipvlan` automatically falls back to
            `bridge` for `Local` / `CrossConnect` networks so same-AS internal links stay
            isolated on the selected Kubernetes node.
        @param cni_master_interface (optional) Master interface for macvlan/ipvlan. Default "eth0".
        @param generate_services (optional) Generate K8s Service resources for nodes. Default False.
        @param service_type (optional) Service type when generate_services is True. 
            Options: "ClusterIP", "NodePort". Default "ClusterIP".
        @param image_pull_policy (optional) K8s ImagePullPolicy. Default "Always".
        """
        # Force selfManagedNetwork=True so that parent logic generates /replace_address.sh call in start.sh
        kwargs['selfManagedNetwork'] = True
        super().__init__(**kwargs)
        self.__registry_prefix = registry_prefix
        self.__namespace = namespace
        self.__use_multus = use_multus
        self.__internet_map_enabled = internetMapEnabled
        self.__manifests = []
        self.__build_commands = []
        self._current_node = None
        
        # Multi-node deployment settings
        strategy = (scheduling_strategy or SchedulingStrategy.NONE).strip().lower()
        valid = {
            SchedulingStrategy.NONE,
            SchedulingStrategy.AUTO,
            SchedulingStrategy.BY_AS,
            SchedulingStrategy.BY_AS_HARD,
            SchedulingStrategy.BY_ROLE,
            SchedulingStrategy.CUSTOM,
        }
        self.__scheduling_strategy = strategy if strategy in valid else SchedulingStrategy.NONE
        self.__node_labels = node_labels or {}
        self.__default_resources = default_resources or {}
        self.__cni_type = cni_type
        self.__local_link_cni_type = local_link_cni_type.strip().lower() if isinstance(local_link_cni_type, str) and local_link_cni_type.strip() else None
        self.__cni_master_interface = cni_master_interface
        self.__generate_services = generate_services
        self.__service_type = service_type
        self.__image_pull_policy = image_pull_policy

    def getName(self) -> str:
        return "Kubernetes"

    def _resolveInternetMapImages(self) -> Tuple[str, str]:
        """Resolve source and deployment image refs for the optional Internet Map service."""
        source_image = os.environ.get(
            "SEED_INTERNET_MAP_SOURCE_IMAGE",
            "handsonsecurity/seedemu-multiarch-map:buildx-latest",
        ).strip() or "handsonsecurity/seedemu-multiarch-map:buildx-latest"

        default_target = source_image
        if self.__registry_prefix:
            default_target = f"{self.__registry_prefix}/seedemu-internet-map:buildx-latest"

        target_image = os.environ.get("SEED_INTERNET_MAP_IMAGE", default_target).strip() or default_target
        return source_image, target_image


    @staticmethod
    def _safeBridgeName(name: str) -> str:
        """Generate a Linux bridge name that fits the 15-char IFNAMSIZ limit.
        
        Uses 'br-' prefix (3 chars) + md5 hash truncated to 12 chars = 15 chars total.
        This ensures uniqueness while staying within the kernel limit.
        """
        h = md5(name.encode()).hexdigest()[:12]
        return f"br-{h}"

    def _doCompile(self, emulator: Emulator):
        registry = emulator.getRegistry()
        self._groupSoftware(emulator)

        # Implementation overview:
        # (1) networks -> NetworkAttachmentDefinition (Multus),
        # (2) nodes -> Deployment/VirtualMachine,
        # (3) output artifacts (k8s.yaml, build_images.sh, .env).
        # 1. Generate NetworkAttachmentDefinitions (if Multus)
        if self.__use_multus:
            for ((scope, type, name), obj) in registry.getAll().items():
                if type == 'net':
                    self.__manifests.append(self._compileNetK8s(obj))

        # 2. Compile Nodes
        for ((scope, type, name), obj) in registry.getAll().items():
            if type in ['rnode', 'csnode', 'hnode', 'rs', 'snode']:
                self.__manifests.append(self._compileNodeK8s(obj))

        # 3. Generate Output Files

        # manifests.yaml
        with open('k8s.yaml', 'w') as f:
            f.write("\n---\n".join(self.__manifests))

        # Stage local Dockerfile contexts for built-in base images (to avoid relying on Docker Hub mirrors
        # that may not whitelist custom images like handsonsecurity/*).
        used_images = sorted(getattr(self, "_used_images", set()))
        try:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            base_image_sources = {
                # These match DockerImageConstant defaults.
                "handsonsecurity/seedemu-multiarch-base:buildx-latest": os.path.join(repo_root, "docker_images", "multiarch", "seedemu-base"),
                "handsonsecurity/seedemu-multiarch-router:buildx-latest": os.path.join(repo_root, "docker_images", "multiarch", "seedemu-router"),
            }
            staged_any = False
            for image in used_images:
                src = base_image_sources.get(image)
                if not src or not os.path.isdir(src):
                    continue
                digest = md5(image.encode("utf-8")).hexdigest()
                dst_root = os.path.join("base_images", digest)
                os.makedirs(os.path.dirname(dst_root), exist_ok=True)
                if os.path.exists(dst_root):
                    shutil.rmtree(dst_root)
                shutil.copytree(src, dst_root)
                staged_any = True
            if not staged_any and os.path.isdir("base_images"):
                shutil.rmtree("base_images")
        except Exception:
            # Best-effort only: compilation should still succeed even if we can't stage base images.
            pass

        # build_images.sh
        with open('build_images.sh', 'w') as f:
            f.write("#!/usr/bin/env bash\n")
            f.write("set -euo pipefail\n")
            # Allow callers to override BuildKit/parallelism without editing generated artifacts.
            f.write('export DOCKER_BUILDKIT="${SEED_DOCKER_BUILDKIT:-0}"\n')
            f.write('PARALLELISM="${SEED_BUILD_PARALLELISM:-1}"\n')
            f.write('if ! [[ "${PARALLELISM}" =~ ^[0-9]+$ ]]; then PARALLELISM=1; fi\n')
            f.write('export REGISTRY_PUSH_RETRIES="${SEED_REGISTRY_PUSH_RETRIES:-5}"\n')
            f.write('if ! [[ "${REGISTRY_PUSH_RETRIES}" =~ ^[0-9]+$ ]]; then REGISTRY_PUSH_RETRIES=5; fi\n')
            f.write('export REGISTRY_PUSH_BACKOFF_SECONDS="${SEED_REGISTRY_PUSH_BACKOFF_SECONDS:-5}"\n')
            f.write('if ! [[ "${REGISTRY_PUSH_BACKOFF_SECONDS}" =~ ^[0-9]+$ ]]; then REGISTRY_PUSH_BACKOFF_SECONDS=5; fi\n')
            f.write('export REGISTRY_PUSH_TIMEOUT_SECONDS="${SEED_REGISTRY_PUSH_TIMEOUT_SECONDS:-180}"\n')
            f.write('if ! [[ "${REGISTRY_PUSH_TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]]; then REGISTRY_PUSH_TIMEOUT_SECONDS=180; fi\n')
            f.write('export SEED_IMAGE_DISTRIBUTION_MODE="${SEED_IMAGE_DISTRIBUTION_MODE:-registry}"\n')
            f.write('if [[ "${SEED_IMAGE_DISTRIBUTION_MODE}" != "registry" && "${SEED_IMAGE_DISTRIBUTION_MODE}" != "preload" ]]; then export SEED_IMAGE_DISTRIBUTION_MODE="registry"; fi\n')
            f.write('export SEED_DOCKER_MAX_CONCURRENT_UPLOADS="${SEED_DOCKER_MAX_CONCURRENT_UPLOADS:-1}"\n')
            f.write('if ! [[ "${SEED_DOCKER_MAX_CONCURRENT_UPLOADS}" =~ ^[0-9]+$ ]]; then export SEED_DOCKER_MAX_CONCURRENT_UPLOADS=1; fi\n')
            # Export so the inline Python snippet (daemon.json edit) can see it.
            f.write('export SEED_DOCKER_IO_MIRROR_ENDPOINT="${SEED_DOCKER_IO_MIRROR_ENDPOINT:-https://docker.m.daocloud.io}"\n')
            f.write('MIRROR_HOST="${SEED_DOCKER_IO_MIRROR_ENDPOINT#http://}"\n')
            f.write('MIRROR_HOST="${MIRROR_HOST#https://}"\n')
            # Export so the inline Python snippet (daemon.json edit) can see it.
            f.write(f'export REGISTRY_PREFIX="{self.__registry_prefix}"\n')
            f.write('export REGISTRY_LOCAL_ENDPOINT="${SEED_REGISTRY_LOCAL_ENDPOINT:-}"\n')
            f.write("\n")
            f.write("docker_pull() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if command -v timeout >/dev/null 2>&1; then\n")
            f.write("    timeout 180s docker pull \"$image\"\n")
            f.write("  else\n")
            f.write("    docker pull \"$image\"\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write("mirror_image_name() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if [[ -z \"${MIRROR_HOST}\" ]]; then\n")
            f.write("    echo \"$image\"\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  if [[ \"$image\" == *\"/\"* ]]; then\n")
            f.write("    echo \"${MIRROR_HOST}/${image}\"\n")
            f.write("  else\n")
            f.write("    echo \"${MIRROR_HOST}/library/${image}\"\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write("ensure_image_present() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if docker image inspect \"$image\" >/dev/null 2>&1; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  local mirror\n")
            f.write("  mirror=\"$(mirror_image_name \"$image\")\"\n")
            # In environments where Docker Hub is blocked, try the mirror first.
            f.write("  if [[ \"$mirror\" != \"$image\" ]]; then\n")
            f.write("    if docker_pull \"$mirror\" >/dev/null 2>&1; then\n")
            f.write("      docker tag \"$mirror\" \"$image\" >/dev/null 2>&1 || true\n")
            f.write("      return 0\n")
            f.write("    fi\n")
            f.write("  fi\n")
            f.write("  if docker_pull \"$image\" >/dev/null 2>&1; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  echo \"[build_images] ERROR: cannot pull base image: $image\" >&2\n")
            f.write("  echo \"[build_images] Hint: set SEED_DOCKER_IO_MIRROR_ENDPOINT to a reachable mirror\" >&2\n")
            f.write("  return 1\n")
            f.write("}\n")
            f.write("\n")
            f.write("ensure_docker_daemon_config() {\n")
            f.write("  if [[ \"${SEED_IMAGE_DISTRIBUTION_MODE}\" == \"preload\" ]]; then return 0; fi\n")
            f.write("  if [[ -z \"${REGISTRY_PREFIX}\" ]]; then return 0; fi\n")
            f.write("  if [[ \"$(id -u)\" != \"0\" ]]; then return 0; fi\n")
            f.write("  if ! command -v systemctl >/dev/null 2>&1; then return 0; fi\n")
            f.write("  mkdir -p /etc/docker\n")
            f.write("  local result\n")
            f.write("  result=\"$(python3 - <<'PY'\n")
            f.write("import json\n")
            f.write("from pathlib import Path\n")
            f.write("import os\n")
            f.write("\n")
            f.write("registry = os.environ.get('REGISTRY_PREFIX', '')\n")
            f.write("mirror = os.environ.get('SEED_DOCKER_IO_MIRROR_ENDPOINT', '')\n")
            f.write("max_uploads = os.environ.get('SEED_DOCKER_MAX_CONCURRENT_UPLOADS', '1')\n")
            f.write("try:\n")
            f.write("    max_uploads_value = max(1, int(max_uploads))\n")
            f.write("except Exception:\n")
            f.write("    max_uploads_value = 1\n")
            f.write("p = Path('/etc/docker/daemon.json')\n")
            f.write("data = {}\n")
            f.write("if p.exists():\n")
            f.write("    try:\n")
            f.write("        data = json.loads(p.read_text(encoding='utf-8'))\n")
            f.write("    except Exception:\n")
            f.write("        data = {}\n")
            f.write("\n")
            f.write("before = json.dumps(data, sort_keys=True)\n")
            f.write("insec = set(data.get('insecure-registries', []) or [])\n")
            f.write("if registry and '/' not in registry:\n")
            f.write("    insec.add(registry)\n")
            f.write("    if ':' in registry:\n")
            f.write("        port = registry.rsplit(':', 1)[1]\n")
            f.write("        insec.add(f'127.0.0.1:{port}')\n")
            f.write("        insec.add(f'localhost:{port}')\n")
            f.write("data['insecure-registries'] = sorted(insec)\n")
            f.write("\n")
            f.write("mirrors = list(data.get('registry-mirrors', []) or [])\n")
            f.write("if mirror and mirror not in mirrors:\n")
            f.write("    mirrors.append(mirror)\n")
            f.write("data['registry-mirrors'] = mirrors\n")
            f.write("data['max-concurrent-uploads'] = max_uploads_value\n")
            f.write("\n")
            f.write("after = json.dumps(data, sort_keys=True)\n")
            f.write("if after != before:\n")
            f.write("    p.write_text(json.dumps(data, indent=2) + '\\n', encoding='utf-8')\n")
            f.write("    print('changed')\n")
            f.write("else:\n")
            f.write("    print('unchanged')\n")
            f.write("PY\n")
            f.write(")\"\n")
            f.write("  if [[ \"${result}\" == \"changed\" ]]; then\n")
            f.write("    systemctl restart docker >/dev/null 2>&1 || true\n")
            f.write("    sleep 2\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write('export REGISTRY_ENDPOINT="${REGISTRY_PREFIX%%/*}"\n')
            f.write('if [[ -z "${REGISTRY_LOCAL_ENDPOINT}" ]] && [[ "${REGISTRY_ENDPOINT}" == *:* ]] && [[ "${REGISTRY_ENDPOINT}" != 127.0.0.1:* ]] && [[ "${REGISTRY_ENDPOINT}" != localhost:* ]]; then REGISTRY_LOCAL_ENDPOINT="127.0.0.1:${REGISTRY_ENDPOINT##*:}"; fi\n')
            f.write('export REGISTRY_PROBE_ENDPOINT="${REGISTRY_LOCAL_ENDPOINT:-${REGISTRY_ENDPOINT}}"\n')
            f.write("registry_probe() {\n")
            f.write("  if [[ -z \"${REGISTRY_PROBE_ENDPOINT}\" ]]; then return 0; fi\n")
            f.write("  if command -v curl >/dev/null 2>&1; then\n")
            f.write("    curl -m 5 -fsS \"http://${REGISTRY_PROBE_ENDPOINT}/v2/\" >/dev/null\n")
            f.write("  elif command -v wget >/dev/null 2>&1; then\n")
            f.write("    wget -q -T 5 -O /dev/null \"http://${REGISTRY_PROBE_ENDPOINT}/v2/\"\n")
            f.write("  else\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write("wait_for_registry() {\n")
            f.write("  local retries=\"${1:-6}\"\n")
            f.write("  local attempt=1\n")
            f.write("  while [ \"${attempt}\" -le \"${retries}\" ]; do\n")
            f.write("    if registry_probe; then\n")
            f.write("      return 0\n")
            f.write("    fi\n")
            f.write("    sleep \"${attempt}\"\n")
            f.write("    attempt=$((attempt + 1))\n")
            f.write("  done\n")
            f.write("  return 1\n")
            f.write("}\n")
            f.write("\n")
            f.write("local_push_image_ref() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if [[ -z \"${REGISTRY_LOCAL_ENDPOINT}\" ]] || [[ -z \"${REGISTRY_PREFIX}\" ]]; then\n")
            f.write("    echo \"${image}\"\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  local suffix=\"${image#${REGISTRY_PREFIX}/}\"\n")
            f.write("  if [[ \"${suffix}\" == \"${image}\" ]]; then\n")
            f.write("    echo \"${image}\"\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  echo \"${REGISTRY_LOCAL_ENDPOINT}/${suffix}\"\n")
            f.write("}\n")
            f.write("\n")
            f.write("docker_push_with_timeout() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if command -v timeout >/dev/null 2>&1; then\n")
            f.write("    timeout \"${REGISTRY_PUSH_TIMEOUT_SECONDS}\" docker push \"${image}\"\n")
            f.write("  else\n")
            f.write("    docker push \"${image}\"\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write("retry_push() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  if [[ -z \"${REGISTRY_PREFIX}\" ]]; then return 0; fi\n")
            f.write("  local attempt=1\n")
            f.write("  while [ \"${attempt}\" -le \"${REGISTRY_PUSH_RETRIES}\" ]; do\n")
            f.write("    if ! wait_for_registry 3; then\n")
            f.write("      echo \"[build_images] registry probe failed before push attempt ${attempt}/${REGISTRY_PUSH_RETRIES}: ${REGISTRY_PROBE_ENDPOINT}\" >&2\n")
            f.write("    fi\n")
            f.write("    if docker_push_with_timeout \"${image}\"; then\n")
            f.write("      return 0\n")
            f.write("    fi\n")
            f.write("    if [ \"${attempt}\" -ge \"${REGISTRY_PUSH_RETRIES}\" ]; then\n")
            f.write("      break\n")
            f.write("    fi\n")
            f.write("    local sleep_seconds=$((REGISTRY_PUSH_BACKOFF_SECONDS * attempt))\n")
            f.write("    echo \"[build_images] retrying push ${image} in ${sleep_seconds}s (${attempt}/${REGISTRY_PUSH_RETRIES})\" >&2\n")
            f.write("    sleep \"${sleep_seconds}\"\n")
            f.write("    attempt=$((attempt + 1))\n")
            f.write("  done\n")
            f.write("  echo \"[build_images] ERROR: push failed after ${REGISTRY_PUSH_RETRIES} attempts: ${image}\" >&2\n")
            f.write("  return 1\n")
            f.write("}\n")
            f.write("\n")
            f.write("seedemu_build_and_push() {\n")
            f.write("  local image=\"$1\"\n")
            f.write("  local context_dir=\"$2\"\n")
            f.write("  docker build -t \"${image}\" \"${context_dir}\"\n")
            f.write("  if [[ \"${SEED_IMAGE_DISTRIBUTION_MODE}\" == \"preload\" ]]; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  if [[ -n \"${REGISTRY_PREFIX}\" ]]; then\n")
            f.write("    local push_image\n")
            f.write("    push_image=\"$(local_push_image_ref \"${image}\")\"\n")
            f.write("    if [[ \"${push_image}\" != \"${image}\" ]]; then\n")
            f.write("      docker tag \"${image}\" \"${push_image}\"\n")
            f.write("    fi\n")
            f.write("    retry_push \"${push_image}\"\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("\n")
            f.write("seedemu_copy_and_push_image() {\n")
            f.write("  local source_image=\"$1\"\n")
            f.write("  local target_image=\"$2\"\n")
            f.write("  ensure_image_present \"${source_image}\"\n")
            f.write("  docker tag \"${source_image}\" \"${target_image}\"\n")
            f.write("  if [[ \"${SEED_IMAGE_DISTRIBUTION_MODE}\" == \"preload\" ]]; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  if [[ -n \"${REGISTRY_PREFIX}\" ]]; then\n")
            f.write("    local push_image\n")
            f.write("    push_image=\"$(local_push_image_ref \"${target_image}\")\"\n")
            f.write("    if [[ \"${push_image}\" != \"${target_image}\" ]]; then\n")
            f.write("      docker tag \"${target_image}\" \"${push_image}\"\n")
            f.write("    fi\n")
            f.write("    retry_push \"${push_image}\"\n")
            f.write("  fi\n")
            f.write("}\n")
            f.write("export -f registry_probe wait_for_registry local_push_image_ref docker_push_with_timeout retry_push seedemu_build_and_push seedemu_copy_and_push_image\n")
            f.write("\n")
            f.write("prepare_dummy_image() {\n")
            f.write("  local base_image=\"$1\"\n")
            f.write("  local dummy_tag=\"$2\"\n")
            f.write("  if docker image inspect \"$dummy_tag\" >/dev/null 2>&1; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  if ! docker image inspect \"$base_image\" >/dev/null 2>&1; then\n")
            f.write("    local ctx=\"base_images/${dummy_tag}\"\n")
            f.write("    if [ -f \"${ctx}/Dockerfile\" ]; then\n")
            f.write("      echo \"[build_images] building base image: ${base_image} (from ${ctx})\" >&2\n")
            f.write("      # Pre-pull common upstream bases via mirror+tag to avoid Docker Hub outages.\n")
            f.write("      ensure_image_present \"ubuntu:20.04\"\n")
            f.write("      docker build -t \"${base_image}\" \"${ctx}\"\n")
            f.write("    else\n")
            f.write("      ensure_image_present \"$base_image\"\n")
            f.write("    fi\n")
            f.write("  fi\n")
            f.write("  mkdir -p dummies\n")
            f.write("  local df=\"dummies/${dummy_tag}.Dockerfile\"\n")
            f.write("  printf 'FROM %s\\n' \"$base_image\" > \"$df\"\n")
            f.write("  docker build -t \"$dummy_tag\" -f \"$df\" dummies >/dev/null\n")
            f.write("}\n")
            f.write("\n")
            f.write("load_prefetched_images() {\n")
            f.write("  if [ ! -d prefetched_images ]; then\n")
            f.write("    return 0\n")
            f.write("  fi\n")
            f.write("  local tarball\n")
            f.write("  shopt -s nullglob\n")
            f.write("  for tarball in prefetched_images/*.tar; do\n")
            f.write("    echo \"[build_images] loading prefetched image: ${tarball}\" >&2\n")
            f.write("    docker load -i \"${tarball}\" >/dev/null\n")
            f.write("  done\n")
            f.write("  shopt -u nullglob\n")
            f.write("}\n")
            f.write("\n")
            f.write("ensure_docker_daemon_config\n")
            f.write("load_prefetched_images\n")

            if used_images:
                f.write('echo "[build_images] preparing base-image dummies"\n')
                for image in used_images:
                    digest = md5(image.encode("utf-8")).hexdigest()
                    f.write(f'prepare_dummy_image "{image}" "{digest}"\n')
                f.write("\n")
            f.write('JOBS_FILE="$(mktemp)"\n')
            f.write('cleanup() { rm -f "${JOBS_FILE}"; }\n')
            f.write('trap cleanup EXIT\n')
            f.write("cat > \"${JOBS_FILE}\" <<'JOBS'\n")
            f.write("\n".join(self.__build_commands))
            f.write("\nJOBS\n")
            f.write('if [ "${PARALLELISM}" -le 1 ]; then\n')
            f.write('  while IFS= read -r cmd; do\n')
            f.write('    [ -z "${cmd}" ] && continue\n')
            f.write('    echo "+ ${cmd}"\n')
            f.write('    eval "${cmd}"\n')
            f.write('  done < "${JOBS_FILE}"\n')
            f.write('else\n')
            # Run each full line as one job (preserve spaces in the docker commands).
            f.write("  awk 'NF' \"${JOBS_FILE}\" | xargs -P \"${PARALLELISM}\" -d '\\n' -I {} bash -lc 'set -euo pipefail; cmd=\"{}\"; echo \"+ ${cmd}\"; eval \"${cmd}\"'\n")
            f.write('fi\n')
        os.chmod('build_images.sh', 0o755)

        image_refs = []
        for command in self.__build_commands:
            parts = shlex.split(command)
            if len(parts) >= 2 and parts[0] == 'seedemu_build_and_push':
                image_refs.append(parts[1])
            elif len(parts) >= 3 and parts[0] == 'seedemu_copy_and_push_image':
                image_refs.append(parts[2])
        with open('images.txt', 'w') as f:
            if image_refs:
                f.write("\n".join(image_refs) + "\n")

        # Generate .env file
        self.generateEnvFile(Scope(0), '') # Simplified scope handling

    def _compileNetK8s(self, net: Network) -> str:
        """Generates NetworkAttachmentDefinition for a network.
        
        Supports multiple CNI types:
        - bridge: Local bridge (single-node)
        - macvlan: For cross-node with L2 access
        - ipvlan: For cross-node networking
        """
        name = self._getRealNetName(net).replace('_', '-').lower()
        prefix = str(net.getPrefix())

        cni_type = self._resolveNetworkCniType(net)

        # Build CNI config based on cni_type
        if cni_type == "macvlan":
            config = {
                "cniVersion": "0.3.1",
                "type": "macvlan",
                "master": self.__cni_master_interface,
                "mode": "bridge",
                "ipam": {
                    "type": "static"  # We manage IPs inside the container
                }
            }
        elif cni_type == "ipvlan":
            config = {
                "cniVersion": "0.3.1",
                "type": "ipvlan",
                "master": self.__cni_master_interface,
                "mode": "l2",
                "ipam": {
                    "type": "static"
                }
            }
        elif cni_type == "host-local":
            config = {
                "cniVersion": "0.3.1",
                "type": "bridge",
                # The Linux bridge device lives at node scope (not K8s namespace scope).
                # If we only hash `name`, different namespaces compiling the same topology
                # (e.g., multiple smoke runs) will share the same L2 segment and collide on
                # IPs/MACs, causing flaky BGP/OSPF behavior. Salt with namespace to isolate.
                "bridge": self._safeBridgeName(f"{self.__namespace}:{name}"),
                "isGateway": False,
                "ipam": {
                    "type": "host-local",
                    "subnet": prefix
                }
            }
        else:  # Default: bridge (single-node)
            config = {
                "cniVersion": "0.3.1",
                "type": "bridge",
                # Same rationale as host-local branch: isolate bridge names per namespace.
                "bridge": self._safeBridgeName(f"{self.__namespace}:{name}"),
                "ipam": {}  # No IPAM, we manage IPs inside
            }

        manifest = f"""apiVersion: "k8s.cni.cncf.io/v1"
kind: NetworkAttachmentDefinition
metadata:
  name: {name}
  namespace: {self.__namespace}
spec:
  config: '{json.dumps(config)}'
"""
        return manifest

    def _resolveNetworkCniType(self, net: Network) -> str:
        net_type = net.getType()
        if net_type in {NetworkType.Local, NetworkType.CrossConnect}:
            if self.__local_link_cni_type:
                return self.__local_link_cni_type
            if self.__scheduling_strategy == SchedulingStrategy.BY_AS_HARD and self.__cni_type in {"macvlan", "ipvlan"}:
                return "bridge"
        return self.__cni_type

    def _compileNodeK8s(self, node: Node) -> str:
        """Compile a node to Kubernetes Deployment manifest or KubeVirt VirtualMachine.
        
        Includes:
        - Scheduling constraints (nodeSelector based on strategy)
        - Resource requests/limits
        - Enhanced labels for AS and role identification
        - Optional Service generation
        """
        self._current_node = node

        # Check virtualization mode
        # Virtualization split point: "KubeVirt" -> VirtualMachine, otherwise Deployment.
        if node.getVirtualizationMode() == "KubeVirt":
            result = self._compileNodeKubeVirt(node)

            if self.__generate_services:
                node_name = self._getComposeNodeName(node).replace('_', '-').lower()
                asn = str(node.getAsn())
                role = self._nodeRoleToString(node.getRole())
                labels = {
                    "app": node_name,
                    "seedemu.io/asn": asn,
                    "seedemu.io/role": role,
                    "seedemu.io/name": node.getName(),
                    "kubevirt.io/domain": node_name
                }
                service = self._compileServiceK8s(node, node_name, labels)
                if service:
                    result += "\n---\n" + service

            return result

        # 1. Prepare Docker build context (reuse logic from Docker compiler)
        real_nodename = self._getRealNodeName(node)

        # Ensure the directory exists
        if not os.path.exists(real_nodename):
            mkdir(real_nodename)

        # We need to change directory to generate the Dockerfile in the right place
        cwd = os.getcwd()
        chdir(real_nodename)

        # Generate Dockerfile
        # This will call _addFile, which we intercept to generate the address script
        image, _ = self._selectImageFor(node)
        dockerfile = self._computeDockerfile(node)
        with open('Dockerfile', 'w') as f:
            f.write(dockerfile)

        chdir(cwd)

        # 2. Add build command
        # If registry_prefix is empty, don't add slash
        if self.__registry_prefix:
            full_image_name = f"{self.__registry_prefix}/{real_nodename}:latest"
        else:
            full_image_name = f"{real_nodename}:latest"
            
        build_context = shlex.quote(f"./{real_nodename}")
        build_image = shlex.quote(full_image_name)
        build_cmd = f"seedemu_build_and_push {build_image} {build_context}"
        self.__build_commands.append(build_cmd)

        # 3. Generate Deployment Manifest
        node_name = self._getComposeNodeName(node).replace('_', '-').lower()  # K8s names must be DNS compliant
        asn = str(node.getAsn())
        role = self._nodeRoleToString(node.getRole())

        # Compute networks annotation
        annotations = {}
        if self.__use_multus:
            nets = []
            net_specs = []
            needs_json_annotation = False
            for iface in node.getInterfaces():
                net = iface.getNet()
                net_name = self._getRealNetName(net).replace('_', '-').lower()
                nets.append(net_name)
                resolved_cni_type = self._resolveNetworkCniType(net)
                if resolved_cni_type in {"macvlan", "ipvlan"}:
                    prefix_len = net.getPrefix().prefixlen
                    net_specs.append({
                        "name": net_name,
                        "ips": [f"{iface.getAddress()}/{prefix_len}"]
                    })
                    needs_json_annotation = True
                else:
                    net_specs.append({
                        "name": net_name,
                    })
                if resolved_cni_type != self.__cni_type:
                    needs_json_annotation = True

            if needs_json_annotation and net_specs:
                # Static IPAM requires IPs in Multus runtime config. Use JSON form annotation
                # so each secondary interface gets deterministic seed-emulator addresses.
                annotations["k8s.v1.cni.cncf.io/networks"] = json.dumps(net_specs)
            elif nets:
                annotations["k8s.v1.cni.cncf.io/networks"] = ", ".join(nets)

        # Compute Envs
        envs = [{"name": "CONTAINER_NAME", "value": node_name}]

        for o, s in node.getScopedRuntimeOptions():
            envs.append({"name": o.name.upper(), "value": str(o.value)})

        # Build enhanced labels for identification and service discovery
        labels = {
            "app": node_name,
            "seedemu.io/asn": asn,
            "seedemu.io/role": role,
            "seedemu.io/name": node.getName(),
            "seedemu.io/workload": "seedemu",
        }

        # Build pod spec
        pod_spec = {
            "containers": [{
                "name": "main",
                "image": full_image_name,
                "imagePullPolicy": self.__image_pull_policy,
                "securityContext": {"privileged": True, "capabilities": {"add": ["ALL"]}},
                "command": ["/start.sh"],
                "env": envs,
                "volumeMounts": []
            }]
        }

        # Add resource requests/limits if configured
        if self.__default_resources:
            pod_spec["containers"][0]["resources"] = self.__default_resources

        # Add scheduling constraints based on strategy
        self._applySchedulingConstraints(pod_spec, node, asn, role, labels)

        manifest = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": node_name,
                "namespace": self.__namespace,
                "labels": labels
            },
            "spec": {
                "replicas": 1,
                "selector": {"matchLabels": {"app": node_name}},
                "template": {
                    "metadata": {
                        "labels": labels,
                        "annotations": annotations
                    },
                    "spec": pod_spec
                }
            }
        }

        result = json.dumps(manifest)

        # Generate Service if enabled
        if self.__generate_services:
            service = self._compileServiceK8s(node, node_name, labels)
            if service:
                result += "\n---\n" + service

        return result

    def _computeNodeSelector(self, node: Node, asn: str, role: str) -> Dict[str, str]:
        """Compute nodeSelector based on scheduling strategy."""
        if self.__scheduling_strategy in {
            SchedulingStrategy.NONE,
            SchedulingStrategy.AUTO,
            SchedulingStrategy.BY_AS,
            SchedulingStrategy.BY_ROLE,
        }:
            return {}

        node_key = f"{asn}_{node.getName()}"
        if node_key in self.__node_labels:
            return self.__node_labels[node_key]
        if asn in self.__node_labels:
            return self.__node_labels[asn]

        if self.__scheduling_strategy == SchedulingStrategy.BY_AS_HARD:
            raise AssertionError(
                f"SchedulingStrategy.BY_AS_HARD requires an explicit nodeSelector mapping for ASN {asn}. "
                f"Pass SEED_NODE_LABELS_JSON with an entry for ASN {asn}, for example: "
                f'{{"{asn}": {{"kubernetes.io/hostname": "node-name"}}}}'
            )

        if self.__scheduling_strategy == SchedulingStrategy.CUSTOM:
            return {}

        return {}

    def _computePodAffinity(self, asn: str, role: str) -> Dict[str, Any]:
        """Compute pod affinity rules for soft grouping strategies."""
        preferred_terms: List[Dict[str, Any]] = []

        if self.__scheduling_strategy in {SchedulingStrategy.AUTO, SchedulingStrategy.BY_AS}:
            preferred_terms.append({
                "weight": 90,
                "podAffinityTerm": {
                    "labelSelector": {
                        "matchExpressions": [{
                            "key": "seedemu.io/asn",
                            "operator": "In",
                            "values": [asn],
                        }]
                    },
                    "topologyKey": "kubernetes.io/hostname",
                }
            })

        if self.__scheduling_strategy in {SchedulingStrategy.AUTO, SchedulingStrategy.BY_ROLE}:
            preferred_terms.append({
                "weight": 40,
                "podAffinityTerm": {
                    "labelSelector": {
                        "matchExpressions": [{
                            "key": "seedemu.io/role",
                            "operator": "In",
                            "values": [role],
                        }]
                    },
                    "topologyKey": "kubernetes.io/hostname",
                }
            })

        if not preferred_terms:
            return {}

        return {
            "podAffinity": {
                "preferredDuringSchedulingIgnoredDuringExecution": preferred_terms
            }
        }

    def _computeTopologySpreadConstraints(self) -> List[Dict[str, Any]]:
        """Compute topology spread constraints for automatic balancing."""
        if self.__scheduling_strategy != SchedulingStrategy.AUTO:
            return []

        return [{
            "maxSkew": 1,
            "topologyKey": "kubernetes.io/hostname",
            "whenUnsatisfiable": "ScheduleAnyway",
            "labelSelector": {
                "matchLabels": {
                    "seedemu.io/workload": "seedemu"
                }
            }
        }]

    def _applySchedulingConstraints(
        self,
        pod_spec: Dict[str, Any],
        node: Node,
        asn: str,
        role: str,
        labels: Dict[str, str],
    ) -> None:
        """Apply nodeSelector/affinity/topology spread to a pod or VMI spec."""
        node_selector = self._computeNodeSelector(node, asn, role)
        if node_selector:
            pod_spec["nodeSelector"] = node_selector

        affinity = self._computePodAffinity(asn, role)
        if affinity:
            pod_spec["affinity"] = affinity

        spread = self._computeTopologySpreadConstraints()
        if spread:
            pod_spec["topologySpreadConstraints"] = spread

    def _compileServiceK8s(self, node: Node, node_name: str, labels: Dict[str, str]) -> Optional[str]:
        """Generate a Kubernetes Service for a node if needed."""
        ports = node.getPorts()
        
        # Only generate service if there are exposed ports or for routers
        if not ports and node.getRole() != NodeRole.Router:
            return None
        
        service_ports = []
        
        # Add ports defined on the node
        for (host_port, node_port, proto) in ports:
            service_ports.append({
                "name": f"port-{node_port}-{proto}",
                "port": node_port,
                "targetPort": node_port,
                "protocol": proto.upper()
            })
        
        # If no ports but it's a router, add a default SSH-like port for management
        if not service_ports:
            return None

        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": f"{node_name}-svc",
                "namespace": self.__namespace,
                "labels": labels
            },
            "spec": {
                "type": self.__service_type,
                "selector": {"app": node_name},
                "ports": service_ports
            }
        }
        
        return json.dumps(service)

    def _compileNodeKubeVirt(self, node: Node) -> str:
        """Compile a node to KubeVirt VirtualMachine manifest."""
        node_name = self._getComposeNodeName(node).replace('_', '-').lower()
        asn = str(node.getAsn())
        role = self._nodeRoleToString(node.getRole())

        # Fail-fast boundary for unsupported container-only features.
        self._assertKubeVirtCompatibility(node)

        # 1. Build Cloud-Init User Data
        user_data = {
            "packages": list(node.getSoftware()),
            "write_files": [],
            "runcmd": []
        }

        # Add files
        for f in node.getFiles():
            path, content = f.get()
            user_data["write_files"].append({
                "path": path,
                "content": content,
                "permissions": "0644"
            })

        # Generate and add replace_address.sh to configure static IPs on Multus interfaces.
        # For VMs, interface names are not always eth1/eth2 (predictable naming varies),
        # so the generated script falls back to auto-detection when needed.
        address_script = self._generateK8sAddressScript(interface_prefix="eth")
        user_data["write_files"].append({
            "path": "/usr/local/bin/replace_address.sh",
            "content": address_script,
            "permissions": "0755"
        })
        user_data["runcmd"].append(["/usr/local/bin/replace_address.sh"])

        # Routers need forwarding and relaxed rp_filter for asymmetric paths.
        user_data["runcmd"].extend([
            ["sh", "-c", "sysctl -w net.ipv4.ip_forward=1"],
            ["sh", "-c", "sysctl -w net.ipv4.conf.all.rp_filter=0"],
            ["sh", "-c", "sysctl -w net.ipv4.conf.default.rp_filter=0"],
        ])

        for command in node.getBuildCommands():
            user_data["runcmd"].append(self._toCloudInitRunCommand(command, False))

        for command in node.getBuildCommandsAtEnd():
            user_data["runcmd"].append(self._toCloudInitRunCommand(command, False))

        # Add start commands
        for cmd, fork in node.getStartCommands():
            user_data["runcmd"].append(self._toCloudInitRunCommand(cmd, fork))

        for cmd, fork in node.getPostConfigCommands():
            user_data["runcmd"].append(self._toCloudInitRunCommand(cmd, fork))

        cloud_init_yaml = "#cloud-config\n" + yaml.dump(user_data)

        # 2. Network Configuration
        networks = [{"name": "default", "pod": {}}]
        interfaces = [{"name": "default", "masquerade": {}}]

        for i, iface in enumerate(node.getInterfaces()):
            net = iface.getNet()
            net_name = self._getRealNetName(net).replace('_', '-').lower()

            networks.append({
                "name": f"net{i+1}",
                "multus": {"networkName": net_name}
            })
            interfaces.append({
                "name": f"net{i+1}",
                "bridge": {}
            })

        # 3. Build Manifest
        labels = {
            "app": node_name,
            "seedemu.io/asn": asn,
            "seedemu.io/role": role,
            "seedemu.io/name": node.getName(),
            "seedemu.io/workload": "seedemu",
            "kubevirt.io/domain": node_name
        }

        # Default base image (Ubuntu 22.04)
        # TODO: Make this configurable via options
        container_disk_image = "quay.io/containerdisks/ubuntu:22.04"
        cloud_init_secret_name = f"{node_name.replace('.', '-')}-cloudinit"

        cloud_init_secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {
                "name": cloud_init_secret_name,
                "namespace": self.__namespace,
                "labels": labels
            },
            "type": "Opaque",
            "stringData": {
                "userdata": cloud_init_yaml
            }
        }

        manifest = {
            "apiVersion": "kubevirt.io/v1",
            "kind": "VirtualMachine",
            "metadata": {
                "name": node_name,
                "namespace": self.__namespace,
                "labels": labels
            },
            "spec": {
                "runStrategy": "Always",
                "template": {
                    "metadata": {
                        "labels": labels
                    },
                    "spec": {
                        "domain": {
                            "devices": {
                                "disks": [
                                    {"name": "containerdisk", "disk": {"bus": "virtio"}},
                                    {"name": "cloudinitdisk", "disk": {"bus": "virtio"}}
                                ],
                                "interfaces": interfaces
                            },
                            "resources": {
                                "requests": {"memory": "512M"},
                                "limits": {"memory": "1024M"}
                            }
                        },
                        "networks": networks,
                        "volumes": [
                            {
                                "name": "containerdisk",
                                "containerDisk": {"image": container_disk_image}
                            },
                            {
                                "name": "cloudinitdisk",
                                "cloudInitNoCloud": {
                                    "secretRef": {
                                        "name": cloud_init_secret_name
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        # Add scheduling constraints
        self._applySchedulingConstraints(manifest["spec"]["template"]["spec"], node, asn, role, labels)

        return json.dumps(cloud_init_secret) + "\n---\n" + json.dumps(manifest)

    def _assertKubeVirtCompatibility(self, node: Node) -> None:
        unsupported_features: List[str] = []

        if node.getImportedFiles():
            unsupported_features.append("imported files")
        if node.getDockerCommands():
            unsupported_features.append("docker commands")
        if node.getDockerVolumes():
            unsupported_features.append("docker volumes")

        runtime_options = list(node.getScopedRuntimeOptions())
        if runtime_options:
            unsupported_features.append("runtime options")

        if unsupported_features:
            unsupported_list = ", ".join(unsupported_features)
            raise AssertionError(
                f"Node as{node.getAsn()}/{node.getName()} in KubeVirt mode has unsupported features: {unsupported_list}"
            )

    def _toCloudInitRunCommand(self, command: str, fork: bool) -> List[str]:
        command_value = f"{command} &" if fork else command
        return ["sh", "-c", command_value]

    def _addFile(self, path: str, content: str) -> str:
        """Override _addFile to intercept the replacement script generation."""
        if path == '/replace_address.sh' and self.__use_multus and self._current_node:
            # Generate K8s specific address replacement script
            content = self._generateK8sAddressScript()
        return super()._addFile(path, content)

    def _generateK8sAddressScript(self, interface_prefix: str = "net") -> str:
        """
        Generate a script to configure static IPs on Multus interfaces.

        - In containers, Multus interfaces are typically named net1/net2/...
        - In VMs (KubeVirt), interface names depend on predictable naming rules and
          are not reliably eth1/eth2/...

        The generated script prefers deterministic `${prefix}1..N` when present,
        otherwise it auto-detects non-default interfaces by ifindex order.
        """
        node = self._current_node
        iface_count = len(node.getInterfaces())

        script = "#!/bin/bash\n"
        script += "set -euo pipefail\n"
        script += "# K8s Address Replacement (Multus)\n\n"
        script += f"iface_prefix=\"{interface_prefix}\"\n"
        script += f"expected_ifaces={iface_count}\n\n"

        script += "declare -a seed_ifaces=()\n"
        script += "if [ -n \"${iface_prefix}\" ] && ip link show \"${iface_prefix}1\" >/dev/null 2>&1; then\n"
        script += "  for i in $(seq 1 ${expected_ifaces}); do\n"
        script += "    seed_ifaces+=(\"${iface_prefix}${i}\")\n"
        script += "  done\n"
        script += "else\n"
        script += "  default_if=\"$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')\"\n"
        script += "  [ -z \"${default_if}\" ] && default_if=\"eth0\"\n"
        script += "  mapfile -t seed_ifaces < <(\n"
        script += "    for dev in /sys/class/net/*; do\n"
        script += "      name=\"$(basename \"$dev\")\"\n"
        script += "      [ \"$name\" = \"lo\" ] && continue\n"
        script += "      [ \"$name\" = \"$default_if\" ] && continue\n"
        script += "      idx=\"$(cat \"$dev/ifindex\" 2>/dev/null || echo 9999)\"\n"
        script += "      echo \"$idx $name\"\n"
        script += "    done | sort -n | awk '{print $2}'\n"
        script += "  )\n"
        script += "fi\n\n"

        script += "configure_iface() {\n"
        script += "  local slot=\"$1\"\n"
        script += "  local addr=\"$2\"\n"
        script += "  local iface=\"${seed_ifaces[$slot]:-}\"\n"
        script += "  if [ -z \"$iface\" ]; then\n"
        script += "    echo \"Missing data interface index $slot for $addr\" >&2\n"
        script += "    return 1\n"
        script += "  fi\n"
        script += "  echo \"Configuring $iface with $addr\"\n"
        script += "  ip link set \"$iface\" up\n"
        script += "  ip addr flush dev \"$iface\" || true\n"
        script += "  ip addr add \"$addr\" dev \"$iface\"\n"
        script += "}\n\n"

        for i, iface in enumerate(node.getInterfaces()):
            addr = iface.getAddress()
            prefix_len = iface.getNet().getPrefix().prefixlen
            script += f"configure_iface {i} \"{addr}/{prefix_len}\"\n"

        return script

    def attachInternetMap(self, asn: int = -1, net: str = '', ip_address: str = '', 
                         port_forwarding: str = '') -> 'KubernetesCompiler':
        """!
        @brief Add the Internet Map visualization service to the Kubernetes deployment.
        
        @param asn the autonomous system number (not used in K8s deployment)
        @param net the network name (not used in K8s deployment)  
        @param ip_address the IP address (not used in K8s deployment)
        @param port_forwarding the port forwarding (not used in K8s deployment)

        @returns self, for chaining API calls.
        """
        if not self.__internet_map_enabled:
            return self
            
        self._log('attaching the Internet Map service to Kubernetes deployment')
        source_image, target_image = self._resolveInternetMapImages()
        if target_image != source_image:
            self.__build_commands.append(
                f"seedemu_copy_and_push_image {source_image} {target_image}"
            )
        
        # Generate Internet Map Kubernetes manifests
        internet_map_manifest = f"""
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: seedemu-internet-map
  namespace: {self.__namespace}
  labels:
    app: seedemu-internet-map
spec:
  replicas: 1
  selector:
    matchLabels:
      app: seedemu-internet-map
  template:
    metadata:
      labels:
        app: seedemu-internet-map
    spec:
      containers:
      - name: internet-map
        image: {target_image}
        ports:
        - containerPort: 8080
        imagePullPolicy: {self.__image_pull_policy}
        securityContext:
          privileged: true
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
---
apiVersion: v1
kind: Service
metadata:
  name: seedemu-internet-map-service
  namespace: {self.__namespace}
spec:
  type: NodePort
  selector:
    app: seedemu-internet-map
  ports:
  - port: 8080
    targetPort: 8080
"""
        
        self.__manifests.append(internet_map_manifest)
        self.__internet_map_enabled = False  # Prevent duplicate additions
        
        return self

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
import yaml


class SchedulingStrategy:
    """Scheduling strategy constants for Kubernetes node placement."""
    NONE = "none"           # No scheduling constraints
    AUTO = "auto"           # Automatic soft grouping + soft spreading
    BY_AS = "by_as"         # Schedule pods by AS number
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
            SchedulingStrategy.BY_ROLE,
            SchedulingStrategy.CUSTOM,
        }
        self.__scheduling_strategy = strategy if strategy in valid else SchedulingStrategy.NONE
        self.__node_labels = node_labels or {}
        self.__default_resources = default_resources or {}
        self.__cni_type = cni_type
        self.__cni_master_interface = cni_master_interface
        self.__generate_services = generate_services
        self.__service_type = service_type
        self.__image_pull_policy = image_pull_policy

    def getName(self) -> str:
        return "Kubernetes"


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

        # build_images.sh
        with open('build_images.sh', 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("set -e\n")
            # Docker BuildKit can be flaky on some teaching/workstation environments
            # (e.g., snapshot cache corruption). Default to legacy builder for
            # reproducibility; users can override by editing the script if needed.
            f.write("export DOCKER_BUILDKIT=0\n")
            f.write("\n".join(self.__build_commands))
            f.write("\n")
        os.chmod('build_images.sh', 0o755)

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
        
        # Build CNI config based on cni_type
        if self.__cni_type == "macvlan":
            config = {
                "cniVersion": "0.3.1",
                "type": "macvlan",
                "master": self.__cni_master_interface,
                "mode": "bridge",
                "ipam": {
                    "type": "static"  # We manage IPs inside the container
                }
            }
        elif self.__cni_type == "ipvlan":
            config = {
                "cniVersion": "0.3.1",
                "type": "ipvlan",
                "master": self.__cni_master_interface,
                "mode": "l2",
                "ipam": {
                    "type": "static"
                }
            }
        elif self.__cni_type == "host-local":
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
            
        self.__build_commands.append(f"docker build -t {full_image_name} ./{real_nodename}")
        
        # Only push if there is a registry
        if self.__registry_prefix:
            self.__build_commands.append(f"docker push {full_image_name}")

        # 3. Generate Deployment Manifest
        node_name = self._getComposeNodeName(node).replace('_', '-').lower()  # K8s names must be DNS compliant
        asn = str(node.getAsn())
        role = self._nodeRoleToString(node.getRole())

        # Compute networks annotation
        annotations = {}
        if self.__use_multus:
            nets = []
            net_specs = []
            for iface in node.getInterfaces():
                net = iface.getNet()
                net_name = self._getRealNetName(net).replace('_', '-').lower()
                nets.append(net_name)
                if self.__cni_type in {"macvlan", "ipvlan"}:
                    prefix_len = net.getPrefix().prefixlen
                    net_specs.append({
                        "name": net_name,
                        "ips": [f"{iface.getAddress()}/{prefix_len}"]
                    })

            if self.__cni_type in {"macvlan", "ipvlan"} and net_specs:
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

        if self.__scheduling_strategy == SchedulingStrategy.CUSTOM:
            # Use custom labels if provided
            # First check node-specific labels
            node_key = f"{asn}_{node.getName()}"
            if node_key in self.__node_labels:
                return self.__node_labels[node_key]
            # Then check AS-level labels
            if asn in self.__node_labels:
                return self.__node_labels[asn]
            # Fall back to no selector
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
        image: handsonsecurity/seedemu-multiarch-map:buildx-latest
        ports:
        - containerPort: 8080
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

# Kubernetes Implementation & Migration Report

## 1. Executive Summary

This report documents the transformation of the SEED Emulator from a deprecated Docker Compose architecture (single-host) to a modern, scalable Kubernetes architecture. The project is now capable of running complex network simulations across multiple physical nodes with self-healing capabilities and robust resource isolation.

**Key Achievements:**
*   **Scalability**: Moved from single-machine limits to multi-node K8s clusters.
*   **Resilience**: Achieved automatic failure recovery (Self-Healing).
*   **Resource Management**: Implemented strict CPU/RAM limits per node.
*   **Networking**: Integrated Multus CNI for complex, multi-interface network topologies (Bridge, Macvlan, Ipvlan).

---

## 2. Detailed Verification

We have validated the implementation against the following criteria:

| Feature | Test Case | Status | Notes |
|:---|:---|:---|:---|
| **Compilation** | `k8s_multinode_demo.py` | ✅ Pass | Generates valid YAML & build scripts. |
| **Image Building** | Local Registry Push | ✅ Pass | Images pushed to `localhost:5001`. |
| **Orchestration** | Pod Scheduling | ✅ Pass | Pods distributed across nodes (simulated). |
| **Connectivity** | Intra-AS Ping | ✅ Pass | Host <-> Router connectivity verified. |
| **Routing** | BGP Establishment | ✅ Pass | All BGP sessions (Stub <-> IX) Established. |
| **Service Discovery** | K8s Services | ✅ Pass | `ClusterIP` services created for Routers. |

---

## 3. Architecture Deep Dive

### 3.1 Legacy vs. New Architecture

#### Legacy: Docker Compose
*   **Structure**: Monolithic `docker-compose.yml`.
*   **Networking**: Standard Docker Bridge.
*   **Isolation**: Process-level (containers).
*   **Limitations**: No native multi-host support (Swarm is deprecated), no self-healing.

#### New: Kubernetes
*   **Structure**: Microservices-oriented (Pods/Deployments).
*   **Networking**: Multi-homed Pods via Multus CNI + Standard CNI Plugins.
*   **Isolation**: Pod-level with ResourceQuotas.
*   **Advantages**: Native multi-host, declarative state, extensive ecosystem.

### 3.2 Component Mapping

```mermaid
graph TD
    subgraph "Legacy (Docker)"
        D_CMP[Compiler] --> D_YML[docker-compose.yml]
        D_YML -->|Creates| D_NET[Docker Network (Bridge)]
        D_YML -->|Starts| D_CON[Container (Router/Host)]
        D_CON -->|Config| D_ENV[Env Vars]
    end

    subgraph "New (Kubernetes)"
        K_CMP[Compiler] --> K_YML[k8s.yaml]
        K_YML -->|Defines| K_NAD[NetworkAttachmentDefinition]
        K_YML -->|Defines| K_DEP[Deployment]
        K_YML -->|Defines| K_SVC[Service]
        
        K_DEP -->|Manages| K_POD[Pod]
        K_NAD -->|Used By| Multus[Multus CNI]
        Multus -->|Creates| K_INT[Pod Interface (net1..n)]
        
        K_POD -->|Config| K_ENV[Env Vars]
        K_POD -->|Accessible Via| K_SVC
    end
```

---

## 4. Codebase Evolution

### 4.1 Key Files Added
*   **`seedemu/compiler/Kubernetes.py`**:
    *   **Logic**: Implements `_doCompile` to generate K8s manifests instead of Compose files.
    *   **Networking**: Generates `NetworkAttachmentDefinition` for every network.
    *   **Nodes**: Generates `Deployment` for every node with `k8s.v1.cni.cncf.io/networks` annotation.
    *   **Address Management**: Injects `replace_address.sh` to configure IPs inside containers (bypassing cloud-native IPAM to satisfy simulation static IP needs).
*   **`examples/kubernetes/`**:
    *   `k8s_simple_as.py`: Single AS demo.
    *   `k8s_multinode_demo.py`: Multi-node capabilities demo.
    *   `setup_kind_cluster.sh` & `patch_kind_registry.sh`: Infrastructure automation.

### 4.2 Execution Flow

1.  **Instantiation**: User script creates `KubernetesCompiler(registry_prefix=..., use_multus=True)`.
2.  **Compilation**:
    *   Iterate Networks -> Generate `NetworkAttachmentDefinition` CRDs.
    *   Iterate Nodes -> Generate `Deployment` + `Service`.
    *   Compute Images -> Generate `Dockerfile` (reusing Docker compiler logic).
3.  **Artifact Generation**:
    *   `k8s.yaml`: The unified manifest.
    *   `build_images.sh`: Script to build/push Docker images.
4.  **Deployment**:
    *   User runs `kubectl apply -f k8s.yaml`.
    *   K8s Controller Manager sees Deployments -> Creates ReplicaSets -> Creates Pods.
    *   Scheduler assigns Pods to Nodes.
    *   Kubelet (on Node) calls Multus CNI.
    *   Multus calls bridge/macvlan CNI for each network in annotation.
    *   Container starts -> `start.sh` -> `replace_address.sh` -> IPs configured.

---

## 5. Usage

### 5.1 Prerequisites
*   Linux Environment
*   Docker
*   Kind (Kubernetes in Docker)
*   Kubectl

### 5.2 Running the Demo
```bash
# 1. Setup Infrastructure
./setup_kind_cluster.sh
./patch_kind_registry.sh
kubectl apply -f https://raw.githubusercontent.com/k8snetworkplumbingwg/multus-cni/master/deployments/multus-daemonset-thick.yml

# 2. Run Example
cd examples/kubernetes
PYTHONPATH=../.. python3 k8s_multinode_demo.py
cd output_multinode_bridge

# 3. Build & Deploy
./build_images.sh
kubectl create ns seedemu
kubectl apply -f k8s.yaml

# 4. Verify
kubectl get pods -n seedemu -o wide
```

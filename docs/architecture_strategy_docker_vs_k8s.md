# Architecture Strategy: Why Moving SEED Emulator from Docker Compose to Kubernetes?

> **Core Thesis**: Docker Compose architecture forces the entire "Internet" simulation to act as a single process-tree on a single kernel, limiting fidelity and scale. Kubernetes transforms the emulation from a "local process group" into a "distributed infrastructure," matching the distributed nature of the Internet itself.

This document outlines the specific architectural bottlenecks in the legacy `DockerCompiler` and how the generic `KubernetesCompiler` resolves them—not for the sake of using K8s, but to solve specific emulation challenges.

## 1. The "Single Kernel" Bottleneck (Networking)

### The Docker Compose Limitation
In the legacy implementation (`Docker.py`), every link in the simulation—regardless of whether it represents a trans-oceanic cable or a local LAN—is realized as a Linux Bridge or veth pair **on the same host kernel**.
*   **Packet Processing**: The host CPU must interrupt-switch every packet for every hop. A `traceroute` across 10 routers triggers 20+ context switches on the same CPU.
*   **Fidelity Loss**: Real Internet routing is distributed. Simulating it on one kernel introduces artificial contention that doesn't exist in reality.

### The K8s + Macvlan Breakthrough
Our K8s implementation (`Kubernetes.py:159`) introduces **Macvlan/Ipvlan CNI**.
*   **Benefit**: We can map a "Simulation Subnet" directly to a "Physical Switch VLAN".
*   **Result**: Packets travel safely "out of the box" to the physical network switch and back to another physical node. This moves the forwarding plane from software (Host CPU) to hardware (Physical Switch), enabling line-rate emulation speed that a single Docker host can never match.

## 2. The "Monolithic Configuration" Trap

### The Docker Compose Limitation
The `DockerCompiler` generates a single, massive `docker-compose.yml` (often 5,000+ lines for Mini-Internet).
*   **Failure Domain**: A syntax error in one AS definition crashes the entire deployment.
*   **Update Friction**: Changing one BGP routing policy in AS-151 requires restarting the entire compose stack (or complex partial apply).
*   **Lifecycle**: All nodes share the same lifecycle. You cannot "upgrade" a router; you recreate the universe.

### The K8s Declarative Model
We map each Node to an independent `Deployment`.
*   **Isolation**: AS-150 is totally decoupled from AS-2. If AS-150 crashes due to a bad config, AS-2 stays up. BGP neighbours will check timeout and re-route, **exactly like the real internet**.
*   **Atomic Updates**: We can patch AS-150's image and run `kubectl apply`. K8s performs a rolling update. The emulation *never stops*, it only converges—just like the real BGP protocol handles changes.

## 3. The "Static Resource" Ceiling

### The Docker Compose Limitation
`seed-emulator` runs heavyweight processes:
*   **BIRD (BGP Route Daemon)**: CPU intensive during convergence.
*   **Web Servers**: Memory intensive.
In Docker Compose, 100 routers fight for the same unconstrained CPU shares. If one router goes into a BGP calculation loop, it starves the others, causing artificial BGP session timeouts (Hold Timer Expired) that confuse students.

### The K8s Resource Scheduler
Our implementation introduces `resources.requests` and `limits` (`Kubernetes.py:287`).
*   **Guarantee**: We can guarantee AS-2 (backbone) routers get 1.0 CPU each, while Student AS routers get 0.1 CPU.
*   **Outcome**: Simulation stability. A student's misconfigured busy-loop script cannot crash the simulation backbone. This is critical for running multi-tenant classes or large experiments.

## 4. The "Localhost" Trap vs. Real Identifiers

### The Docker Compose Limitation
Docker specific DNS (container names) works only inside the bridge. It leaks "implementation details" (Docker's internal DNS) into the emulation.

### The K8s Service Abstraction
We automatically generate `Service` objects (`Kubernetes.py:353`).
*   **Abstraction**: Other components access `router-svc`, not a container IP.
*   **Integration**: This exposes simulation nodes to the outside world (via NodePort/DataPlane) using standard patterns, allowing external visualizations (like the Internet Map) or hardware routers to peer with virtual routers seamlessly.

## Summary Table

| Challenge | Docker Compose Approach | The "SEED" Limitation | Kubernetes Solution & Experience |
| :--- | :--- | :--- | :--- |
| **Scale** | Single Machine | Max ~100 nodes before CPU thrashing | **Multi-Node**: Scale to 1000s of nodes across a lab cluster. |
| **Failures** | "All or Nothing" | One bad script kills the lab | **Fault Isolation**: Problems stay in their Pod/AS. |
| **Network** | Linux Bridge | Host CPU is the bottleneck | **Hardware Offload**: Use physical switches via CNI. |
| **Recovery** | Manual `docker restart` | Does not simulate network recovery | **Self-Healing**: K8s replaces pods; Protocols (BGP) re-converge naturally. |

---
*This analysis explains why K8s was chosen: not for "buzzwords," but to solve the physical limitations of single-host network emulation.*

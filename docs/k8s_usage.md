# SEED Emulator: Kubernetes 使用指南（通用版）

本指南的目标是：把 SEED 的 K8s 方案“真的用起来”，并且在不同环境（本机 Kind、实验室多机、云上多机）都能复现，不会因为等待/网络抖动导致脚本卡死。

如果你要看长期维护与架构抽象，而不是只看操作步骤，请同时阅读：

- `docs/k3s_runtime_architecture.md`

仓库路径不固定，本文统一用：

- `<repo_root>`（例如：`/home/seed/seed-emulator-k8s`）

---

## 0. 核心概念（只讲和本项目直接相关的）

### Kubernetes / Kind / K3s

- `Kubernetes (K8s)`：编排系统，负责调度、自愈、声明式状态。
- `Kind`：用 Docker 容器模拟 K8s 节点。优点是快、稳定、适合快速验证；缺点是网络语义更偏“教学/模拟”。
- `K3s`：轻量 K8s 发行版，适合真实多机（包括云上 VM）部署。

### Multus / CNI

- `Multus`：让一个 Pod 拥有多网卡（SEED 拓扑需要多接口）。
- `CNI`：网卡/二层连接怎么做。对本项目最关键的参数是：
  - `bridge`/`host-local`：更偏单机/节点本地二层（Kind 上最稳）。
  - `macvlan`/`ipvlan`：更偏真实跨节点二层语义（更适合真实多机/K3s）。

### KubeVirt 是什么

`KubeVirt` 是把 “VM” 作为 K8s 工作负载的一层扩展（资源类型是 `VirtualMachine` / `VirtualMachineInstance`）。

在 SEED 里它的意义是：同一拓扑里，可以让部分节点（通常是 router）用 VM 形式运行，从而更贴近真实虚拟化/多机的边界条件。

---

## 1. 统一的路径护栏（强烈建议）

`development.env` 里是 `pwd` 注入 `PYTHONPATH`（有 cwd 漂移风险）。建议统一使用：

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh
```

这一步的目的：

- 固定 `REPO_ROOT` / `PYTHONPATH`，避免“换目录导入失败”。

### 常用环境变量（建议统一用 env 控）

- `SEED_NAMESPACE`: 部署命名空间（示例默认 `seedemu-kvtest` 或 `seedemu`）。
- `SEED_REGISTRY`: 镜像仓库前缀。
  - Kind 默认推荐 `localhost:5001`（本仓库 `setup_kubevirt_cluster.sh` 会配置 mirror）。
  - 多机/K3s 推荐 `<master_ip>:5000`（本仓库 `setup_k3s_cluster.sh` 会在 master 起 registry）。
- `SEED_CNI_TYPE`: `bridge|host-local|macvlan|ipvlan`。
- `SEED_CNI_MASTER_INTERFACE`: 仅当 `SEED_CNI_TYPE=macvlan/ipvlan` 时需要，必须是每台节点上真实存在的网卡名（云上常见 `eth0/ens3`）。
- `SEED_OUTPUT_DIR`: （可选）覆盖示例的输出目录；若是相对路径，将以示例脚本所在目录为基准解析。
- `SEED_IMAGE_PULL_POLICY`: （可选）`IfNotPresent|Always`。

---

## 2. Track A：本机 Kind（推荐用于快速验证）

### 2.1 创建 Kind + Multus + KubeVirt + Registry（一次性）

```bash
cd <repo_root>
SEED_CLUSTER_NAME=seedemu-kvtest WORKER_COUNT=2 ./setup_kubevirt_cluster.sh
kubectl config use-context kind-seedemu-kvtest
kubectl get nodes -o wide
```

说明：

- Kind 节点是容器，但 K8s 的调度/控制器/自愈语义是真实的。
- 这条链路适合验证编译产物正确性、工作负载可用性、协议与连通性检查。

#### 2.1.1 重要：Multus 的 `Text file busy` 问题（已在脚本中自动规避）

在某些环境中，Multus 的 initContainer 会把 `multus-shim` 直接 `cp` 到宿主机 `/opt/cni/bin/multus-shim`。
如果 kubelet/containerd 正在执行这个二进制，Linux 可能报错 `Text file busy`，导致：

- `kube-multus-ds` CrashLoop
- 所有 Pod 都会卡在 `ContainerCreating`（连 `coredns` 都起不来）

本仓库的 `setup_kubevirt_cluster.sh` 已自动把安装方式改成 “cp 到临时文件再 `mv` 原子替换”，避免覆盖正在执行的文件。

如果你是在“已有集群”上遇到这个问题，可以手工修复（一次即可）：

```bash
kubectl -n kube-system patch ds kube-multus-ds --type='strategic' -p '{
  "spec": {
    "template": {
      "spec": {
        "initContainers": [
          {
            "name": "install-multus-binary",
            "command": ["/bin/sh", "-c"],
            "args": [
              "set -eu; src=/usr/src/multus-cni/bin/multus-shim; dst=/host/opt/cni/bin/multus-shim; tmp=/host/opt/cni/bin/.multus-shim.tmp.$$; cp \"$src\" \"$tmp\"; chmod 0755 \"$tmp\"; mv -f \"$tmp\" \"$dst\";"
            ]
          }
        ]
      }
    }
  }
}'
kubectl -n kube-system rollout status ds/kube-multus-ds --timeout=300s
kubectl -n kube-system get pod -l name=multus -o wide
```

### 2.2 运行一个例子（以 `k8s_transit_as.py` 为例）

```bash
source scripts/env_seedemu.sh
export SEED_NAMESPACE=seedemu-kvtest
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_transit_as.py
cd output_transit_as
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl get pods -n "${SEED_NAMESPACE}" -o wide
```

### 2.3 一键验证链路（推荐，带证据输出）

如果你不是在“开发示例脚本”，而是想快速回答 “现在这套 K8s 后端到底能不能稳定跑通”，优先用仓库自带验证脚本：

```bash
cd <repo_root>
source scripts/env_seedemu.sh

# 建议先用 degraded（全容器）跑通链路，再切 full/auto 走 VM。
SEED_NAMESPACE=seedemu-local-quick \
SEED_REGISTRY=localhost:5001 \
SEED_CNI_TYPE=bridge \
SEED_RUNTIME_PROFILE=degraded \
SEED_CLEAN_NAMESPACE=true \
SEED_ARTIFACT_DIR="${REPO_ROOT}/output/kubevirt_validation_local_quick" \
./scripts/validate_kubevirt_hybrid.sh
```

它会做的事情（每一步都有 timeout，失败会落证据）：

- 编译示例 `examples/kubernetes/k8s_hybrid_kubevirt_demo.py`
- 构建并 push 镜像到 `SEED_REGISTRY`
- 清理并重建 namespace（避免脏状态影响）
- `kubectl apply` 部署 manifest，并等待 `Deployment/VMI` Ready
- 检查 BGP 是否 `Established`
- 做跨 AS ping 验证
- 删除一个关键 Pod，验证 deployment 自愈并记录恢复时间
- 输出证据到 `SEED_ARTIFACT_DIR/`（例如：`runtime_profile.json`、`bird_protocols.txt`、`pods_wide.txt`、`recovery_check.json`）

---

## 3. Track B：真实多机（K3s，适合云上/阿里环境）

这条路径的重点不是“能不能跑”，而是“多机网络语义到底是什么”，以及工作负载能否真实分布到多节点。

### 3.1 准备 3 台机器（示例：云上 3 台 VM）

你需要准备：

- 1 台 master + 2 台 worker（能互相 SSH）。
- 建议开放：SSH、K8s API（master 6443）、以及你用于镜像仓库的端口（默认 `5000`）。

### 3.2 一键安装 K3s + Multus（控制机运行）

在控制机（你现在这台机器）执行：

```bash
cd <repo_root>
source scripts/env_seedemu.sh

export SEED_K3S_MASTER_IP=1.2.3.4
export SEED_K3S_WORKER1_IP=1.2.3.5
export SEED_K3S_WORKER2_IP=1.2.3.6
export SEED_K3S_USER=ubuntu
export SEED_K3S_SSH_KEY=$HOME/.ssh/id_ed25519
export SEED_REGISTRY_HOST=${SEED_K3S_MASTER_IP}
export SEED_REGISTRY_PORT=5000
export SEED_K3S_CLUSTER_NAME=seedemu-k3s

./scripts/setup_k3s_cluster.sh
```

说明（避免“卡死”）：

- `setup_k3s_cluster.sh` 默认使用非交互 SSH（key-based）并要求远端 `sudo` 免密码；不满足会直接失败并提示原因（避免长时间卡住）。
- 如云上网络慢，可调大 Ansible 总超时：`export SEED_ANSIBLE_TIMEOUT=3600s`。

预期产物：

- kubeconfig 会输出到：`output/kubeconfigs/seedemu-k3s.yaml`

### 3.3 切换到 K3s 集群并运行例子

```bash
export KUBECONFIG="${REPO_ROOT}/output/kubeconfigs/seedemu-k3s.yaml"
kubectl get nodes -o wide

export SEED_NAMESPACE=seedemu-k3s-test
export SEED_REGISTRY=${SEED_REGISTRY_HOST}:${SEED_REGISTRY_PORT}
export SEED_CNI_TYPE=macvlan

# 找出 master 网卡名（云上常见是 eth0/ens3）
ip -o -4 route show to default | awk '{print $5; exit}'
export SEED_CNI_MASTER_INTERFACE=eth0

cd <repo_root>/examples/kubernetes
python3 k8s_transit_as.py
cd output_transit_as
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl get pods -n "${SEED_NAMESPACE}" -o wide
```

---

## 4. Runtime Profile：auto/full/degraded/strict（Hybrid/KubeVirt 场景）

`SEED_RUNTIME_PROFILE` 只影响需要 KubeVirt 的例子（例如 `k8s_hybrid_kubevirt_demo.py`）：

- `auto`：自动判断（推荐）。在 `arm64 + 无 /dev/kvm` 时自动降级。
- `full`：强制 VM 路径（路由器会编译成 `VirtualMachine`）。
- `degraded`：强制全容器（不生成 VM）。
- `strict`：要求 VM 必须可用，不满足就直接失败（避免“半跑半坏”卡住）。

查看决策证据：

- `examples/kubernetes/output_kubevirt_hybrid/runtime_profile.json`

---

## 5. “不卡死”策略（实用）

### 5.1 所有等待都必须有 timeout

你在脚本里尽量使用：

- `kubectl wait ... --timeout=...`
- BGP/连通性用重试次数和间隔控制，不用无限循环

### 5.2 卡住时优先收集证据

```bash
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
kubectl -n "${SEED_NAMESPACE}" get events --sort-by=.lastTimestamp | tail -n 50
kubectl -n "${SEED_NAMESPACE}" describe pod <pod>
kubectl -n "${SEED_NAMESPACE}" logs <pod> --tail=200
```

### 5.3 Kind 和多机不要混用同一套“网络结论”

- Kind + `bridge`：更像“节点本地二层”，为了稳定验证可能会有 colocate/放宽策略。
- K3s + `macvlan/ipvlan`：才是你要拿来回答“多机器如何连接”的真实语义。

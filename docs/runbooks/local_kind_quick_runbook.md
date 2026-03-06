# 本地快速跑通 Runbook（Kind + Multus + KubeVirt，含证据产物）

目标：在一台本机上，**稳定地**把 SEED Emulator 的 K8s 后端跑起来，并且输出一套可审阅的证据文件。

本 Runbook 假设仓库在：

- `<repo_root>`（例如：`/home/seed/seed-emulator-k8s`）

并且你希望“不要卡死”，所以所有等待都必须有 timeout，失败要有证据落盘。

---

## 0. 你将跑到什么程度（明确验收）

你将完成两条链路（建议都跑一次）：

1. **Degraded（全容器）**：最快、最稳定，用来回答“编译器后端和网络栈是不是整体健康”。
2. **Full（混合：VM 路由器 + 容器主机）**：验证 KubeVirt/VM 路径能跑，并记录典型的收敛窗口（第一次 ping 可能要重试几十秒）。

两条链路都用同一个验证脚本：

- `scripts/validate_kubevirt_hybrid.sh`

它会输出证据到你指定的 `SEED_ARTIFACT_DIR`。

---

## 1. 预检查（1 分钟确认环境没坑）

### 1.1 必需命令是否存在

```bash
command -v docker kubectl conda rg kind || true
docker version
kubectl version --client
```

预期：

- `docker` 可用（本机能启动容器）
- `kubectl` 可用
- `conda` 可用（我们用独立 python env）
- `kind` 如果没有也没关系，`setup_kubevirt_cluster.sh` 会自动安装

### 1.2 Conda 环境就绪（固定 Python 依赖）

```bash
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda env list | rg -n "seedemu-k8s-py310" || true
conda activate seedemu-k8s-py310
python -V
python -c "import yaml; import geopy; print('deps-ok')"
```

如果 `seedemu-k8s-py310` 不存在，按下面创建：

```bash
conda create -n seedemu-k8s-py310 python=3.10 -y
conda activate seedemu-k8s-py310
cd <repo_root>
pip install -r requirements.txt -r tests/requirements.txt
```

### 1.3 路径护栏（强制绝对 PYTHONPATH，避免 cwd 漂移）

```bash
cd <repo_root>
source scripts/env_seedemu.sh
python -c "import seedemu; print('seedemu-import-ok')"
echo "REPO_ROOT=$REPO_ROOT"
echo "PYTHONPATH=$PYTHONPATH"
```

对照 Docker Compose 的意义：

- Docker Compose 时代你一般在某个目录 `docker compose up` 就跑了。
- 这里我们必须确保 **编译器 import 的是仓库代码**，否则“换目录就坏”会非常隐蔽。

---

## 2. 一次性准备集群（Kind + 本地 registry + Multus + KubeVirt）

### 2.1 一键创建/修复集群

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_CLUSTER_NAME=seedemu-kvtest WORKER_COUNT=2 ./setup_kubevirt_cluster.sh
kubectl config use-context kind-seedemu-kvtest
```

这一步在干什么（对应 docker-compose）：

- Docker Compose：你本机的“调度器”就是你自己，人肉决定容器在哪跑。
- Kind：我们用 1 个 control-plane + 2 个 worker 模拟多节点集群，让调度/自愈/声明式资源这些 **K8s 语义真实存在**。
- 本地 registry：替代 docker-compose 里本地 build 后直接运行。K8s 需要能从 registry pull 镜像。
- Multus：让 Pod/VM 能有多网卡（SEED 的拓扑必须）。
- KubeVirt：让部分节点可以用 VM 形态跑（Full profile 用到）。

### 2.2 集群健康检查（必须过）

```bash
kubectl get nodes -o wide
kubectl -n kube-system get ds kube-multus-ds -o wide
kubectl -n kubevirt get pods -o wide
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' | rg -n "kind-registry|registry"
```

预期：

- nodes: 3 个节点都 `Ready`
- `kube-multus-ds`: `READY=3/3`
- kubevirt: `virt-operator/virt-api/virt-controller/virt-handler` 全部 Running
- `kind-registry` 在本机跑，端口通常是 `127.0.0.1:5001->5000`

### 2.3 重要坑：Multus 的 `Text file busy`（已自动规避）

如果你碰到：

- `kube-multus-ds` CrashLoop
- event 出现：`Text file busy` / `FailedCreatePodSandBox ... multus-shim`

你可以直接再跑一遍 `./setup_kubevirt_cluster.sh`；仓库已经把 Multus 的 shim 安装改成了“原子 mv 替换”，避免覆盖正在执行的二进制。

---

## 3. Track A：Degraded（全容器）一键验证（建议先跑）

目的：快速确认整个 K8s 后端链路“能编译、能 build/push、能部署、BGP 能起来、跨 AS 连通性有证据、自愈有证据”。

### 3.1 执行命令（推荐直接复制）

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_NAMESPACE=seedemu-local-quick \
SEED_REGISTRY=localhost:5001 \
SEED_CNI_TYPE=bridge \
SEED_RUNTIME_PROFILE=degraded \
SEED_CLEAN_NAMESPACE=true \
SEED_ARTIFACT_DIR="${REPO_ROOT}/output/kubevirt_validation_local_quick" \
./scripts/validate_kubevirt_hybrid.sh
```

### 3.2 你应当看到什么

- 脚本会打印 `Runtime profile: degraded -> degraded`
- 所有 Deployment `condition met`
- BGP 检查里出现 `Established`
- Connectivity `ping` 直接成功或在重试窗口内成功
- Self-healing check 会删除一个 web pod，并在几分钟内恢复

### 3.3 证据产物在哪里（跑完必看）

```bash
ls -la "${REPO_ROOT}/output/kubevirt_validation_local_quick"
cat "${REPO_ROOT}/output/kubevirt_validation_local_quick/runtime_profile.json"
cat "${REPO_ROOT}/output/kubevirt_validation_local_quick/recovery_check.json"
sed -n '1,80p' "${REPO_ROOT}/output/kubevirt_validation_local_quick/bird_protocols.txt"
```

对照 Docker Compose 的意义：

- Docker Compose：通常你“看见容器起来了”就算成功，但很难形成结构化证据。
- 这里：我们把关键结论（profile 决策、BGP、连通性、自愈）固化成文件，便于复现与审阅。

---

## 4. Track B：Full（混合：VM 路由器 + 容器主机）一键验证

目的：证明 VM 路径（KubeVirt）确实能跑起来，且多网卡/路由/BGP/连通性在同一条验证链路里成立。

注意：Full 模式下，**BGP Established 之后，跨 AS ping 可能要等一段收敛窗口**，所以脚本会重试（这是正常现象）。

### 4.1 执行命令

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_NAMESPACE=seedemu-local-full \
SEED_REGISTRY=localhost:5001 \
SEED_CNI_TYPE=bridge \
SEED_RUNTIME_PROFILE=full \
SEED_CLEAN_NAMESPACE=true \
SEED_ARTIFACT_DIR="${REPO_ROOT}/output/kubevirt_validation_local_full" \
./scripts/validate_kubevirt_hybrid.sh
```

### 4.2 运行时你可以边看边讲（实时观察点）

```bash
kubectl -n seedemu-local-full get pods -o wide
kubectl -n seedemu-local-full get vm,vmi -o wide
kubectl -n seedemu-local-full get events --sort-by=.lastTimestamp | tail -n 30
```

预期：

- 你会看到一个 `virt-launcher-...` pod（这是 VM 的承载 pod）
- 你会看到 `vmi/as150brd-router0-...` 最终 `Ready=True`

### 4.3 证据产物（跑完必看）

```bash
ls -la "${REPO_ROOT}/output/kubevirt_validation_local_full"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/runtime_profile.json"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/vm_vmi.txt"
cat "${REPO_ROOT}/output/kubevirt_validation_local_full/recovery_check.json"
```

---

## 5. 直接跑 3 个核心例子（不走验证脚本，适合你改代码时用）

这部分适合你要改 example 或者做更泛化的实验，而不是“只要证据”。

### 5.1 `k8s_transit_as.py`

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-transit-as
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_transit_as.py
cd output_transit_as
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
```

### 5.2 `k8s_mini_internet.py`

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-mini
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_mini_internet.py
cd output_mini_internet
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide
```

### 5.3 `k8s_mini_internet_with_visualization.py`（含 Internet Map）

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export SEED_NAMESPACE=seedemu-mini-viz
export SEED_REGISTRY=localhost:5001
export SEED_CNI_TYPE=bridge

cd examples/kubernetes
python3 k8s_mini_internet_with_visualization.py
cd output_mini_internet_with_viz
./build_images.sh

kubectl create ns "${SEED_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply -n "${SEED_NAMESPACE}" -f k8s.yaml
kubectl -n "${SEED_NAMESPACE}" get pods -o wide

# 访问可视化：更可靠的方式是 port-forward
kubectl -n "${SEED_NAMESPACE}" port-forward service/seedemu-internet-map-service 8080:8080
```

然后浏览器打开：

- `http://127.0.0.1:8080/`

---

## 6. 常见故障与“立刻定位”指令（不卡死的关键）

### 6.1 Pod 卡 `ContainerCreating`

优先看 event：

```bash
kubectl -n <ns> get events --sort-by=.lastTimestamp | tail -n 50
```

如果看到 `multus-shim` 相关错误：

```bash
kubectl -n kube-system get ds kube-multus-ds -o wide
kubectl -n kube-system get pods -l name=multus -o wide
```

结论：

- **Multus 不健康，整个 SEED 拓扑都不可能跑起来**（多网卡依赖）。

### 6.2 镜像 pull 失败（registry 链路问题）

```bash
docker ps | rg -n "kind-registry"
kubectl -n kube-public get cm local-registry-hosting -o yaml | sed -n '1,80p'
kubectl -n <ns> describe pod <pod> | rg -n "Failed|ImagePull|Back-off|pull" -n || true
```

### 6.3 BGP 不到 `Established`

```bash
kubectl -n <ns> get pods -l seedemu.io/name=router0 -o name
kubectl -n <ns> exec <router-pod> -- birdc s p
```

### 6.4 Full 模式下 VMI 不 Ready

```bash
kubectl -n <ns> get vm,vmi -o wide
kubectl -n <ns> describe vmi <vmi-name> | sed -n '1,260p'
kubectl -n kubevirt get pods -o wide
kubectl -n kubevirt logs -l kubevirt.io=virt-handler --tail=120 || true
```

---

## 7. 清理与复位（需要时再做）

### 7.1 删除某个实验 namespace

```bash
kubectl delete ns seedemu-local-quick --ignore-not-found
kubectl delete ns seedemu-local-full --ignore-not-found
```

### 7.2 删除 kind 集群（彻底重来）

```bash
kind delete cluster --name seedemu-kvtest
docker rm -f kind-registry || true
```

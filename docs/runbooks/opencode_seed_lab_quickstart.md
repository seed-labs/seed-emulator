# opencode + SEED Lab 统一入口（从空白环境到可用）

目标：给第一次接触该仓库的用户一个单文档入口，覆盖：

1. 环境安装（含 opencode 多系统安装方式）
2. 本地 k8s/k3s 运行前置
3. 智能体使用入口
4. mini-internet 的自动调度与严格调度两种模式
5. 常见故障与最小重试命令

---

## 0. 先看结论

你有两条路径：

1. 一键路径（推荐）
- 直接跑 `scripts/bootstrap_seed_lab_env.sh`
- 脚本会尽量自动完成：opencode、conda 环境、Python 依赖、kubectl/kind、可选 KVM+k3s

2. 手动路径
- 自己装 opencode + conda + 依赖，再跑本仓库脚本

无论走哪条路径，建议第一条命令都先执行：

```bash
cd /home/zzw4257/seed-k8s
scripts/seed_lab_entry_status.sh
```

它会先告诉你当前可用状态（KVM 数量、k3s 节点、kubeconfig、默认 namespace/profile）和下一条推荐命令，避免盲目直接跑长流水线。

---

## 1. 一键路径（推荐）

### 1.1 仅准备本机工具（不创建 KVM 集群）

```bash
cd /home/zzw4257/seed-k8s
scripts/bootstrap_seed_lab_env.sh base
```

### 1.2 完整准备（含 KVM+k3s 三节点）

```bash
cd /home/zzw4257/seed-k8s
scripts/bootstrap_seed_lab_env.sh all
```

### 1.3 仅检查当前状态（无破坏）

```bash
cd /home/zzw4257/seed-k8s
scripts/bootstrap_seed_lab_env.sh check
```

脚本位置：
- `scripts/bootstrap_seed_lab_env.sh`

---

## 2. 手动安装路径

## 2.1 安装 opencode（多系统）

官方推荐（Linux/macOS）：

```bash
curl -fsSL https://opencode.ai/install | bash
```

其他方式：

1. npm/bun/pnpm/yarn
```bash
npm i -g opencode-ai@latest
```

2. macOS/Linux（Homebrew）
```bash
brew install anomalyco/tap/opencode
```

3. Windows
- Scoop: `scoop install opencode`
- Chocolatey: `choco install opencode`

安装完成后验证：

```bash
opencode --version
opencode models
```

## 2.2 安装 conda 与 Python 环境

默认环境名：`seedemu-k8s-py310`

```bash
cd /home/zzw4257/seed-k8s
source /home/zzw4257/miniconda3/etc/profile.d/conda.sh
conda create -y -n seedemu-k8s-py310 python=3.10
conda activate seedemu-k8s-py310
pip install -r requirements.txt -r dev-requirements.txt
pip install -e .
```

## 2.3 准备仓库运行护栏

```bash
cd /home/zzw4257/seed-k8s
source scripts/env_seedemu.sh
```

---

## 3. 关键变量（必须理解）

最常用：

1. `KUBECONFIG`
- 连接哪个集群

2. `SEED_NAMESPACE`
- 资源部署到哪个 namespace

3. `SEED_EXPERIMENT_PROFILE`
- 运行哪个 profile（`mini_internet` / `transit_as` / `mini_internet_viz` / `hybrid_kubevirt`）

4. `SEED_CNI_TYPE`
- `macvlan|ipvlan|bridge|host-local`

5. `SEED_SCHEDULING_STRATEGY`
- `auto|none|by_as|by_role|custom`

6. `SEED_PLACEMENT_MODE`
- `auto`：自动分布（默认）
- `strict3`：严格三节点映射（用于强验收）

7. `SEED_NODE_LABELS_JSON`
- 仅在 `custom` / `strict3` 场景需要；否则可留空

8. `SEED_ARTIFACT_DIR` / `SEED_OUTPUT_DIR`
- 验证证据目录 / 编译输出目录

---

## 4. mini-internet 调度模式说明（核心）

当前已支持两种主模式：

1. `auto`（默认）
- 不再硬编码 ASN->节点映射
- 编译器使用自动软分组与软均衡（K8s 调度主导）
- placement 验收看 `placement_passed`

2. `strict3`
- 用固定 ASN->hostname 映射做强约束
- 用于“必须三节点且映射命中”的演示/验收
- placement 验收看 `strict3_passed`

设置示例：

```bash
export SEED_PLACEMENT_MODE=auto
export SEED_SCHEDULING_STRATEGY=auto
```

严格模式示例：

```bash
export SEED_PLACEMENT_MODE=strict3
export SEED_SCHEDULING_STRATEGY=custom
# 可选：提供 SEED_NODE_LABELS_JSON，否则验证脚本会按默认 strict3 模板生成
```

---

## 5. 启动智能体（opencode）

在仓库根目录启动：

```bash
cd /home/zzw4257/seed-k8s
opencode
```

本仓库默认：

1. agent：`seed-lab`
2. model：`opencode/minimax-m2.5-free`

建议命令顺序：

1. `/seed-lab-home`
- 先看“当前可用环境 / 可做任务 / 证据路径”

2. `/seed-lab-doctor`
- 只做体检，不部署

3. `/seed-lab-start`
- preflight -> compile -> build -> deploy

4. `/seed-lab-verify`
- placement + BGP + ping + recovery

5. `/seed-lab-observe`
- 采集运行态快照

6. `/seed-lab-kubectl`
- 根据当前上下文输出最常用 kubectl 查询

---

## 6. 不用智能体也可直接跑

```bash
cd /home/zzw4257/seed-k8s
source /home/zzw4257/miniconda3/etc/profile.d/conda.sh
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

scripts/seed_k8s_profile_runner.sh "${SEED_EXPERIMENT_PROFILE:-mini_internet}" doctor
scripts/seed_k8s_profile_runner.sh "${SEED_EXPERIMENT_PROFILE:-mini_internet}" start
scripts/seed_k8s_profile_runner.sh "${SEED_EXPERIMENT_PROFILE:-mini_internet}" verify
scripts/seed_k8s_profile_runner.sh "${SEED_EXPERIMENT_PROFILE:-mini_internet}" observe
scripts/seed_k8s_profile_runner.sh "${SEED_EXPERIMENT_PROFILE:-mini_internet}" report
```

---

## 7. 常用 kubectl（给 docker-compose 迁移用户）

对照关系：

1. `docker compose ps` -> `kubectl get pods -o wide`
2. `docker compose logs` -> `kubectl logs`
3. `docker compose restart <svc>` -> `kubectl rollout restart deployment/<name>`
4. `docker compose exec` -> `kubectl exec -it`

常用命令（假设已设置 `KUBECONFIG` 与 `NS`）：

```bash
export NS="${SEED_NAMESPACE}"
kubectl --kubeconfig "${KUBECONFIG}" get nodes -o wide
kubectl --kubeconfig "${KUBECONFIG}" -n "${NS}" get pods -o wide
kubectl --kubeconfig "${KUBECONFIG}" -n "${NS}" get deploy -o wide
kubectl --kubeconfig "${KUBECONFIG}" -n "${NS}" get vm,vmi -o wide
kubectl --kubeconfig "${KUBECONFIG}" -n "${NS}" get events --sort-by=.lastTimestamp | tail -n 40
```

---

## 8. 关键证据目录

1. 运行入口状态
- `output/assistant_entry/latest/summary.json`

2. 验证主证据
- `output/multinode_mini_validation/<timestamp>/summary.json`
- `output/multinode_mini_validation/<timestamp>/placement_check.json`
- `output/multinode_mini_validation/<timestamp>/bird_router151.txt`
- `output/multinode_mini_validation/<timestamp>/ping_150_to_151.txt`
- `output/multinode_mini_validation/<timestamp>/recovery_check.json`

3. profile 统一产物
- `output/profile_runs/<profile>/latest/`

4. 报告
- `output/profile_runs/<profile>/latest/report/report.json`
- `output/seedlab_reports/latest/report.json`

---

## 9. 故障分流（最小重试）

1. `kubectl ... localhost:8080 refused`
```bash
scripts/k3s_fetch_kubeconfig.sh && scripts/validate_k3s_mini_internet_multinode.sh preflight
```

2. `Cannot read SSH key`
```bash
export SEED_K3S_SSH_KEY=/path/to/key
scripts/validate_k3s_mini_internet_multinode.sh preflight
```

3. `PLACEMENT_FAILED`
```bash
scripts/validate_k3s_mini_internet_multinode.sh verify
cat "${SEED_ARTIFACT_DIR}/placement_check.json"
```

4. `BGP_NOT_ESTABLISHED` / `CONNECTIVITY_FAILED` / `RECOVERY_FAILED`
```bash
scripts/validate_k3s_mini_internet_multinode.sh verify
```

---

## 10. 破坏性动作确认

以下动作必须先确认再执行：

1. 删除 namespace
2. 删除 pod 做故障注入
3. 重建 k3s 集群（`scripts/setup_k3s_cluster.sh`）

确认短语规范：

`CONFIRM_SEED_DESTRUCTIVE: <target>`

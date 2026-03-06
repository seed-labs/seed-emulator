# 2026-03-05 记录：K3s+KVM 多节点复现（mini_internet）+ Real Topology RR（214/1897）迁移到本仓库

> 本文件是**一次性统一记录**：把我们之前做过的事情、做法、入口、产物与人工检查方式写清楚。  
> 目标：任何人**不借助 AI**，只按本文就能复现并理解 `mini_internet` 与 `real_topology_rr`（K3s 多节点）的运行模式与验证方式。

给不熟 K8s、只想抓住“怎么跑 / 怎么看证据 / 怎么问 AI”的同学，优先看：

- `docs/runbooks/seed_lab_evidence_first_operator_guide.md`

---

## 0. 时间戳与范围

- 记录日期：`2026-03-05`
- 本仓库：`/home/seed/seed-emulator-k8s`
- 本记录覆盖两条线：
  1. **历史（外部目录）**：`~/lxl_topology/autocoder_test` 下基于 `RR_214_example.py` 的大规模 Docker Compose 运行（1899 服务）与经验总结。
  2. **本仓库（K8s/K3s 多节点）**：迁移为 `examples/kubernetes/k8s_real_topology_rr.py` + profile/validate 一键链路，并补齐 RR iBGP 支持。

## 0.1 今日实测结果（证据为准）

- `mini_internet`（K3s 多节点）：
  - 结果：PASS
  - RunID：`output/profile_runs/mini_internet/20260305_202033`
  - 汇总：`output/profile_runs/mini_internet/20260305_202033/validation/summary.json`
- `real_topology_rr`（K3s 多节点，`SEED_TOPOLOGY_SIZE=214`）：
  - 结果：PASS（`expected_nodes=214`, `nodes_used=3`, `bgp_passed=true`）
  - RunID：`output/profile_runs/real_topology_rr/20260305_202612`
  - 汇总：`output/profile_runs/real_topology_rr/20260305_202612/validation/summary.json`

---

## 1. 入口与“在哪里找”

### 1.1 最重要的统一入口（不依赖 AI）

所有 profile（含 `mini_internet` / `real_topology_rr`）统一入口：

```bash
cd <repo_root>
source scripts/env_seedemu.sh
scripts/seed_k8s_profile_runner.sh <profile_id> <action>
```

- 入口脚本：`scripts/seed_k8s_profile_runner.sh`
- profiles 定义：`configs/seed_k8s_profiles.yaml`
- action：`doctor|start|verify|observe|all|triage|report`

### 1.2 两个关键 profile 的落点

- mini internet（多节点强验证）：`examples/kubernetes/k8s_mini_internet.py`
- real topology（RR + 外部数据集）：`examples/kubernetes/k8s_real_topology_rr.py`

### 1.3 多节点强验证脚本（证据落盘）

- mini internet（严格三节点/多节点校验）：`scripts/validate_k3s_mini_internet_multinode.sh`
- real topology（RR，多节点校验）：`scripts/validate_k3s_real_topology_multinode.sh`

### 1.4 快速状态入口（跑之前先看）

```bash
cd <repo_root>
scripts/seed_lab_entry_status.sh
```

它会给出 kubeconfig、节点 Ready、默认 profile/namespace 等快照，并把证据写到：

- `output/assistant_entry/latest/summary.json`

---

## 2. 环境现状（KVM + K3s 三节点）

> 这部分是“我们定位到的现状”，用于复现时对齐。

- K3s 三节点（KVM）：
  - `seed-k3s-master` / `seed-k3s-worker1` / `seed-k3s-worker2`
  - IP：`192.168.122.110/111/112`
- kubeconfig（仓库产物）：`output/kubeconfigs/seedemu-k3s.yaml`
- 默认路由网卡（节点内）：`ens2`（脚本会通过 SSH 自动探测并写入 `SEED_CNI_MASTER_INTERFACE`）
- 容量（当前小规格，仅建议先跑 214 级别）：
  - master/worker1/worker2：约 `4+2+2 CPU / 6+4+4Gi`
- CNI 建议：
  - K3s 多节点真实二层：`SEED_CNI_TYPE=macvlan`（需要 `SEED_CNI_MASTER_INTERFACE=ens2`）
- 受限网络提示（Docker Hub 不可用时必看）：
  - `scripts/setup_k3s_cluster.sh` 默认写入 `/etc/rancher/k3s/registries.yaml`：把 `docker.io` 拉取指向 `SEED_DOCKER_IO_MIRROR_ENDPOINT`（默认 `https://docker.m.daocloud.io`）
  - Multus 的 hostPath（K3s 的 CNI conf/bin 目录）会被安装脚本与验证脚本自动修正（避免 `cannot find valid master CNI config`）

---

## 3. 历史：外部目录的大规模 Docker Compose 运行（经验来源）

> 这条链路发生在外部目录 `~/lxl_topology/autocoder_test`，它是“真实拓扑数据集 + 大规模容器运行”的原始来源与性能经验总结。

### 3.1 关键脚本/数据（外部目录）

- 拓扑生成脚本（外部）：`~/lxl_topology/autocoder_test/RR_214_example.py`
- 大规模运行记录（外部）：`~/lxl_topology/autocoder_test/deployment_record/`

### 3.2 运行结果摘要（来自当时日志）

- 部署日期：`2026-03-05`
- Docker Compose 服务数：`1899`
- 运行中容器：`1898`
- 已退出容器：`1`（`seedemu_internet_map`）
- 网络数量：`1877`
- 总耗时：约 `1 小时 45 分钟`

时间线（来自当时部署记录，时间以记录为准）：

| 时间 | 事件 |
|---|---|
| `10:30` | 开始部署 |
| `10:30:15` | `docker compose down` 清理旧容器 |
| `10:30:25` | 创建网络（1000+，约 10 分钟） |
| `10:40` | 创建所有容器（1899） |
| `10:45` | 分批启动（每批 100，间隔 10 秒） |
| `12:15` | 最终状态：1898 Running / 1 Exited |

当时常用命令（用于排障/复现）：

```bash
# 数量/状态
docker ps --format "{{.Names}}\t{{.Status}}" | wc -l
docker ps -a --filter 'status=exited' --format '{{.Names}}'

# 分批启动（解决 systemd/cgroup 超时）
docker ps -a --filter "status=created" --format "{{.Names}}" \
  | head -100 \
  | xargs -I {} docker start {}

# 进入/查日志
docker logs <container>
docker exec -it <container> bash
```

### 3.3 当时的关键问题与对策（用于迁移到 K8s 的设计参考）

1. systemd cgroup 超时（大量容器并发启动触发）
   - 对策：分批启动（每批 100，间隔 10 秒）
2. 构建超时（并行 build 过大）
   - 对策：分批构建 + 缓存预热

> K8s 迁移后：启动自愈交给 Deployment；构建阶段我们通过 `build_images.sh` 增加可控并行度来替代“手写批处理脚本”。

---

## 4. 本仓库迁移：Real Topology RR（K3s 多节点）

### 4.1 RR iBGP 支持（本仓库代码变更点）

- Router 标记 RR：
  - `seedemu/core/Node.py`：`Router.makeRouteReflector()` / `Router.isRouteReflector()`
- iBGP 渲染逻辑（向后兼容）：
  - `seedemu/layers/Ibgp.py`
  - 规则：
    - AS 内无 RR：保持 **full-mesh iBGP**
    - AS 内有 RR：
      - RR 之间 full-mesh
      - client 仅与 RR 建立 iBGP
      - RR->client 的 BIRD BGP 协议块包含 `rr client;`

### 4.2 Real Topology K8s 示例（外部数据集、可配置）

示例脚本：`examples/kubernetes/k8s_real_topology_rr.py`

数据文件**不入库**，通过 env 指定：

| env | 默认值 | 说明 |
|---|---|---|
| `SEED_REAL_TOPOLOGY_DIR` | `~/lxl_topology/autocoder_test` | 外部数据目录 |
| `SEED_TOPOLOGY_SIZE` | `214` | 先跑 214；大演示用 1897 |
| `SEED_TOPOLOGY_FILE` | `${DIR}/real_topology_${SIZE}.txt` | 可覆盖 |
| `SEED_ASSIGNMENT_FILE` | `${DIR}/assignment.pkl` | 可覆盖 |

**缺文件会 fail-fast**（明确报错 + 提示需要设置哪些 env）。

Internet Map 默认关闭（避免额外工作负载影响 demo）：

- 打开方式：`SEED_ENABLE_INTERNET_MAP=true`

---

## 5. 一键复现（不依赖 AI）

> 下面命令是“最短路径”。执行前先 `source scripts/env_seedemu.sh` 固定 `REPO_ROOT/PYTHONPATH`。

### 5.1 mini_internet（多节点强验证）

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_EXPERIMENT_PROFILE=mini_internet \
scripts/seed_k8s_profile_runner.sh mini_internet all
```

成功证据（跑完必看）：

- `output/profile_runs/mini_internet/latest/validation/summary.json`
- `output/profile_runs/mini_internet/latest/validation/placement.tsv`

### 5.2 real_topology_rr（K3s 多节点，默认 214）

说明：

- 只支持自动分布：`SEED_PLACEMENT_MODE=auto`（脚本会对 `strict3` fail-fast）
- 数据文件缺失会 fail-fast（不会静默 fallback）

```bash
cd <repo_root>
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

SEED_EXPERIMENT_PROFILE=real_topology_rr \
SEED_REAL_TOPOLOGY_DIR="$HOME/lxl_topology/autocoder_test" \
SEED_TOPOLOGY_SIZE=214 \
scripts/seed_k8s_profile_runner.sh real_topology_rr all
```

成功证据：

- `output/profile_runs/real_topology_rr/latest/validation/summary.json`
- `output/profile_runs/real_topology_rr/latest/validation/placement.tsv`
- `output/profile_runs/real_topology_rr/latest/validation/bird_sample.txt`

### 5.3 构建并行度控制（大规模 build 必懂）

`KubernetesCompiler` 生成的 `build_images.sh` 支持：

- `SEED_BUILD_PARALLELISM`（默认 `1`，行为不变）
- `SEED_DOCKER_BUILDKIT`（默认 `0`，可改 `1`）

示例（谨慎使用并行，先从 2/4 起）：

```bash
SEED_BUILD_PARALLELISM=4 SEED_DOCKER_BUILDKIT=0 \
scripts/seed_k8s_profile_runner.sh real_topology_rr start
```

> K3s 多节点验证脚本会在 master 上远程执行 `build_images.sh`，并透传这两个 env。

---

## 6. 运行模式解释（让 docker-compose 用户一眼能懂）

### 6.1 Docker Compose 模式（历史）

- 产物：`docker-compose.yml`
- 运行：`docker compose up -d`
- 人工介入点：分批 `docker start`（避免 systemd/cgroup 超时）

### 6.2 Kubernetes/K3s 模式（本仓库）

- 产物：`k8s.yaml` + `build_images.sh`
- 运行模型：
  1. compile（生成清单 + build 脚本）
  2. build（build + push 到 registry）
  3. deploy（`kubectl apply`，Deployment 管理生命周期）
  4. verify（pods/placement/BGP 证据化）
- 自愈：Deployment 原生保证（无需“手动重启容器”）

---

## 7. 人工检查（最常用，不依赖脚本）

```bash
export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
export NS="${SEED_NAMESPACE}"

kubectl -n "${NS}" get pods -o wide
kubectl -n "${NS}" get deploy -o wide

# 找一个路由器 pod（seedemu.io/name 以 r 开头）
kubectl -n "${NS}" get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.metadata.labels.seedemu\.io/name}{"\n"}{end}' | head

# 进容器/看 BGP
kubectl -n "${NS}" exec -it <pod> -- bash
birdc show protocols
birdc show route count
```

---

## 8. 证据目录（出问题时第一时间看这里）

profile runner 的核心证据目录：

- `output/profile_runs/<profile>/latest/validation/summary.json`

mini_internet 常见证据：

- `output/profile_runs/mini_internet/latest/validation/bird_router151.txt`
- `output/profile_runs/mini_internet/latest/validation/ping_150_to_151.txt`

real_topology_rr 常见证据：

- `output/profile_runs/real_topology_rr/latest/validation/bird_sample.txt`
- `output/profile_runs/real_topology_rr/latest/validation/pods_wide.txt`

---

## 9. 跑的时候如何监督（最小监控闭环）

> 目标：不需要盯着 AI 输出，也不需要猜；只看“证据文件 + kubectl”就能判断跑到哪一步、卡在哪里。

### 9.1 最短的监督入口（推荐）

1) 看整体环境快照（KVM/K3s/kubeconfig/profile/namespace）：

```bash
cd <repo_root>
scripts/seed_lab_entry_status.sh
cat output/assistant_entry/latest/summary.json
```

（跑的时候）看当前动作的实时日志：

```bash
tail -f output/profile_runs/<profile>/latest/runner.log
```

2) 只做体检（不部署）：

```bash
scripts/seed_k8s_profile_runner.sh <profile> doctor
cat output/profile_runs/<profile>/latest/runner_summary.json
cat output/profile_runs/<profile>/latest/next_actions.json
```

如果 `doctor/preflight` 卡住或失败，优先看两类证据（能直接看到根因）：

- `output/profile_runs/<profile>/latest/validation/kube_system_pods.txt`
- `output/profile_runs/<profile>/latest/validation/kube_system_events_tail.txt`

常见根因（尤其是受限网络环境）：`FailedCreatePodSandBox`，原因是节点无法拉取 `rancher/mirrored-pause:3.6`（Docker Hub 超时），会导致 `kube-system` 的所有 Pod 都卡在 `ContainerCreating/Init`，进而 Multus 永远不 Ready。

最小修复建议：

- 直接重跑 `scripts/setup_k3s_cluster.sh`（会写入 `docker.io` mirror，并自动修正 Multus 的 hostPath），然后再跑一次 `doctor`。

3) 真正跑起来（start / all），并在失败时只看证据文件：

```bash
scripts/seed_k8s_profile_runner.sh <profile> all
cat output/profile_runs/<profile>/latest/validation/summary.json
cat output/profile_runs/<profile>/latest/validation/diagnostics.json
cat output/profile_runs/<profile>/latest/validation/next_actions.json
```

### 9.2 kubectl 监督（docker-compose 用户对照）

- `docker compose ps` -> `kubectl -n "$NS" get pods -o wide`
- `docker compose logs` -> `kubectl -n "$NS" logs <pod> --tail=200`
- `docker compose exec` -> `kubectl -n "$NS" exec -it <pod> -- bash`

最常用的一组：

```bash
export NS="${SEED_NAMESPACE}"
kubectl -n "$NS" get pods -o wide
kubectl -n "$NS" get deploy -o wide
kubectl -n "$NS" get events --sort-by=.lastTimestamp | tail -n 40
```

### 9.3 强验证监督点（Real Topology RR）

验证脚本会固化三类证据（跑完必看）：

- **数量对齐**：`counts.json`（expected vs deployments/running_pods）
- **多节点分布**：`placement.tsv`（至少 `nodes_used>=2`）
- **协议收敛**：`bird_sample.txt`（至少一个 `Established`）

---

## 10. 回归测试（本次实现的自证）

> 记录：`2026-03-05` 已跑通以下测试。

```bash
cd <repo_root>
python3 -m unittest tests/ibgp_route_reflector_test.py -v
python3 -m unittest tests/kubevirt_compiler_test.py -v
```

---

## 11. 与 opencode 的关系（可选，不是必须）

- opencode 的“指令入口”仍然只是调用本仓库统一入口：
  - `scripts/seed_k8s_profile_runner.sh <profile> <action>`
- 如果不用 AI，直接按第 5 节命令跑即可。

---

## 12. 本仓库在 2026-03-05 落地的改动（可审阅的“对照表”）

> 这一节回答：“我们到底在仓库里改了哪些点/新增了哪些入口？”

- 新增/迁移：`examples/kubernetes/k8s_real_topology_rr.py`（Real Topology RR -> KubernetesCompiler）
- 新增：`scripts/validate_k3s_real_topology_multinode.sh`（real_topology_rr 强验证流水线 + 证据落盘）
- 新增 profile：`configs/seed_k8s_profiles.yaml`（`real_topology_rr`）
- RR 支持：
  - `seedemu/core/Node.py`（Router RR 标记 API）
  - `seedemu/layers/Ibgp.py`（RR iBGP 渲染 + graph）
- build 可控：
  - `seedemu/compiler/Kubernetes.py`（生成的 `build_images.sh` 支持 `SEED_BUILD_PARALLELISM`/`SEED_DOCKER_BUILDKIT`）
  - `scripts/validate_k3s_mini_internet_multinode.sh` / `scripts/validate_k3s_real_topology_multinode.sh`（remote build 透传 env）
- 统一入口与证据：
  - `scripts/seed_k8s_profile_runner.sh`（mini/real 两条链路统一到一个入口）
  - `docs/runbooks/opencode_seed_lab_quickstart.md`（单文档入口：变量、模式、证据、人工检查）
  - `scripts/opencode_seedlab_smoke.sh`（repo/agent 健康检查）
- 清理硬编码路径：
  - `.opencode/**`、`docs/**`、`configs/seed_failure_action_map.yaml`（统一改为 repo-root 相对路径 / `PYTHONPATH=.`）
- 单测新增：`tests/ibgp_route_reflector_test.py`（full-mesh vs RR）

---

## 13. 如何问 AI（opencode 的 seed-lab agent）

> 结论：你可以**直接用自然语言问**（不需要 slash commands）。  
> AI 的输出目标是：**当前状态 + 一条下一步命令 + 证据文件路径**（便于任何人复现与审阅）。

### 13.1 推荐问法（自然语言，最省事）

你可以直接问：

- “现在 `mini_internet` 跑到哪一步了？卡在哪里？”
- “`latest` 为什么失败？给我 `failure_code` 和第一证据文件路径。”
- “下一步只给 1 条命令（最小重试）。”
- “帮我判断 `real_topology_rr` 是否满足验收（数量/多节点分布/BGP）。”

AI 应该优先读取这些证据文件并据此回答（而不是凭感觉）：

1. `output/assistant_entry/latest/summary.json`（环境快照）
2. `output/profile_runs/<profile>/latest/runner_summary.json`（本次 action 状态）
3. `output/profile_runs/<profile>/latest/validation/diagnostics.json`（失败原因/证据/最小重试）
4. `output/profile_runs/<profile>/latest/validation/next_actions.json`（下一步动作）
5. `output/profile_runs/<profile>/latest/validation/summary.json`（验收汇总）

回答格式建议固定为 3 行（越短越好）：

1) `status: PASS|FAIL, stage: <stage>, profile: <profile>`  
2) `evidence: <file>`  
3) `next: <one command>`

### 13.2 如果你喜欢 slash commands（可选）

```bash
cd <repo_root>
opencode
```

在 opencode 里常用的命令（只是“快捷入口”，本质仍是调用仓库脚本）：

1) `/seed-lab-home`（生成环境快照 + 推荐下一步）
2) `/seed-lab-doctor`（只体检，不部署）
3) `/seed-lab-start`（preflight -> compile -> build -> deploy）
4) `/seed-lab-verify`（强校验）
5) `/seed-lab-observe`（采集运行态快照）
6) `/seed-lab-report`（把证据归一化成报告）

如果失败，直接问：

- `/seed-lab-triage`（它会读 artifacts 并给出最小重试命令）
- `/seed-lab-next`（只输出 1 条下一步命令）

### 13.3 让 AI 跑哪个 profile（只改一个变量）

在启动 opencode 前（或同一 shell session）设置：

```bash
export SEED_EXPERIMENT_PROFILE=mini_internet
# 或：
export SEED_EXPERIMENT_PROFILE=real_topology_rr
```

Real Topology RR 还需要外部数据集：

```bash
export SEED_REAL_TOPOLOGY_DIR="$HOME/lxl_topology/autocoder_test"
export SEED_TOPOLOGY_SIZE=214
```

### 13.4 破坏性动作的确认短语（必须）

任何需要删除 namespace / 重建集群的动作，AI 会要求你输入：

`CONFIRM_SEED_DESTRUCTIVE: <target>`

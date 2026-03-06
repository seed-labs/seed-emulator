# SEED Lab 证据优先操作指南（给不熟 K8s 的同学）

最后更新：`2026-03-06`

这份文档是给“知道我们在做什么，但不想先学一大堆 Kubernetes 概念”的同学准备的。

目标只有 4 个：

1. 看懂当前环境是什么。
2. 知道小规模 `mini_internet` 怎么跑、怎么验收。
3. 知道历史大规模 Docker Compose 是怎么跑的，以及现在迁移到了哪里。
4. 知道以后不懂时，如何让 opencode/AI 基于**真实证据**回答，而不是空谈。

如果你只想记住一个入口，请记住：

```bash
cd /home/seed/seed-emulator-k8s
source scripts/env_seedemu.sh
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

其中：

- `<profile>` 目前最重要的是 `mini_internet` 和 `real_topology_rr`
- `<action>` 最常用的是 `doctor`、`all`、`report`

---

## 1. 先看现在这套东西到底是什么

### 1.1 当前环境，不要猜，按这个理解

当前我们维护的是两条线：

1. **历史线：Docker Compose 大规模网络**
   - 外部目录：`~/lxl_topology/autocoder_test`
   - 核心脚本：`~/lxl_topology/autocoder_test/RR_214_example.py`
   - 核心特征：一次生成大量服务，然后用 `docker compose` 和分批 `docker start` 跑起来

2. **当前线：K3s/K8s 多节点运行体系**
   - 仓库目录：`/home/seed/seed-emulator-k8s`
   - 统一入口：`scripts/seed_k8s_profile_runner.sh`
   - 核心特征：用 profile + validate + report 的方式把运行、验证、日志、证据都统一起来

### 1.2 当前 K3s 集群是什么

当前仓库内已经定位好的 K3s 集群是：

- `seed-k3s-master`
- `seed-k3s-worker1`
- `seed-k3s-worker2`

对应 kubeconfig：

- `output/kubeconfigs/seedemu-k3s.yaml`

当前三节点默认真实网卡：

- `ens2`

所以凡是多节点真实二层相关的运行，优先按下面理解：

- `SEED_CNI_TYPE=macvlan`
- `SEED_CNI_MASTER_INTERFACE=ens2`

### 1.3 先看状态，而不是直接开跑

第一条建议命令：

```bash
cd /home/seed/seed-emulator-k8s
scripts/seed_lab_entry_status.sh
cat output/assistant_entry/latest/summary.json
```

这一步的意义：

- 确认 kubeconfig 是否存在
- 确认 K3s 节点是否 Ready
- 确认当前默认 profile / namespace
- 给出当前环境快照

如果连这一步都看不懂，就先不要直接跑 `all`。

---

## 2. 小规模：`mini_internet` 怎么跑、怎么测

`mini_internet` 是我们现在的**小规模标准回归例子**。

它的意义不是“规模小”，而是：

- 它最适合快速验证链路完整性
- 它有比较强的自动化验收
- 它最适合不会 K8s 的同学先熟悉“怎么跑、怎么判断对不对”

### 2.1 一键跑法

```bash
cd /home/seed/seed-emulator-k8s
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
SEED_EXPERIMENT_PROFILE=mini_internet \
scripts/seed_k8s_profile_runner.sh mini_internet all
```

### 2.2 它内部到底做了什么

这条命令并不是“神秘黑盒”，它本质上做的是：

1. `doctor/preflight`
   - 看 kubeconfig
   - 看 K3s 节点是否 Ready
   - 看 Multus/CNI/registry 是否正常

2. `compile`
   - 用 `examples/kubernetes/k8s_mini_internet.py` 生成 K8s 清单

3. `build`
   - 生成并执行 `build_images.sh`
   - 构建并推送所需镜像

4. `deploy`
   - `kubectl apply`
   - 等待 deployment 可用

5. `verify`
   - 看调度分布
   - 看 BGP
   - 看跨 AS 连通性
   - 看恢复/自愈

6. `observe/report`
   - 把证据整理成可读报告

### 2.3 它跑完以后，应该看哪里

先看总结果：

- `output/profile_runs/mini_internet/latest/validation/summary.json`

当前我们已有一份通过的记录：

- `output/profile_runs/mini_internet/20260305_202033/validation/summary.json`

重点字段：

- `placement_passed`
- `strict3_passed`
- `bgp_passed`
- `connectivity_passed`
- `recovery_passed`

### 2.4 学长只看这几个证据就够了

#### A. 调度是否分布到了多节点

- `output/profile_runs/mini_internet/latest/validation/placement.tsv`

#### B. 路由/BGP 是否起来了

- `output/profile_runs/mini_internet/latest/validation/bird_router151.txt`
- `output/profile_runs/mini_internet/latest/validation/bird_ix100.txt`

#### C. 业务连通性是否通了

- `output/profile_runs/mini_internet/latest/validation/ping_150_to_151.txt`

#### D. 自愈是否通过

- `output/profile_runs/mini_internet/latest/validation/recovery_check.json`

### 2.5 跑的时候怎么盯

最实在的方式：

```bash
tail -f output/profile_runs/mini_internet/latest/runner.log
```

和：

```bash
export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
export NS=seedemu-k3s-mini-mn

kubectl -n "$NS" get pods -o wide
kubectl -n "$NS" get deploy -o wide
kubectl -n "$NS" get events --sort-by=.lastTimestamp | tail -n 40
```

### 2.6 如果想人工进去看

```bash
export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
export NS=seedemu-k3s-mini-mn

kubectl -n "$NS" get pods -o wide
kubectl -n "$NS" exec -it <router-pod> -- bash
birdc show protocols
birdc show route count
```

你可以把它理解为：

- `docker compose ps` -> `kubectl get pods -o wide`
- `docker compose exec` -> `kubectl exec -it`
- `docker compose logs` -> `kubectl logs`

---

## 3. 历史大规模：之前 Docker Compose 是怎么跑的

这部分不是废弃物，而是现在大规模迁移的来源。

### 3.1 外部目录在哪里

历史大规模目录：

- `~/lxl_topology/autocoder_test`

关键文件：

- 拓扑脚本：`~/lxl_topology/autocoder_test/RR_214_example.py`
- 部署记录：`~/lxl_topology/autocoder_test/deployment_record/README.md`
- 部署总结：`~/lxl_topology/autocoder_test/deployment_record/SUMMARY.md`
- 详细日志：`~/lxl_topology/autocoder_test/deployment_record/logs/deployment.log`

### 3.2 它当时是怎么运行的

核心流程是：

1. 用 `RR_214_example.py` 生成大量服务
2. 用 `docker compose up -d` 创建网络和容器
3. 因为规模太大，再用“分批启动”的方法把 created 容器逐批拉起来

典型命令：

```bash
cd ~/lxl_topology/autocoder_test

python RR_214_example.py
docker compose -f ./output/docker-compose.yml up -d

for i in {1..20}; do
    docker ps -a --filter "status=created" --format "{{.Names}}" | head -100 | xargs -I {} docker start {}
    sleep 10
done
```

### 3.3 它跑出来的结果是什么

根据已有日志：

- 服务数：`1899`
- 运行中容器：`1898`
- 已退出：`1`
- 网络数：`1877`
- 总耗时：约 `1 小时 45 分钟`

这些都写在：

- `~/lxl_topology/autocoder_test/deployment_record/logs/deployment.log`
- `~/lxl_topology/autocoder_test/deployment_record/SUMMARY.md`

### 3.4 它最大的问题是什么

主要有三个：

1. 同时启动太多容器，systemd/cgroup 超时
2. 并行构建过大，build 超时
3. 运行状态和验证状态不统一，很多时候只能靠人工看终端

这正是后来迁移到 K3s 体系的主要原因。

---

## 4. 现在大规模改到哪里了、怎么运行

当前仓库里，大规模真实拓扑的 K3s 入口是：

- 示例脚本：`examples/kubernetes/k8s_real_topology_rr.py`
- profile：`configs/seed_k8s_profiles.yaml`
- 验证脚本：`scripts/validate_k3s_real_topology_multinode.sh`
- 统一入口：`scripts/seed_k8s_profile_runner.sh`

### 4.1 和历史 Docker Compose 的对应关系

历史：

- `RR_214_example.py` -> Docker Compose

现在：

- `k8s_real_topology_rr.py` -> KubernetesCompiler -> `k8s.yaml` + `build_images.sh`

你可以把它理解成：

- 以前是“先生成 compose，再手工 build/up/start”
- 现在是“先生成 K8s 清单，再统一走 runner/validate”

### 4.2 现在改动的核心位置

#### A. 真实拓扑迁移

- `examples/kubernetes/k8s_real_topology_rr.py`

职责：

- 从外部目录读取数据集
- 生成 K8s 版本的真实拓扑
- 支持 RR（route reflector）语义

#### B. 真实拓扑的自动化验证

- `scripts/validate_k3s_real_topology_multinode.sh`

职责：

- preflight
- compile
- remote build
- deploy
- verify

#### C. 统一 profile 入口

- `scripts/seed_k8s_profile_runner.sh`

职责：

- 根据 profile 选择 validate 脚本
- 统一生成 `runner.log` / `summary.json` / `report`

#### D. 大规模 build 的能力提升

- `seedemu/compiler/Kubernetes.py`

职责：

- 生成更可控的 `build_images.sh`
- 支持 `SEED_BUILD_PARALLELISM`
- 支持 `SEED_DOCKER_BUILDKIT`

#### E. RR 内核支持

- `seedemu/core/Node.py`
- `seedemu/layers/Ibgp.py`
- `tests/ibgp_route_reflector_test.py`

职责：

- 让 route reflector 成为真正的 core 能力，而不是示例层 hack

### 4.3 现在的大规模 K3s 怎么跑

当前建议先跑 `214` 规模，因为三节点资源只够这个级别稳定演示。

```bash
cd /home/seed/seed-emulator-k8s
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda activate seedemu-k8s-py310
source scripts/env_seedemu.sh

export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
export SEED_REAL_TOPOLOGY_DIR="$HOME/lxl_topology/autocoder_test"
export SEED_TOPOLOGY_SIZE=214

scripts/seed_k8s_profile_runner.sh real_topology_rr all
```

### 4.4 跑完以后看哪里

总结果：

- `output/profile_runs/real_topology_rr/latest/validation/summary.json`

当前已通过的一次记录：

- `output/profile_runs/real_topology_rr/20260305_202612/validation/summary.json`

关键字段：

- `expected_nodes=214`
- `nodes_used=3`
- `bgp_passed=true`

### 4.5 学长只看这几个证据就能判断是否成功

#### A. 数量对不对

- `output/profile_runs/real_topology_rr/latest/validation/counts.json`

#### B. pod 是否分布到了多个节点

- `output/profile_runs/real_topology_rr/latest/validation/placement.tsv`

#### C. 所有 workload 是否都起来了

- `output/profile_runs/real_topology_rr/latest/validation/pods_wide.txt`
- `output/profile_runs/real_topology_rr/latest/validation/deployments_wide.txt`

#### D. BGP 至少有没有 Established

- `output/profile_runs/real_topology_rr/latest/validation/bird_sample.txt`

#### E. 总报告

- `output/profile_runs/real_topology_rr/latest/report/report.json`
- `output/profile_runs/real_topology_rr/latest/report/report.md`

### 4.6 跑的时候怎么盯

最直接：

```bash
tail -f output/profile_runs/real_topology_rr/latest/runner.log
```

和：

```bash
export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
export NS=seedemu-k3s-real-topo

kubectl -n "$NS" get pods -o wide
kubectl -n "$NS" get deploy -o wide
kubectl -n "$NS" get events --sort-by=.lastTimestamp | tail -n 40
```

---

## 5. 以后其他例子怎么做，不要乱加

后续如果要加新的 K3s 例子，建议按下面顺序做。

### 5.1 先决定它是“小回归”还是“大演示”

如果目标是高频验证：

- 参考 `mini_internet`

如果目标是真实拓扑/大规模演示：

- 参考 `real_topology_rr`

### 5.2 新例子至少要落这 4 个点

#### A. 示例脚本

- 放到 `examples/kubernetes/`

#### B. profile

- 在 `configs/seed_k8s_profiles.yaml` 注册

#### C. 验证脚本

- 简单例子可走 generic
- 复杂例子需要新建 `scripts/validate_k3s_<name>_multinode.sh`

#### D. 文档

- 至少要补到 `docs/runbooks/opencode_seed_lab_quickstart.md`
- 如果是结构性改动，要补到 `docs/k3s_runtime_architecture.md`

### 5.3 不要做的事情

1. 不要只加 Python 示例，不加 profile/validate/doc
2. 不要把运行逻辑塞进 prompt，让离开 AI 就不会跑
3. 不要让大规模例子成为默认 smoke
4. 不要只看终端，不落证据文件

---

## 6. 如果不懂 K8s，怎么问 opencode/AI

这一部分最重要的原则是：

> 让 AI 读证据，再回答。

而不是问一个抽象问题，让它凭印象解释。

### 6.1 最推荐的问法：自然语言 + 证据优先

先进入仓库：

```bash
cd /home/seed/seed-emulator-k8s
opencode
```

然后直接问：

- “现在 `mini_internet` 跑到哪一步了？只告诉我状态、证据文件、下一步命令。”
- “`real_topology_rr` 现在是不是已经满足验收？给我 counts、placement、bird 的证据路径。”
- “我不懂 K8s，你不要讲概念，直接告诉我我该看哪个文件、执行哪条命令。”
- “这个失败是 kubeconfig 问题、registry 问题，还是 BGP 问题？给证据。”

### 6.2 要求 AI 优先看的证据文件

#### 环境入口

- `output/assistant_entry/latest/summary.json`

#### 某次运行的主状态

- `output/profile_runs/<profile>/latest/runner_summary.json`

#### 失败原因与下一步

- `output/profile_runs/<profile>/latest/validation/diagnostics.json`
- `output/profile_runs/<profile>/latest/validation/next_actions.json`

#### 最终验收

- `output/profile_runs/<profile>/latest/validation/summary.json`

### 6.3 如果学长不会写好 prompt，就照抄这句

你可以直接对 AI 说：

```text
不要泛泛解释。请先读 output/assistant_entry/latest/summary.json 和 output/profile_runs/<profile>/latest/validation/summary.json、diagnostics.json，然后只用三行回答我：
1) status/stage
2) evidence file
3) next one command
```

### 6.4 如果喜欢 slash commands，也可以这么用

常用顺序：

1. `/seed-lab-home`
2. `/seed-lab-doctor`
3. `/seed-lab-start`
4. `/seed-lab-verify`
5. `/seed-lab-report`
6. `/seed-lab-triage`

但如果你不熟 K8s，其实**自然语言更适合**，因为你只需要抓住“证据 + 下一步命令”。

---

## 7. 给不熟 K8s 的同学，一个最小判断标准

如果你只想知道“现在到底成没成”，那就按下面判断。

### 7.1 `mini_internet` 成功标准

看：

- `output/profile_runs/mini_internet/latest/validation/summary.json`

至少要同时满足：

- `placement_passed=true`
- `bgp_passed=true`
- `connectivity_passed=true`
- `recovery_passed=true`

### 7.2 `real_topology_rr` 成功标准

看：

- `output/profile_runs/real_topology_rr/latest/validation/summary.json`

至少要同时满足：

- `expected_nodes` 正确
- `nodes_used >= 2`（当前实际是 `3`）
- `bgp_passed=true`

### 7.3 如果失败，第一反应不要乱试

先看：

- `diagnostics.json`
- `next_actions.json`

因为里面已经给了：

- `failure_code`
- `first_evidence_file`
- `minimal_retry_command`
- `fallback_command`

这比自己瞎猜“是不是 K8s 坏了”要可靠得多。

---

## 8. 最后给学长的一页纸结论

如果你要把现在这套东西讲给别人听，可以直接这么说：

1. 小规模验证看 `mini_internet`
   - 它是标准回归例子
   - 一键命令：`scripts/seed_k8s_profile_runner.sh mini_internet all`
   - 结果看 `output/profile_runs/mini_internet/latest/validation/summary.json`

2. 历史大规模真实拓扑以前在外部目录跑 Docker Compose
   - 目录：`~/lxl_topology/autocoder_test`
   - 日志：`~/lxl_topology/autocoder_test/deployment_record/logs/deployment.log`

3. 现在大规模真实拓扑已经迁到仓库里走 K3s/K8s
   - 示例：`examples/kubernetes/k8s_real_topology_rr.py`
   - 入口：`scripts/seed_k8s_profile_runner.sh real_topology_rr all`
   - 当前建议先跑 `214`

4. 如果不懂 K8s，不要先学术语
   - 先看 `summary.json`
   - 再看 `diagnostics.json`
   - 再让 opencode/AI 基于证据回答“状态、证据、下一步命令”

5. 以后加新例子，不是只写 Python 文件
   - 必须同时补 profile、validate、report、文档

---

## 9. 相关文档（按用途看）

### 快速入口

- `docs/runbooks/opencode_seed_lab_quickstart.md`

### 带时间戳的迁移和运行记录

- `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`

### 长期架构与维护文档

- `docs/k3s_runtime_architecture.md`

### 当前仓库的 Kubernetes 示例说明

- `examples/kubernetes/README.md`


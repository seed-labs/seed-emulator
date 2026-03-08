# SEED Emulator 多仓库源码差异说明（给准备自己改源码的同学）

最后更新：`2026-03-08`

这份文档只回答一个问题：

> 现在机器上有多个 `seed-emulator` 目录，到底哪个是当前 K3s 运行链路真正用到的？它们彼此差在哪？如果学长要自己改，应该改哪里？

---

## 1. 先说结论

当前真正用于 **K3s/K8s 多节点运行** 的仓库是：

- `/home/seed/seed-emulator-k8s`

另外两个目录更像历史版本 / 个人改动分支：

- `/home/seed/seed-emulator`
- `/home/seed/seed-emulator1211`

如果学长要改 **当前 K3s 跑法**，应该改：

- `/home/seed/seed-emulator-k8s/seedemu/...`
- `/home/seed/seed-emulator-k8s/scripts/...`
- `/home/seed/seed-emulator-k8s/examples/...`

如果学长要回看你以前的“魔改版本”思路，优先看：

- `/home/seed/seed-emulator`

---

## 2. 三个目录分别是什么

| 目录 | 当前状态 | `bird` 自动启动 | RR(iBGP route reflector) | K3s profile/validate 流程 | 建议用途 |
|---|---|---|---|---|---|
| `/home/seed/seed-emulator-k8s` | 当前主线 | **开** | **有（baseline + scale knobs）** | **有** | 当前开发、编译、K3s 复现 |
| `/home/seed/seed-emulator` | 历史深改版 | **关（被注释）** | **有（你自己的 cluster 版）** | 无当前这套 | 回看旧逻辑、迁移思路 |
| `/home/seed/seed-emulator1211` | 更老旧快照 | **关（被注释）** | 基本无 | 无 | 只做参考，不建议作为当前修改基线 |

这三个目录当前看到的 Git 头分别是：

- `/home/seed/seed-emulator-k8s`：`b1268692`
- `/home/seed/seed-emulator`：`c039e7b1`
- `/home/seed/seed-emulator1211`：`059f5ee4`

其中 `/home/seed/seed-emulator` 当前工作树还是脏的（有未提交改动），更说明它像“实验中目录”，不是现在这套 K3s 标准运行入口。

---

## 3. 为什么说当前真正跑的是 `seed-emulator-k8s`

证据不是口头说法，而是当前脚本链路明确绑定到这个 repo：

1. `scripts/env_seedemu.sh:7` 会把 `REPO_ROOT` 固定为 **当前仓库根目录**。
2. `scripts/env_seedemu.sh:15` 会把 `PYTHONPATH` 设为 `${REPO_ROOT}`。
3. `scripts/seed_k8s_profile_runner.sh:367` 编译 profile 时强制使用 `PYTHONPATH="${REPO_ROOT}"`。
4. `scripts/validate_k3s_real_topology_multinode.sh:652` 编译 real topology 时也强制使用 `PYTHONPATH="${REPO_ROOT}"`。
5. 实际 Python 导入结果显示 `seedemu` 来自：`/home/seed/seed-emulator-k8s/seedemu/__init__.py`。

所以：

- 现在 `mini_internet` 的 K3s 运行链路，用的是 `seed-emulator-k8s`
- 现在 `real_topology_rr` 的 K3s 运行链路，用的也是 `seed-emulator-k8s`
- 不是 `/home/seed/seed-emulator`
- 也不是 `/home/seed/seed-emulator1211`

---

## 4. 关键差异一：`bird` 自动启动到底在哪个版本开着

### 4.1 当前仓库：`seed-emulator-k8s`

当前 K3s 路径里，路由器和 RS 都会在启动脚本里自动拉起 `bird`：

- `seedemu/layers/Routing.py:92`
- `seedemu/layers/Routing.py:93`
- `seedemu/layers/Routing.py:120`
- `seedemu/layers/Routing.py:121`

关键代码语义就是：

- 先创建 `/run/bird`
- 再执行 `bird -d`

这些 start commands 会被编译进容器 `/start.sh`，而 K8s Pod 入口就是 `/start.sh`：

- `seedemu/compiler/Docker.py:30`
- `seedemu/compiler/Docker.py:1012`
- `seedemu/compiler/Docker.py:1018`
- `seedemu/compiler/Docker.py:1042`
- `seedemu/compiler/Kubernetes.py:533`

因此当前仓库的实际行为是：

- `bird` 由编译产物自动拉起
- validate 脚本只负责用 `birdc` 检查，不负责启动 `bird`

### 4.2 旧目录：`/home/seed/seed-emulator`

这里 `bird` 自动启动被注释掉了：

- `/home/seed/seed-emulator/seedemu/layers/Routing.py:118`
- `/home/seed/seed-emulator/seedemu/layers/Routing.py:119`
- `/home/seed/seed-emulator/seedemu/layers/Routing.py:147`

也就是说，如果当年你是基于这个目录编译镜像，那么“默认不启动 `bird`”这个记忆是成立的。

### 4.3 更老目录：`/home/seed/seed-emulator1211`

这里同样把 `bird -d` 注释掉了：

- `/home/seed/seed-emulator1211/seedemu/layers/Routing.py:92`
- `/home/seed/seed-emulator1211/seedemu/layers/Routing.py:93`
- `/home/seed/seed-emulator1211/seedemu/layers/Routing.py:120`
- `/home/seed/seed-emulator1211/seedemu/layers/Routing.py:121`

所以你看到的现象并不矛盾：

- 你以前改过的老目录，确实可能默认不启动 `bird`
- 现在 K3s 在跑的这套当前仓库，默认是会启动 `bird` 的

---

## 5. 关键差异二：RR 支持的风格不一样

### 5.1 当前仓库：统一、最小化 RR API

当前仓库的 RR 能力主要在两个文件：

- `seedemu/core/Node.py:1215`
- `seedemu/core/Node.py:1229`

核心 API 是：

- `Router.makeRouteReflector(True)`
- `Router.isRouteReflector()`

当前实现思路是：

1. 如果某个 AS **没有 RR**，保持原来的 **full-mesh iBGP**。
2. 如果某个 AS **有 RR**：
   - client 只连 RR
   - RR 连所有 client
   - RR 之间 full-mesh
3. 图渲染也按真实 RR 拓扑画，不再一律全连。

并且当前主线又往前走了一步：

- baseline 默认继续使用 `simple` RR 模式
- 学长旧版 cluster 思路被整理成显式 `clustered` 模式
- 通过 `real_topology_rr_scale` profile 才会默认启用

对应实现：

- `seedemu/layers/Ibgp.py:20`
- `seedemu/layers/Ibgp.py:29`
- `seedemu/layers/Ibgp.py:112`
- `seedemu/layers/Ibgp.py:167`

这个版本的特点是：

- API 简单
- 不引入你旧版那套 cluster 管理接口
- 直接适配当前 `real_topology_rr` 示例

### 5.2 旧目录：你自己的 cluster-based RR 设计

`/home/seed/seed-emulator` 里，你以前做的是另一套更强的 RR 设计。

关键点在：

- `/home/seed/seed-emulator/seedemu/core/Node.py:1149`：`makeRouteReflector()`
- `/home/seed/seed-emulator/seedemu/core/Node.py:1153`：`joinBgpCluster()`
- `/home/seed/seed-emulator/seedemu/core/AutonomousSystem.py:98`：`_aggregateBgpClusters()`
- `/home/seed/seed-emulator/seedemu/layers/Ibgp.py:36`
- `/home/seed/seed-emulator/seedemu/layers/Ibgp.py:47`
- `/home/seed/seed-emulator/seedemu/layers/Ibgp.py:133`
- `/home/seed/seed-emulator/seedemu/layers/Ibgp.py:144`

它的特点是：

- 不只是“标记一个 RR”
- 还允许 Router `joinBgpCluster(cluster_id)`
- RR 到 client 的配置里会写 `rr cluster id {clusterId}`
- AS 内 RR 的组织方式由 `_aggregateBgpClusters()` 决定

也就是说：

- 旧目录不是“没有 RR”
- 它其实是“RR 更复杂、更定制”的版本
- 只是这套逻辑没有接到当前统一的 K3s profile / validate 流水线里

### 5.3 更老目录：基本还是传统 full-mesh

`/home/seed/seed-emulator1211` 中：

- `Node.py` 里没有当前这些 RR API
- `Ibgp.py` 基本还是传统 full-mesh 渲染

对应位置：

- `/home/seed/seed-emulator1211/seedemu/layers/Ibgp.py:20`
- `/home/seed/seed-emulator1211/seedemu/layers/Ibgp.py:92`

所以学长如果想找“更早、没改太多”的基线，可以看这个；但不建议直接在它上面继续做当前工作。

---

## 6. 关键差异三：只有当前仓库有完整 K3s 运行体系

当前仓库里，和 K3s 多节点复现直接相关的入口已经统一好了。

### 6.1 小规模 `mini_internet`

统一入口：

- `scripts/seed_k8s_profile_runner.sh`

严格多节点验证：

- `scripts/validate_k3s_mini_internet_multinode.sh`

### 6.2 真实拓扑 `real_topology_rr`

当前新增并接通的入口：

- `configs/seed_k8s_profiles.yaml:24`
- `examples/kubernetes/k8s_real_topology_rr.py`
- `scripts/validate_k3s_real_topology_multinode.sh`

### 6.3 当前仓库里已经有“给不会 K8s 的人”的说明文档

- `docs/runbooks/seed_lab_evidence_first_operator_guide.md`
- `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`
- `docs/k3s_runtime_architecture.md`

而另外两个旧目录里，没有这套统一的：

- profile runner
- validate 脚本
- real topology K3s 示例
- 证据归档路径

所以如果目的是“让别人一眼看懂、能复现、能验收”，应当继续围绕当前仓库维护，而不是回到旧目录。

---

## 7. 学长如果要自己改，最常见是改哪几处

### 7.1 想改 `bird` 是否自动启动

改：

- `seedemu/layers/Routing.py`

看这两类节点：

- `_configure_rs(...)`
- `_configure_bird_router(...)`

### 7.2 想改 RR 标记方式或 RR 会话生成规则

改：

- `seedemu/core/Node.py`
- `seedemu/layers/Ibgp.py`

如果只是想保留当前简单接口：

- 改 `makeRouteReflector()` / `isRouteReflector()`
- 改 `Ibgp.render()` 和 `_doCreateGraphs()`

如果想把你旧版的 cluster 概念迁回当前仓库，再额外参考：

- `/home/seed/seed-emulator/seedemu/core/AutonomousSystem.py`
- `/home/seed/seed-emulator/seedemu/core/Node.py`
- `/home/seed/seed-emulator/seedemu/layers/Ibgp.py`

### 7.3 想改当前 K3s 的编译 / 部署 / 校验链路

看：

- `scripts/seed_k8s_profile_runner.sh`
- `scripts/validate_k3s_mini_internet_multinode.sh`
- `scripts/validate_k3s_real_topology_multinode.sh`
- `configs/seed_k8s_profiles.yaml`
- `examples/kubernetes/k8s_real_topology_rr.py`

### 7.4 想回看历史 Docker Compose 大规模跑法

外部历史目录：

- `~/lxl_topology/autocoder_test`

核心参考：

- `~/lxl_topology/autocoder_test/RR_214_example.py`
- `~/lxl_topology/autocoder_test/deployment_record/README.md`
- `~/lxl_topology/autocoder_test/deployment_record/SUMMARY.md`

---

## 8. 不建议怎么做

下面这些做法最容易把人搞晕：

1. **不要混着改三个目录**。
   - 当前主线只改 `/home/seed/seed-emulator-k8s`

2. **不要一边在旧目录写代码，一边在当前仓库运行脚本**。
   - 这样会出现“以为改生效了，其实运行时没用到”的错觉

3. **不要把历史目录的行为记忆，直接当成当前仓库事实**。
   - 例如“以前 `bird` 不自动启动”在旧目录成立，但在当前仓库不成立

4. **不要修改编译产物目录来代替改源码**。
   - 正确改法应该是改 `seedemu/...` 或 `scripts/...`
   - 然后重新 compile / build / deploy

---

## 9. 推荐的实际工作方式

如果学长现在要继续做当前主线，建议按下面顺序：

### 9.1 先看小规模是否通

```bash
cd /home/seed/seed-emulator-k8s
source scripts/env_seedemu.sh
scripts/seed_k8s_profile_runner.sh mini_internet all
```

### 9.2 再看真实拓扑 `214` 是否通

```bash
cd /home/seed/seed-emulator-k8s
source scripts/env_seedemu.sh
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr all
```

### 9.2.1 想验证大规模实验档，不改主线默认值

```bash
cd /home/seed/seed-emulator-k8s
source scripts/env_seedemu.sh
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

### 9.3 想改核心逻辑时，先改当前仓库，再跑回归

最关键的回归点：

```bash
python3 -m unittest tests/ibgp_route_reflector_test.py -v
python3 -m unittest tests/kubevirt_compiler_test.py -v
```
### 9.4 想借旧思路，但不要直接拿旧目录当运行入口

做法应该是：

1. 去 `/home/seed/seed-emulator` 看你以前怎么做的
2. 把需要的设计迁回 `/home/seed/seed-emulator-k8s`
3. 在当前仓库的测试和 K3s profile 链路里验证

---

## 10. 一句话版给学长

如果只想记住一句话，请记住：

> 现在真正用于 K3s/K8s 多节点复现的是 `/home/seed/seed-emulator-k8s`；`/home/seed/seed-emulator` 是你以前深改过、连 `bird` 自动启动都关掉过的历史分支；`/home/seed/seed-emulator1211` 更老，只适合参考，不适合作为当前主线继续改。

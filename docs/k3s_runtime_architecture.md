# SEED Emulator K3s 运行抽象与维护手册

最后更新：`2026-03-06`

本文不是“快速上手页”，而是给后续开发、测试、维护者的长期文档。它回答四个问题：

1. 本仓库现在怎样抽象 K3s/K8s 运行模式。
2. `mini_internet` 与 `real_topology_rr` 这两个大小例子在抽象层面分别代表什么。
3. 新例子、新 profile、新验证链路应该如何加入，而不破坏现有体系。
4. 后续开发、测试、维护应该遵循什么边界与流程。

相关入口文档：

- 快速入口：`docs/runbooks/opencode_seed_lab_quickstart.md`
- 带时间戳的迁移/复盘记录：`docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`
- 通用 K8s 使用说明：`docs/k8s_usage.md`

---

## 1. 设计目标

当前 K3s/K8s 方案的目标不是“把 Docker Compose 原封不动搬进 K8s”，而是形成一套稳定的多层运行抽象：

- **编译层**：Python 示例脚本只描述拓扑与编译参数，不直接关心部署细节。
- **profile 层**：用 profile 表达“跑什么、默认 namespace/cni/scheduling 是什么、验证期望是什么”。
- **执行层**：统一 runner 负责 `doctor/start/verify/observe/report` 生命周期。
- **验证层**：真实多节点验证脚本负责把“成功/失败”落成证据，而不是靠人看终端。
- **报告层**：把验证产物归一化，产出可供 AI 和人类同时消费的 summary/diagnostics/report。

一句话：

> 示例脚本负责“生成”，profile 负责“命名和默认值”，runner 负责“调度生命周期”，validate 脚本负责“证据化验收”。

---

## 2. 运行抽象总览

### 2.1 四个核心对象

#### A. 示例脚本（compile script）

位置：`examples/kubernetes/*.py`

职责：

- 构建 SEED 拓扑。
- 读取运行时 env。
- 调用 `KubernetesCompiler` 输出 `k8s.yaml` 与 `build_images.sh`。

示例：

- `examples/kubernetes/k8s_mini_internet.py`
- `examples/kubernetes/k8s_real_topology_rr.py`

边界：

- 不直接 `kubectl apply`
- 不直接 `docker build`
- 不直接做 cluster preflight

#### B. Profile

位置：`configs/seed_k8s_profiles.yaml`

职责：

- 定义 profile id。
- 给出默认 namespace / CNI / scheduling。
- 描述 verify mode 和观测产物要求。

当前关键 profile：

- `mini_internet`
- `real_topology_rr`
- `transit_as`
- `mini_internet_viz`
- `hybrid_kubevirt`

#### C. Runner

位置：`scripts/seed_k8s_profile_runner.sh`

职责：

- 统一外部入口。
- 生成每次 run 的目录结构。
- 对 profile 做分发：
  - 专用 validate 路径（`mini_internet` / `real_topology_rr`）
  - generic 路径（其他 profile）
- 维护 `latest` 链接和 `runner_summary.json`。

这是当前最重要的抽象边界：

```bash
scripts/seed_k8s_profile_runner.sh <profile_id> <action>
```

#### D. Validate 脚本

位置：`scripts/validate_k3s_*_multinode.sh`

职责：

- 做 kubeconfig/preflight 检查。
- 编译。
- 远程构建镜像并推送到 registry。
- 部署到 K3s。
- 写出严格验证证据。

当前已有：

- `scripts/validate_k3s_mini_internet_multinode.sh`
- `scripts/validate_k3s_real_topology_multinode.sh`

---

## 3. 目录与产物抽象

### 3.1 单次运行的标准目录

统一输出到：

```text
output/profile_runs/<profile_id>/<run_id>/
```

标准子目录：

- `compiled/`：编译产物（`k8s.yaml`, `build_images.sh`）
- `validation/`：验证证据
- `observe/`：运行时观测快照
- `report/`：归一化报告
- `runner.log`：runner 总日志
- `runner_summary.json`：runner 级状态摘要
- `diagnostics.json` / `next_actions.json`：runner 级下一步动作

### 3.2 为什么必须保留这些层

这是为了服务两个消费方：

- **人类维护者**：可以直接看 `summary.json` / `bird_sample.txt` / `placement.tsv`
- **AI/agent**：可以只读固定路径，输出稳定的“状态 + 证据 + 下一步命令”

这也是为什么我们不把所有逻辑都塞进一个超长 shell 脚本里：

- 编译产物要能单独复用
- 验证证据要能单独审阅
- 报告要能独立再生成

---

## 4. 当前两个代表性例子的抽象意义

### 4.1 `mini_internet`

定位：

- 小规模、可重复、强校验的基线例子。
- 用来验证“多节点调度 + 协议收敛 + 连通性 + 自愈”整条链路。

它代表的抽象能力：

- profile 化运行
- `strict3` / `auto` placement
- BGP 与 ping 的强校验
- Pod 重建/恢复验证
- 适合作为 CI/回归主力例子

它的意义不是规模，而是**验证强度高、闭环完整**。

### 4.2 `real_topology_rr`

定位：

- 真实拓扑数据集迁移后的多节点大演示例子。
- 当前默认跑 `214` 规模，未来可扩到 `1897`。

它代表的抽象能力：

- 外部数据文件驱动
- K3s 多节点大规模部署
- route reflector iBGP 拓扑支持
- registry 远程 build + push
- 大规模 workload 计数、分布与 BGP 抽样验证

它的意义不是“取代 mini”，而是：

- `mini_internet` 负责**严密回归**
- `real_topology_rr` 负责**大规模真实演示**

两者不能互相代替。

---

## 5. K3s 运行模式的核心抽象提升

相对于过去“直接跑 Compose 或手写脚本”的模式，现在的提升主要有五点。

### 5.1 从“容器集合”升级为“生命周期对象”

Docker Compose 关注：

- build
- up
- ps
- logs

现在的 K3s 抽象关注：

- doctor
- start
- verify
- observe
- report
- triage

这使得运行不再只是“起来没起来”，而是有阶段、有验收、有证据。

### 5.2 从“单次命令”升级为“可追踪运行”

以前常见问题：

- 人工执行多步命令，终端关了就丢信息。
- 很难知道这次部署和上次部署差别在哪。

现在：

- 每次 run 有独立目录。
- `latest` 永远指向当前最相关的一次运行。
- 失败可以只看 `diagnostics.json`。

### 5.3 从“脚本成功”升级为“证据成功”

现在的成功判据必须落盘。

例如：

- `mini_internet` 看 `placement.tsv` / `bird_router151.txt` / `ping_150_to_151.txt`
- `real_topology_rr` 看 `counts.json` / `placement.tsv` / `bird_sample.txt`

这是后续自动化和 agent 化的基础。

### 5.4 从“示例是孤岛”升级为“示例属于 profile 体系”

新增例子时，不能只加 `examples/kubernetes/foo.py`。

必须同时回答：

- 它属于哪个 profile？
- 它默认 namespace/cni 是什么？
- 它成功证据是什么？
- 它失败时最小重试命令是什么？

### 5.5 从“实验能跑”升级为“可维护”

可维护性体现在：

- repo-root 相对路径
- `source scripts/env_seedemu.sh`
- `summary.json` / `diagnostics.json` 约定
- failure code 映射
- 统一 runner 入口

---

## 6. RR core 变更的工程意义

### 6.1 变更点

核心改动位于：

- `seedemu/core/Node.py`
- `seedemu/layers/Ibgp.py`
- `tests/ibgp_route_reflector_test.py`

### 6.2 新行为

新增 Router API：

- `Router.makeRouteReflector(is_rr=True)`
- `Router.isRouteReflector()`

Ibgp 行为：

- AS 内无 RR：保持 full-mesh
- AS 内有 RR：
  - RR 之间 full-mesh
  - client 只连 RR
  - RR -> client 会话带 `rr client;`

### 6.3 为什么这是“内核级”改动

因为这不是示例层逻辑，而是：

- 影响所有可能使用 Ibgp 的拓扑
- 影响 BIRD 配置生成
- 影响 graph 可视化
- 影响未来真实拓扑和教学拓扑的行为一致性

所以它必须有独立单测，不能只靠一次大规模跑通来证明。

---

## 7. 测试分层建议

### 7.1 单元测试层

适合放在 `tests/*.py`，要求秒级完成。

当前核心例子：

- `tests/ibgp_route_reflector_test.py`
- `tests/kubevirt_compiler_test.py`

RR 相关单测至少应覆盖：

- 无 RR 时 full-mesh 不变
- 单 RR 时 client 只连 RR
- 多 RR 时 client 连所有 RR，RR 之间互连
- graph 与会话拓扑一致
- 不同连通分量在同一 AS 内行为正确

### 7.2 编译回归层

目标：确认编译器输出格式不坏。

推荐：

```bash
python3 -m unittest tests/kubevirt_compiler_test.py -v
```

未来如果 `KubernetesCompiler` 再扩展 registry/build 行为，建议新增：

- `build_images.sh` 结构断言
- `SEED_BUILD_PARALLELISM` 行为断言
- `SEED_DOCKER_BUILDKIT` 输出断言

### 7.3 多节点验证层

这是最接近真实运行的自动化。

命令：

```bash
scripts/seed_k8s_profile_runner.sh mini_internet all
scripts/seed_k8s_profile_runner.sh real_topology_rr all
```

该层不适合高频 CI，但适合：

- 发布前验收
- 集群变更后回归
- 演示前预热

### 7.4 手工检查层

永远保留最小可执行手工检查：

```bash
export KUBECONFIG=output/kubeconfigs/seedemu-k3s.yaml
kubectl -n <ns> get pods -o wide
kubectl -n <ns> get deploy -o wide
kubectl -n <ns> exec -it <router-pod> -- birdc show protocols
```

原因：

- 自动化失败时，人工需要最短路径确认真实状态。
- 手工命令是所有文档、agent、排障的共同底座。

---

## 8. 新增一个 K3s profile 的标准流程

### 8.1 第一步：先定义它属于哪一类

先决定它是：

- **generic profile**：generic verify 就够用
- **specialized profile**：需要专用 validate 脚本

判断标准：

- 是否有强协议校验？
- 是否有严格 placement 规则？
- 是否需要远程 build / 多节点证据？
- 是否有外部数据集？

只要答案大于等于一个“是”，优先考虑专用 validate 脚本。

### 8.2 第二步：加 compile script

要求：

- 只负责拓扑和 compiler 参数
- 所有运行时差异优先 env 化
- 缺关键文件时 fail-fast

### 8.3 第三步：加 profile

必须在 `configs/seed_k8s_profiles.yaml` 中登记：

- `profile_id`
- `compile_script`
- `default_namespace`
- `default_cni_type`
- `default_scheduling_strategy`
- `verify_mode`
- `observe_required_files`

### 8.4 第四步：确定验证方式

- generic：沿用 runner generic 路径
- specialized：新增 `scripts/validate_k3s_<profile>_multinode.sh`

### 8.5 第五步：补文档与证据说明

至少更新：

- `docs/runbooks/opencode_seed_lab_quickstart.md`
- `examples/kubernetes/README.md`

如果是结构性能力增强，再补：

- `docs/k3s_runtime_architecture.md`
- 时间戳 runbook

---

## 9. 维护者最常做的事情

### 9.1 升级一个示例脚本

检查清单：

- 示例脚本只改 compile 行为，没有偷偷塞部署逻辑
- 新 env 都有默认值或 fail-fast
- README / quickstart 有对应说明
- validate 证据路径没变或已同步更新 report

### 9.2 调整 runner

风险最大，因为它是所有 profile 的统一入口。

修改 `scripts/seed_k8s_profile_runner.sh` 时必须确认：

- `latest` 链接逻辑不回退
- read-only action（`report`, `triage`）可以复用旧 run
- `KUBECONFIG` 选择逻辑不会误连 `localhost:8080`
- `runner.log` 不会因为只读动作被错误截断

### 9.3 调整 validate 脚本

必须保证：

- 失败总能生成 `diagnostics.json`
- 失败总有最小重试命令
- 关键证据文件路径稳定
- preflight 可以单独运行

### 9.4 调整 report 逻辑

必须保证：

- 没有 observe 目录时也能生成报告
- profile 差异不会导致引用不存在的证据文件
- 失败分支不会因为缺字段而再次失败

---

## 10. 当前实际运行规模的抽象边界

### 10.1 `mini_internet`

当前定位：

- 常驻回归例子
- 小规模、快验证
- 最适合频繁执行

### 10.2 `real_topology_rr` 214

当前定位：

- 真实拓扑多节点标准演示
- 适配当前 KVM 三节点资源
- 是“真实拓扑链路可工作”的主证据

### 10.3 `real_topology_rr` 1897

当前定位：

- 大演示目标
- 不是当前默认回归用例
- 需要更高 KVM 规格后再作为常规演示入口

维护原则：

- 不要让 1897 成为默认 smoke/CI
- 214 作为真实拓扑默认验证规格
- 1897 作为容量验证与大演示专用规格

---

## 11. 未来开发建议

### 11.1 建议优先做的方向

1. **把 failure code/profile 关系继续结构化**
- 让 `configs/seed_failure_action_map.yaml` 支持 profile-aware fallback。

2. **把 report 再统一成 profile-aware 模板**
- 现在已支持 mini/real 两条主线，但仍可继续抽象。

3. **给 `KubernetesCompiler` 增加更可测试的 build plan 输出**
- 把 `build_images.sh` 的 job 列表单独输出为 JSON，便于测试和审计。

4. **给 `real_topology_rr` 增加更细的 BGP 抽样策略**
- 当前只要求存在 `Established`，未来可增加多 AS 抽样。

### 11.2 不建议现在做的方向

1. 把所有 profile 合并成一个超级 validate 脚本
- 会迅速失控，失去 profile 语义。

2. 把所有逻辑塞进 AI prompt
- 会让“没有 AI 就无法复现”，与当前目标相反。

3. 让大规模 1897 成为默认回归
- 会拖慢日常开发与问题定位。

---

## 12. 发布前检查清单

每次准备演示或合并较大改动前，至少做：

```bash
python3 -m unittest tests/ibgp_route_reflector_test.py -v
python3 -m unittest tests/kubevirt_compiler_test.py -v
scripts/opencode_seedlab_smoke.sh
scripts/seed_k8s_profile_runner.sh mini_internet report
scripts/seed_k8s_profile_runner.sh real_topology_rr report
```

如果当天涉及 K3s 集群变更，再加：

```bash
scripts/seed_k8s_profile_runner.sh mini_internet all
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr all
```

---

## 13. 结论

当前仓库的 K3s/K8s 抽象已经稳定形成以下结构：

- 示例脚本：负责生成
- profile：负责命名与默认值
- runner：负责生命周期入口
- validate：负责真实证据化验收
- report：负责给人和 AI 的统一阅读面

未来所有新增能力，建议都顺着这五层扩展，而不是绕开它们单点堆脚本。这样才能同时满足：

- 人能清晰复现
- AI 能稳定协作
- 文档能长期维护
- 测试能持续回归

# SEED K3s+KVM 主线改动分层回放与建议 Commit 切法

最后更新：`2026-03-08 10:30 UTC`

这份文档不讲泛泛背景，只回答 4 个维护问题：

1. 这次主线稳定化到底改了哪些层。
2. 如果要自己 review / cherry-pick，应该按什么顺序看。
3. 如果要自己继续改，先改哪层、后改哪层。
4. 每一层改完后，最低限度要跑什么测试。

如果只想看“怎么跑”，优先看：

- `docs/runbooks/seed_lab_evidence_first_operator_guide.md`
- `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`

如果想看“当前机器上哪个仓库才是真正生效的仓库”，看：

- `docs/runbooks/seedemu_repo_variant_diff_20260306.md`

---

## 1. 当前已经验证通过的主线状态

当前已确认通过：

- `mini_internet`
  - `output/profile_runs/mini_internet/20260308_082105/validation/summary.json`
- `real_topology_rr`
  - `output/profile_runs/real_topology_rr/20260308_080803/validation/summary.json`
- `real_topology_rr_scale`
  - `output/profile_runs/real_topology_rr_scale/20260308_100706/validation/summary.json`

其中 `real_topology_rr_scale` 的关键验收证据是：

- `output/profile_runs/real_topology_rr_scale/20260308_100706/validation/counts.json`
- `output/profile_runs/real_topology_rr_scale/20260308_100706/validation/placement.tsv`
- `output/profile_runs/real_topology_rr_scale/20260308_100706/validation/bird_sample.txt`

结论：

- 当前 3 节点 K3s+KVM 基线已恢复。
- 真实拓扑 baseline 已稳定。
- 真实拓扑 scale 已能在 `214` 规模上跑通。
- `1897` 仍属于下一阶段扩容演示，不是当前默认回归规格。

---

## 2. 这次改动应该怎么分层理解

建议始终按下面 4 层理解，不要混着改：

### Layer 1：核心网络语义层（core / layers）

职责：

- 定义 RR 能力和 clustered RR 能力。
- 定义 routing / ospf 的 scale knob。
- 保证默认语义仍然安全、可回归。

文件：

- `seedemu/core/Node.py`
- `seedemu/core/AutonomousSystem.py`
- `seedemu/layers/Ibgp.py`
- `seedemu/layers/Routing.py`
- `seedemu/layers/Ospf.py`
- `tests/ibgp_route_reflector_test.py`
- `tests/routing_scale_profiles_test.py`

这一层的核心原则：

- baseline 默认行为不能被实验逻辑污染。
- 有 scale 行为时，必须通过显式 knob 触发。

### Layer 2：K8s 编译与运行层（compiler / example / profile / validate）

职责：

- 把 `RR_214_example.py` 迁移成 K8s 示例。
- 把 baseline / scale 接到统一 profile 入口。
- 把编译、构建、部署、验证做成固定流水线。

文件：

- `seedemu/compiler/Kubernetes.py`
- `examples/kubernetes/k8s_real_topology_rr.py`
- `configs/seed_k8s_profiles.yaml`
- `scripts/seed_k8s_profile_runner.sh`
- `scripts/validate_k3s_real_topology_multinode.sh`
- `scripts/validate_k3s_mini_internet_multinode.sh`
- `scripts/kvm_lab.sh`
- `scripts/kvm_quickstart.sh`

这一层的核心原则：

- 统一入口始终是 `scripts/seed_k8s_profile_runner.sh <profile> <action>`。
- `mini_internet` 是回归基线。
- `real_topology_rr` 是真实拓扑 baseline。
- `real_topology_rr_scale` 是真实拓扑 scale 档位。

### Layer 3：证据与报告层（status / report / failure map）

职责：

- 把“现在跑到哪一步”写成稳定的证据文件。
- 把失败原因从日志里抽成明确 code。
- 让人和 AI 都能从固定路径直接读状态。

文件：

- `scripts/seed_lab_entry_status.sh`
- `scripts/seedlab_report_from_artifacts.sh`
- `configs/seed_failure_action_map.yaml`

这一层的核心原则：

- 不靠聊天记忆当前状态。
- 不靠人脑推断镜像流向。
- 不靠 AI 猜测失败原因。

### Layer 4：维护与交接文档层（docs）

职责：

- 让不懂 K8s 的同学也能按文档复现。
- 让学长能快速看懂“以前怎么做、现在怎么做、改在哪里”。
- 让未来维护者知道默认值与实验值的边界。

文件：

- `docs/runbooks/seed_lab_evidence_first_operator_guide.md`
- `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`
- `docs/k3s_runtime_architecture.md`
- `docs/runbooks/seedemu_repo_variant_diff_20260306.md`
- `docs/runbooks/seed_k8s_multilayer_commit_replay_20260308.md`

---

## 3. 建议的 Commit 切法

如果要把这批改动拆成可 review、可回滚、可 cherry-pick 的 commit，建议按下面顺序切。

### Commit A：`core: add rr/clustered reflection and scale knobs`

建议包含：

- `seedemu/core/Node.py`
- `seedemu/core/AutonomousSystem.py`
- `seedemu/layers/Ibgp.py`
- `seedemu/layers/Routing.py`
- `seedemu/layers/Ospf.py`
- `tests/ibgp_route_reflector_test.py`
- `tests/routing_scale_profiles_test.py`

为什么第一层先提交它：

- 它定义了后面 K8s 示例和 profile 依赖的语义。
- 这一层最适合独立跑单测。
- 这层稳定后，后面脚本和文档才有落点。

这一层最低测试门槛：

```bash
python3 -m unittest tests/ibgp_route_reflector_test.py -v
python3 -m unittest tests/routing_scale_profiles_test.py -v
python3 -m unittest tests/kubevirt_compiler_test.py -v
```

### Commit B：`k8s: add real topology rr profiles and multinode validation`

建议包含：

- `seedemu/compiler/Kubernetes.py`
- `examples/kubernetes/k8s_real_topology_rr.py`
- `configs/seed_k8s_profiles.yaml`
- `scripts/seed_k8s_profile_runner.sh`
- `scripts/validate_k3s_real_topology_multinode.sh`
- `scripts/validate_k3s_mini_internet_multinode.sh`
- `scripts/kvm_lab.sh`
- `scripts/kvm_quickstart.sh`

为什么第二层单独提交：

- 这是把 core 语义接到 K3s/KVM 主线的那一层。
- 它包含真实运行路径，不应与文档或报告层混在一起 review。
- 它也包含 KVM 版本参数化（`SEED_KVM_UBUNTU_SERIES=jammy|noble`）。

这一层最低测试门槛：

```bash
python3 -m unittest tests/kubevirt_compiler_test.py -v
scripts/seed_k8s_profile_runner.sh mini_internet report
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr report
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale report
```

如果要做运行验收，再加：

```bash
scripts/seed_k8s_profile_runner.sh mini_internet all
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr all
SEED_TOPOLOGY_SIZE=214 scripts/seed_k8s_profile_runner.sh real_topology_rr_scale all
```

### Commit C：`tooling: improve evidence-first status and report output`

建议包含：

- `scripts/seed_lab_entry_status.sh`
- `scripts/seedlab_report_from_artifacts.sh`
- `configs/seed_failure_action_map.yaml`

为什么单独切：

- 这层不改变网络语义，但改变“人如何理解运行结果”。
- 这层决定 AI/维护者看到的是不是准确信息。
- 这里已经显式区分：
  - `mini_internet` 默认 registry push
  - `real_topology_rr*` 默认 preload

这一层最低测试门槛：

```bash
scripts/seed_lab_entry_status.sh
scripts/opencode_seedlab_smoke.sh
scripts/seed_k8s_profile_runner.sh mini_internet report
scripts/seed_k8s_profile_runner.sh real_topology_rr_scale report
```

### Commit D：`docs: document baseline, scale and operator workflow`

建议包含：

- `docs/runbooks/seed_lab_evidence_first_operator_guide.md`
- `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`
- `docs/k3s_runtime_architecture.md`
- `docs/runbooks/seedemu_repo_variant_diff_20260306.md`
- `docs/runbooks/seed_k8s_multilayer_commit_replay_20260308.md`

为什么最后提交：

- 文档依赖前 3 层已经稳定。
- 文档最后写，才不会写错默认值、证据路径和运行结果。

---

## 4. 这次实际解决掉的核心问题

### 4.1 不是 compile 挂，而是 registry push 超时

之前最关键的误判点是：

- `mini_internet` 最近失败的直接原因，是 master registry `192.168.122.110:5000` push 超时。
- 不是 Python compile 本身挂掉。

所以现在 failure map 里已经补上：

- `REGISTRY_TIMEOUT`

### 4.2 `device_ospf_only` 曾导致 BIRD 重复 kernel protocol

这是本次 scale 真正卡住过的一次核心 bug。

症状：

- BIRD 报 `Kernel syncer (kernel1) already attached to table master4`

根因：

- `bird.conf` 内联了一份 `protocol kernel`
- `/etc/bird/conf/kernel.conf` 又放了一份 `protocol kernel`

修复：

- 默认模式不变。
- `device_ospf_only` 模式下切到 `rnode_bird_no_kernel`，只在 `kernel.conf` 放 kernel protocol。

### 4.3 `large_scale` OSPF 慢时序不适合作为当前 214 默认值

这点一定要写清楚，因为它是“学长旧思路已吸收，但不默认启用”的典型例子。

已确认的现象：

- OSPF 邻接会卡在 `Init/ExStart`
- BGP session 保持 `Connect`

因此现在主线采取的策略是：

- `real_topology_rr_scale` 默认：
  - `SEED_IBGP_REFLECTION_MODE=clustered`
  - `SEED_ROUTING_KERNEL_EXPORT_MODE=device_ospf_only`
  - `SEED_OSPF_TIMING_PROFILE=default`
- `large_scale` OSPF 仍然保留为显式实验开关，但不再是当前 3 节点实验环境的默认值。

### 4.4 SSH 探测曾卡死，已改成有限超时

之前 KVM VM SSH 一旦异常，preflight 会跟着卡住。

现在修复方式：

- `scripts/validate_k3s_real_topology_multinode.sh` 统一通过 `run_ssh_probe()` 做短时探测
- 支持 `SEED_SSH_PROBE_TIMEOUT_SECONDS`

这直接提升了“失败时可诊断性”。

---

## 5. 以后自己继续改时，应该怎么下手

### 5.1 如果要改协议语义

只先动：

- `seedemu/core/...`
- `seedemu/layers/...`
- `tests/...`

不要一上来就改：

- `scripts/validate_*`
- `docs/...`

顺序必须是：

1. 改 core/layers
2. 单测过
3. 再接 profile / validate
4. 最后补 docs

### 5.2 如果要改 K3s 运行流程

优先看：

- `scripts/seed_k8s_profile_runner.sh`
- `scripts/validate_k3s_real_topology_multinode.sh`
- `scripts/validate_k3s_mini_internet_multinode.sh`
- `seedemu/compiler/Kubernetes.py`

不要直接去改 docs 里的命令示例，先把脚本行为改准。

### 5.3 如果要改学长的大规模思路

优先沿用已有 knob，不要再回到“直接覆盖默认模板”的方式：

- iBGP：`simple` / `clustered`
- Routing：`default` / `device_ospf_only`
- OSPF：`default` / `large_scale`

如果再加新的实验档位，也建议继续走：

- 新 knob
- 新 profile
- 新 validate 证据

而不是再造一条平行脚本链。

---

## 6. 一眼就能看懂的维护顺序

如果学长明天要自己接着改，建议从这里开始：

1. 先看 `docs/runbooks/seed_lab_evidence_first_operator_guide.md`
2. 再看 `docs/runbooks/20260305_k3s_kvm_multinode_real_topology_rr.md`
3. 如果要自己动源码，再看 `docs/runbooks/seedemu_repo_variant_diff_20260306.md`
4. 如果要 review 这次改动的结构，再看 `docs/runbooks/seed_k8s_multilayer_commit_replay_20260308.md`

如果只记一条命令入口：

```bash
scripts/seed_k8s_profile_runner.sh <profile> <action>
```

如果只记一条状态入口：

```bash
scripts/seed_lab_entry_status.sh
```

如果只记一条证据路径模式：

```bash
output/profile_runs/<profile>/latest/
```

---

## 7. 当前不该混进默认主线的东西

这些不是不能做，而是**现在不应默认为真**：

1. 容器基础镜像直接默认切到 `24.04`
2. `large_scale` OSPF 慢时序直接覆盖默认 OSPF
3. 手工启动 `bird` 进入 K3s 默认路径
4. 再回到“用 prompt 解释流程，而不是用固定脚本入口”的方式

默认主线必须继续满足：

- baseline 可回归
- scale 可显式开启
- 证据路径稳定
- 没有 AI 也能跑

---

## 8. 结论

这次主线收敛，真正的价值不是“又多了几个脚本”，而是把过去分散的东西整理成了 4 层：

- core 语义层
- K8s 运行层
- 证据报告层
- 文档交接层

以后只要继续遵守这个分层，就可以同时满足：

- 学长能自己改
- 你能自己维护
- AI 能基于证据协助
- 多物理机扩展时不用重造入口

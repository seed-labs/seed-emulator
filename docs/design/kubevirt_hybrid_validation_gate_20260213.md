# SEED KubeVirt Hybrid 验收门禁报告（2026-02-13）

## 1. 执行背景
- 验证分支：`integration/kubevirt-verify`
- 基线来源：KubeVirt 混合部署特性分支（单提交引入文档与编译器变更）
- 执行策略：先修后并 + Kind/K8s 1.32.2 + 中等覆盖
- 执行时间：2026-02-13

## 2. 已完成修复
1. `seedemu/compiler/Kubernetes.py`
   - KubeVirt 路径补齐 `fork` 语义。
   - KubeVirt 路径补齐 `post config commands`。
   - KubeVirt 不支持项改为显式失败（不再静默忽略）。
   - Cloud-Init 改为 Secret 引用（规避 inline `userData` 体积限制）。
   - VM 清单改用 `runStrategy`（替代弃用字段 `running`）。
2. `seedemu/core/Node.py`
   - `copySettings()` 传播 `virtualization_mode`。
3. `setup_kubevirt_cluster.sh`
   - 固定 Kind/K8s/Multus/KubeVirt 版本。
   - 无 `/dev/kvm` 自动 `useEmulation=true`。
   - 补齐 Kind 节点 CNI `bridge` 插件，避免 Multus 二网卡创建失败。
4. 新增验证资产
   - 示例：`examples/kubernetes/k8s_hybrid_kubevirt_demo.py`
   - E2E：`scripts/validate_kubevirt_hybrid.sh`
   - 单测：`tests/kubevirt_compiler_test.py`

## 3. 验证矩阵与结果
### 3.1 编译/回归
- `PYTHONPATH=. python3 tests/kubevirt_compiler_test.py -v`：**通过**。
- `examples/kubernetes/k8s_nano_internet.py` 编译回归：**通过**。

### 3.2 集群环境
- Kind 节点镜像：`kindest/node:v1.32.2`
- Multus：`v4.1.0`
- KubeVirt：`v1.7.0`
- 节点架构：`arm64`
- 宿主机 `/dev/kvm`：**缺失**（已自动启用 emulation）

### 3.3 混合拓扑 E2E（VM + 容器 + BGP）
- 容器 Deployment：**Ready**
- VM/VMI：**未 Ready（失败）**
- 门禁结论：**Not Merge**（按“任一阻断失败不合并”）

## 4. 阻断证据
本轮阻断集中在 `arm64 + 无 /dev/kvm` 的 VM 启动链路，KubeVirt 在该组合下无法稳定拉起目标 VMI。

关键证据（本地）：
- `output/kubevirt_validation/failure_events.txt`
- `output/kubevirt_validation/failure_vmi_describe.txt`
- `output/kubevirt_validation/failure_vm_describe.txt`
- `output/kubevirt_validation/failure_virt_launcher_compute.log`

关键现象摘要：
- `VMI readiness failed`（`kubectl wait vmi --for=condition=Ready` 超时）
- 事件包含 `host-passthrough` 与当前 hypervisor 组合不兼容报错，以及同步失败。

## 5. 复测建议（x86 + /dev/kvm）
建议在 x86_64 且 `/dev/kvm` 可用的主机复测：

```bash
# 1) 环境重建
SEED_CLUSTER_NAME=seedemu-kvtest WORKER_COUNT=1 ./setup_kubevirt_cluster.sh

# 2) 编译回归
PYTHONPATH=. python3 tests/kubevirt_compiler_test.py -v

# 3) 混合拓扑验收（失败时自动采集证据）
SEED_CLUSTER_NAME=seedemu-kvtest SEED_NAMESPACE=seedemu-kvtest ./scripts/validate_kubevirt_hybrid.sh
```

## 6. 2026-02-14 补充：Runtime Profile 兼容策略
为兼容 `Linux(x86/arm64)` 与 `Linux server(x86)`，新增 Runtime Profile：

- `auto`：自动选择；在 `arm64 + 无 /dev/kvm` 自动降级为 `degraded`。
- `full`：强制 KubeVirt VM + 容器混合模式。
- `degraded`：强制全部容器模式（不生成 VM）。
- `strict`：要求 VM 模式可用，否则直接失败。

本机（`arm64` 且 `/dev/kvm` 缺失）复验结果：
- `SEED_RUNTIME_PROFILE=auto`：**通过**（自动降级为 `degraded`，连通性/BGP/自愈通过）。
- `SEED_RUNTIME_PROFILE=strict`：**按预期失败**（快速失败，阻止错误环境继续执行）。

结论口径更新：
- 本机可用结论：**可通过 `auto/degraded` 完成稳定验证**。
- 目标门禁（真实 VM 混合模式）结论：**仍需在 x86 + /dev/kvm 环境跑 `full/strict` 后再合并**。

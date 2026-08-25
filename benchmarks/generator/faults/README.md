<!-- README_SYNC_REQUIRED -->

# FaultSpec 与 FaultDriver 平台

本层把声明式 `FaultSpec v1` 转换为安全、确定性、可恢复的执行计划，并提供故障插件、
影响分析、组合覆盖率、崩溃恢复和大规模计划验证。

> **强制同步规则（README_SYNC_REQUIRED）**：修改本目录任意 `.py` 文件时，必须同步更新
> 本 README。新增或改变 FaultSpec、FaultDriver、CLI 或执行生命周期时，还必须更新
> `generator/README.md`；若 Bundle 消费方式变化，同时更新 `generator/bundle/README.md`。

## 数据流

```text
FaultSpec v1
  → selector/capability 目标解析
  → FaultDriver.compile()
  → 影响与冲突检查
  → CompiledFaultPlan + plan_fingerprint
  → baseline snapshot
  → inject
  → active verification
  → recover
  → recovery verification + durable journal
```

`FaultSpec` 描述意图，不直接携带宿主机命令。具体动作只能由注册的 FaultDriver 生成。

## 模块索引

| 文件 | 作用 |
|---|---|
| `models.py` | `FaultSpec`、`FaultAction`、`CompiledFaultPlan` 严格合同 |
| `drivers.py` | `FaultDriver` 接口与内置 Docker/网络/软件插件 |
| `compiler.py` | 目标解析、驱动选择、影响分析、冲突检查和计划编译 |
| `journal.py` | 原子日志、状态快照、执行阶段和崩溃恢复 |
| `coverage.py` | 驱动/资产/期望覆盖率和确定性自动组合选择 |
| `software.py` | 从软件能力与 fault profile 发现 FaultSpec 候选 |
| `adapters.py` | 把已有 benchmark 故障模板迁移为 FaultSpec/计划 |
| `scale_validation.py` | 大拓扑规划性能和抽样覆盖验证 |
| `cli.py` | 编译、选择、发现、覆盖率、注入和恢复入口 |

## FaultDriver 合同

驱动必须：

1. 声明唯一、版本化的插件 ID 和所需能力；
2. 严格校验参数和目标数量；
3. 生成最小作用域的 baseline、inject、verify 和 recover 动作；
4. 提供受影响资产/ASN 与 protected assets 信息；
5. 保证恢复幂等，并允许从 journal 重放；
6. 不接受任意用户 shell，不逃逸批准容器和接口；
7. 增加正向、冲突、边界、恢复和盲测观测测试；
8. 更新本 README 和插件清单相关文档。

当前驱动覆盖容器停止、DNS nameserver、BIRD ASN、scoped ACL、`tc/netem`、IPv6 connected
route、OSPF area、Docker network，以及通用软件配置替换和可执行文件禁用。以运行时
inventory 为准：

```bash
python3 -m generator.bundle.cli plugins
```

## CLI

```bash
python3 -m generator.faults.cli compile --help
python3 -m generator.faults.cli select --help
python3 -m generator.faults.cli discover-software --help
python3 -m generator.faults.cli validate-software --help
python3 -m generator.faults.cli coverage --help
python3 -m generator.faults.cli inject --help
python3 -m generator.faults.cli recover --help
python3 -m generator.faults.cli recover-incomplete --help
```

## 安全与恢复

- 编译阶段锁定实际 container、interface、ASN 和资产集合。
- 同一资源上的不可兼容动作在执行前拒绝。
- protected observer 不得被选为破坏目标。
- journal 在每个状态变更前后原子写入，并记录 action fingerprint。
- 进程崩溃后只恢复已知、已注入且尚未恢复的动作。
- 清理失败必须保留失败状态并阻止后续批次，不得假报成功。
- netem 的延迟、丢包、限速和抖动参数必须在驱动边界校验。

## 验证

```bash
python3 -m py_compile generator/faults/*.py
python3 tests/test_fault_injection_platform.py
python3 tests/test_benchmark_generator.py
python3 tests/test_generator_readmes.py
```
## 通用组合语义（2026-08-26）

故障编译器接受任意声明顺序的 `depends_on`，先进行稳定拓扑排序，再产生注入
顺序；恢复顺序始终是该顺序的严格逆序。未知依赖、自依赖、依赖环、关系类型
与依赖图不一致，以及同一容器的 `exclusive` 故障和其他突变组合都会失败
关闭。编译计划的 `impact` 现在显式记录 `dependency_edges`、
`injection_order` 和 `recovery_order`，用于执行日志、盲测与晋级审计。

`independent` 不允许依赖边；`cascading` 必须只有一个根且其余故障均有依赖；
`mixed` 必须同时存在至少两个独立根和一个依赖节点。FaultExecutor 按已编译
顺序注入，并按 `cleanup_order` 逆序恢复，因此崩溃恢复仍使用同一确定性计划。

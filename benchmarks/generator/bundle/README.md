<!-- README_SYNC_REQUIRED -->

# Multi-Agent Benchmark Bundle

本层把一个高层 `BenchmarkRequest v1` 编译为完整、可测试、可评分、可发布的
`CompiledBenchmarkBundle`。生成过程由九类确定性 Worker 组成，既可以内置单进程运行，
也可以通过角色受限的外部 Worker 和分布式调度运行。

> **强制同步规则（README_SYNC_REQUIRED）**：修改本目录任意 `.py` 文件时，必须在同一
> 变更中更新本 README。若更改 Bundle 公共接口、生产数据流或 CLI，还必须同步更新
> `generator/README.md`；修改 `examples/` 时同步更新 `examples/README.md`。

## 生产数据流

```text
BenchmarkRequest
  → build_agent_tasks()
  → BenchmarkCoordinator
  → 9 × AgentArtifact
  → BundleCompiler
  → safety + quality + dedup + scale
  → optional Docker no-AI lifecycle × N
  → qualification
  → optional public/private release
  → summary.json
```

`ProductionGenerator.generate()` 是完整的一键入口。请求不包含可执行代码；Worker 只从已
注册应用模板、FaultDriver 和 capability manifest 产生受控产物。

## 九类 Worker

| 角色 | 产物 | 职责 |
|---|---|---|
| `topology_agent` | `topology_ref` | 绑定拓扑指纹、资产和能力 |
| `software_agent` | `software` | 选择软件包与软件能力 |
| `service_agent` | `service` | 生成启动命令和健康检查 |
| `workload_agent` | `workload` | 生成真实业务工作负载 |
| `fault_agent` | `fault_set` | 自动选择安全且有覆盖度的故障组合 |
| `test_agent` | `test` | 生成 baseline、active、recovery 测试 |
| `oracle_agent` | `oracle` | 保存私有根因与恢复判据 |
| `scoring_agent` | `scoring` | 定义多维评分规则 |
| `safety_reviewer_agent` | `blind_policy` | 审查安全范围和公私隔离 |

依赖关系由 `request.build_agent_tasks()` 固定生成。协调器按角色发放租约，防止错误角色领取
任务；状态和产物可以在进程崩溃后恢复。

## 模块索引

| 文件 | 作用 |
|---|---|
| `request.py` | 严格解析 `BenchmarkRequest v1`，生成九 Worker DAG 和 BundleSpec |
| `workers.py` | 九类内置 Worker、共享上下文和外部 Worker SDK |
| `templates.py` | 版本化应用语义模板及注册表 |
| `artifacts.py` | 不可变、带指纹的 AgentArtifact 与原子 ArtifactStore |
| `coordinator.py` | 带租约、重试、恢复和 DAG 校验的协调器 |
| `models.py` | 顶层 BundleSpec 与 CompiledBenchmarkBundle 合同 |
| `specs.py` | 服务、工作负载、测试、oracle、评分、生命周期和盲测模型 |
| `compiler.py` | 解析能力选择器并编译跨 Agent 产物 |
| `plugins.py` | Bundle 组件共享的版本化插件注册表 |
| `security.py` | 跨产物安全审查和盲测泄漏检查 |
| `quality.py` | 难度、可观测性、恢复性、唯一性、组合选择和去重 |
| `scale.py` | 5/20/100/1000/10000 计划级规模验证 |
| `lifecycle.py` | Docker baseline → injection → active → recovery 执行与回执 |
| `qualification.py` | 至少两次独立回执的正式资格记录 |
| `publishing.py` | 多维评分、SemVer 注册和 public/private 原子发布 |
| `scheduler.py` | 分布式文件调度、租约、隔离、重试、缓存和 CI 矩阵 |
| `pipeline.py` | 一键生产流水线和白名单调度 Worker Runtime |
| `pilot.py` | 测试和集成使用的确定性三应用 pilot |
| `cli.py` | 所有 Bundle、Worker、评分、发布和调度命令入口 |

## CLI 入口

```bash
# 一键生成
python3 -m generator.bundle.cli generate --request request.json --workspace reports/run

# 查看应用模板与故障插件
python3 -m generator.bundle.cli templates
python3 -m generator.bundle.cli plugins

# 单独编译、检查和拆分
python3 -m generator.bundle.cli compile --help
python3 -m generator.bundle.cli review --help
python3 -m generator.bundle.cli split --help

# 生命周期、资格和评分
python3 -m generator.bundle.cli run --help
python3 -m generator.bundle.cli qualify --help
python3 -m generator.bundle.cli score --help

# 协调器和分布式调度
python3 -m generator.bundle.cli coordinate-status --help
python3 -m generator.bundle.cli worker-run --help
python3 -m generator.bundle.cli schedule-run --help
python3 -m generator.bundle.cli ci-matrix --help
```

## Workspace 结构

```text
<workspace>/
├── request.json
├── tasks.json
├── coordinator.json
├── artifacts/
├── bundle_spec.json
├── compiled_bundle.json
├── quality.json
├── scale_validation.json
├── ci_matrix.json
├── journals/                 # execute_lifecycle=true
├── lifecycle_round_*.json    # execute_lifecycle=true
├── qualification.json        # 正式生命周期通过后
└── summary.json
```

发布目录位于 workspace 的父目录下：`releases_public/`、`releases_private/` 和
`release_registry.json`。private bundle 文件权限必须为 `0600`。

## 扩展点

- 新应用：注册 `ApplicationTemplate v1`，或通过 `--template-file` 加载。
- 新故障：实现 `generator.faults.drivers.FaultDriver` 并注册插件。
- 外部 Worker：使用 `run_external_worker_once()`，严格按角色领取任务。
- 分布式生成：提交 `ProductionJob`，Worker 只能执行 `benchmark.generate`。
- 新评分维度：同步修改评分模型、public contract、测试和本 README。

## 安全约束

- 请求、任务和调度 payload 拒绝未知字段与目录逃逸。
- public bundle 不包含 FaultSpec、oracle、恢复动作或私有答案。
- observer 属于受保护资产，故障组合必须保持其可用性。
- 故障必须经过目标解析、影响分析、冲突检查和计划指纹计算。
- 资格必须引用真实、哈希匹配的独立生命周期回执。
- 失败、陈旧资格、版本覆盖和重复场景均 fail closed。

## 验证

```bash
python3 -m py_compile generator/bundle/*.py
python3 tests/test_multi_agent_bundle.py
python3 tests/test_production_generator.py
python3 tests/run_group_meeting_generator_demo.py --mode plan
python3 tests/run_group_meeting_generator_demo.py --mode evidence
python3 tests/test_generator_readmes.py
```

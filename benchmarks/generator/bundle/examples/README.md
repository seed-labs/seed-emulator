<!-- README_SYNC_REQUIRED -->

# BenchmarkRequest 示例

本目录保存可直接交给生产 Bundle 入口的声明式 `BenchmarkRequest v1` 示例。示例本身不含
任意 shell；所有软件、服务、工作负载、探针和故障语义都由已注册模板与插件解析。

> **强制同步规则（README_SYNC_REQUIRED）**：修改、新增或删除本目录任意 JSON 时，必须
> 在同一变更中更新本 README，并在请求字段或行为变化时同步更新 `../README.md` 和
> `../../README.md`。

## 文件

| 文件 | 生命周期 | 发布 | 用途 |
|---|---:|---:|---|
| `production_application_request.json` | 否 | 否 | 快速生成、九 Worker、质量和规模规划演示 |
| `production_application_e2e_request.json` | 两轮 | 是 | 真实 Docker、formal qualification 和 v1.0.0 发布 |

两份示例都使用 `multi_agent_application_pilot`，包含 nginx、BIND9 和 PostgreSQL，并由
`network_observer` 执行跨应用探针。默认组合为三个故障，难度为 `hard`。

## 运行

从 `benchmarks/` 目录执行：

```bash
python3 -m generator.bundle.cli generate \
  --request generator/bundle/examples/production_application_request.json \
  --workspace reports/example_plan
```

真实 E2E 会改变 Docker 状态，只应在已编译拓扑可用时执行，并使用新的 workspace：

```bash
python3 tests/run_group_meeting_generator_demo.py --mode real
```

## 主要字段

| 字段 | 约束 |
|---|---|
| `schema_version` | 当前必须为 `1` |
| `request_id` | 3–96 位小写稳定标识 |
| `objective` | 人类可读目标，不得包含执行载荷 |
| `topology_id` | 已注册声明式拓扑 ID |
| `applications` | 1–16 个唯一应用模板 ID |
| `seed` | 非空，决定确定性组合与指纹 |
| `difficulty` | `easy`、`medium`、`hard` 或 `expert` |
| `scale` | 1–10000 |
| `fault_count` | 1–64，且不能超过应用数 |
| `fault_types` | 可选的唯一插件 ID 白名单 |
| `prepare_topology` | 是否先注册并编译 `topology_spec` |
| `execute_lifecycle` | 是否运行真实 Docker 生命周期 |
| `qualification_runs` | 2–10 次独立运行 |
| `publish` | 只有取得资格后才能为真 |
| `resource_class` | `small`、`medium`、`large`、`xlarge` |

解析器拒绝未知字段、绝对路径、`..` 路径穿越和不支持的模板/插件组合。

## 新增示例检查表

1. 使用新的 `request_id` 和 seed，避免覆盖已有演示证据。
2. 先设置 `execute_lifecycle=false`、`publish=false` 验证计划。
3. 核对 `quality.json`、`scale_validation.json` 和九 Worker 状态。
4. 再进行真实无 AI 生命周期，至少取得两个独立回执。
5. 更新本 README 的文件表和行为说明。
6. 运行 `python3 tests/test_generator_readmes.py`。

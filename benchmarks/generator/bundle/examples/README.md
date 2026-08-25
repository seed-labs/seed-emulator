<!-- README_SYNC_REQUIRED -->

# BenchmarkRequest 示例

> [!IMPORTANT]
> **README_SYNC_REQUIRED（强制联级同步）**：修改、新增或删除本目录 JSON，必须同时更新
> 本 README、`generator/bundle/README.md` 和 `generator/README.md`；若修改
> `boundary_validation/`，还必须先更新其 README。联级门禁会逐层检查，不能只改叶子说明。

## 当前示例集合（2026-08-26 审计）

根层包含 `production_application_request.json`（计划/静态路径）和
`production_application_e2e_request.json`（真实端到端路径）；`boundary_validation/` 包含
IPv6、OSPF、Docker network、software config、software executable 和 cascading compound
六类正式故障边界。实际字段以 `BenchmarkRequest.from_dict` 和 CLI 校验为准。

本目录保存可直接交给生产 Bundle 入口的声明式 `BenchmarkRequest v1` 示例。示例本身不含
任意 shell；所有软件、服务、工作负载、探针和故障语义都由已注册模板与插件解析。

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

## Remaining-boundary validation fixtures

`boundary_validation/` contains real no-AI lifecycle requests for the IPv6
connected-route, BIRD OSPF-area, scoped Docker-network, generic software
configuration, and generic software executable boundaries. See
`boundary_validation/README.md` for the request-to-driver mapping and run
command. These fixtures require the compiled `bundle_boundary_validation`
Compose topology and keep publishing disabled.
## 组合与隔离字段（2026-08-26）

`fault_count` 可大于 `applications` 数量，但仍受 1–64 上限、能力清单、资源锁
和安全影响预算约束。`fault_relationship` 可设置为 `independent`、
`cascading` 或 `mixed`；`mixed` 至少需要三个故障。执行
`execute_lifecycle=true` 时，生产入口会自行创建唯一 Compose session，不应
预先手动启动同一拓扑。运行结果在 workspace 的 `isolation.json` 和
`lifecycle_round_*.json` 中记录隔离、收敛、恢复和清理证据。

同一个已编译 `topology_id` 的多个请求可以并行执行。每个请求派生独立 Compose
文档和 project，并以 manifest 的稳定 service 名发现运行时容器；请求文件
不得声明或猜测 session 容器名。

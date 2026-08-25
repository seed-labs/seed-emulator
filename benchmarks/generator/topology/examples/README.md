<!-- README_SYNC_REQUIRED -->

# 声明式拓扑请求示例

> [!IMPORTANT]
> **README_SYNC_REQUIRED（强制联级同步）**：修改、新增或删除本目录 JSON 时，必须同步
> 本 README、`generator/topology/README.md` 和 `generator/README.md`。示例 schema 或
> capability 影响 NL/Bundle/Fault 时还要更新横向消费者 README。

## 当前示例集合（2026-08-26 审计）

现有示例为 `small_ring.json`、`software_fault_demo.json`、
`multi_agent_application_pilot.json` 以及 `scale_100/500/1000/10000.json`。scale 名称描述
规划目标；只有明确的 real/sampled 回执才能声明真实 Docker 验证，`scale_10000.json` 本身不代表
单机启动了 10,000 个容器。

本目录包含 `TopologyRequest` 示例输入，用于规划、注册和编译不同规模或软件能力的 SEED
Emulator 拓扑。注册后，对应的规范化 request 和确定性 plan 会写入
`benchmarks/topology_specs/<topology_id>/`。

## 示例清单

| 文件 | AS × 每 AS 主机 | 预计容器 | 目的 |
|---|---:|---:|---|
| `small_ring.json` | 3 × 1 | 8 | 小规模环形拓扑和真实生命周期 |
| `scale_100.json` | 4 × 24 | 102 | 100 节点级拓扑验证 |
| `scale_500.json` | 10 × 49 | 502 | 500 节点规划验证 |
| `scale_1000.json` | 20 × 49 | 1002 | 1,000 节点规划/性能验证 |
| `scale_10000.json` | 50 × 199 | 10002 | 10,000 节点规划/抽样验证 |
| `software_fault_demo.json` | 1 × 1 | 4 | 声明式软件与软件故障能力 |
| `multi_agent_application_pilot.json` | 1 × 4 | 7 | nginx、BIND9、PostgreSQL 和 observer |

预计容器包括 SEED 编译器产生的基础服务；它是资源预算值，不等同于所有规模都进行了真实
Docker 启动。

## 使用

先查看具体命令参数：

```bash
python3 -m generator.topology.cli plan --help
python3 -m generator.topology.cli register --help
python3 -m generator.topology.cli compile --help
```

典型流程是用示例执行 plan，检查输出和预算后再 register；注册会生成：

```text
topology_specs/<topology_id>/request.json
topology_specs/<topology_id>/plan.json
```

随后 compile 生成：

```text
generated/declarative/<topology_id>/output/docker-compose.yml
generated/declarative/<topology_id>/output/topology_manifest.json
```

## 修改规则

- 新示例必须使用新的稳定 `topology_id` 和非空 `master_seed`。
- 地址池必须足以容纳所有 LAN、IX 和 loopback 分配。
- budget 必须显式覆盖预计 AS、容器、网络、链路、CPU 和内存。
- `explicit_edges` 使用 AS 索引，不直接使用最终 ASN。
- 安装软件只能使用严格的 `SoftwareSpec`；不得加入任意宿主 shell。
- 大规模示例默认先做 plan/performance/sampled 验证，不能声称已全量部署。
- 修改示例后必须重新生成并验证对应 `topology_specs`，不能只改 request 而保留陈旧 plan。
- 更新本 README 的示例表，并运行 `python3 tests/test_generator_readmes.py`。

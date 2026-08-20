<!-- README_SYNC_REQUIRED -->

# 声明式拓扑生成层

本层负责把 `TopologyRequest` 转换为经过预算、地址、ASN 和连通性检查的确定性
`TopologyPlan`，再适配 SEED Emulator 编译为 Docker Compose，并发布故障系统可消费的
capability manifest。

> **强制同步规则（README_SYNC_REQUIRED）**：修改本目录任意 `.py` 文件时，必须同步更新
> 本 README。改变拓扑 schema、CLI、输出布局或 capability manifest 时，还必须更新
> `generator/README.md`、受影响的 `examples/README.md`，以及消费该字段的 Bundle/Fault
> README。

## 数据流

```text
TopologyRequest JSON
  → models.TopologyRequest
  → planner.plan_topology()
  → TopologyPlan
  → registry: topology_specs/<id>/{request,plan}.json
  → compiler.build_emulator()
  → SEED Emulator Docker compiler
  → generated/declarative/<id>/output/docker-compose.yml
  → topology_manifest.json
  → fault bindings / Bundle capabilities
```

## 模块索引

| 文件 | 作用 |
|---|---|
| `models.py` | ResourceBudget、TopologyRequest、AS/链路计划和资源估算模型 |
| `planner.py` | 图生成、ASN/地址分配、预算和连通性验证 |
| `registry.py` | request/plan 原子注册、读取和目录边界 |
| `compiler.py` | SEED Emulator 构建、软件安装、Compose 和 capability manifest |
| `bindings.py` | 将故障模板绑定到真实容器、ASN、接口和软件能力 |
| `cli.py` | plan、register、compile、validate、smoke、bind、test、preflight、inventory |

## TopologyRequest

主要字段：

- `topology_id`、`master_seed`
- `as_count`、`hosts_per_as`
- `edge_policy`、`extra_links`、`explicit_edges`
- `asn_start`
- `lan_pool`、`ix_pool`、`loopback_pool`
- `lan_prefixlen`、`ix_prefixlen`
- `platform`
- `budget`
- 可选 `software: SoftwareSpec[]`

解析器拒绝未知字段。planner 必须保证地址不重叠、ASN 唯一、图连通、资源估算不超过预算，
且相同 request 和 seed 生成相同 fingerprint。

## 注册文件与编译输出

```text
topology_specs/<topology_id>/
├── request.json       # 规范化声明输入
└── plan.json          # 确定性规划结果及指纹

generated/declarative/<topology_id>/output/
├── docker-compose.yml
├── topology_manifest.json
└── <node build contexts>
```

`topology_manifest.json` 包含：

- 实际 Compose service 数量；
- 容器、ASN、节点角色、loopback 和接口地址；
- 已安装软件及其 capabilities/fault profiles；
- `container_stopped`、DNS、BIRD ASN、scoped ACL、netem 等故障绑定；
- 资源估算、拓扑指纹和网络 gateway mode。

该 manifest 是故障编译器和生产 Bundle Worker 的真实资产来源，不能使用友好名称猜测容器。

## CLI

```bash
python3 -m generator.topology.cli plan --help
python3 -m generator.topology.cli register --help
python3 -m generator.topology.cli compile --help
python3 -m generator.topology.cli validate --help
python3 -m generator.topology.cli smoke --help
python3 -m generator.topology.cli bind --help
python3 -m generator.topology.cli test --help
python3 -m generator.topology.cli preflight --help
python3 -m generator.topology.cli inventory --help
```

推荐顺序：plan → register → compile → validate → smoke/preflight → test。真实 Docker 测试完成后
必须对精确 Compose project 执行 down，并检查拓扑未污染。

## 软件安装边界

`SoftwareSpec` 通过 `node.addSoftware()`、`node.setFile()` 和受控 chmod 转换为 SEED 构建
操作，不执行请求提供的任意 shell。软件模板必须声明目标角色/ASN/节点、包、托管文件、能力
和可选 fault profile。

## 验证

```bash
python3 -m py_compile generator/topology/*.py
python3 tests/test_topology_generator.py
python3 tests/test_production_generator.py
python3 tests/test_generator_readmes.py
```

规模语义必须明确：`plan.json` 的 10,002 个预计容器不代表实际启动了 10,002 个容器；实际
执行、拓扑编译、计划性能和抽样覆盖应分别记录。

## 自然语言场景交付

`generator.nl.scene_bridge` 将通过安全检查的 `BenchmarkSceneIntent v1` 确定性转换为本层的
`TopologyRequest`。`nl-scene-generate` 使用 `compile_topology(..., root=<benchmarks>)` 在指定
benchmark 根目录注册并编译拓扑，再调用 `validate_compiled_output(..., root=<benchmarks>)` 验证
`topology_manifest.json`。该 manifest 和配套 `BenchmarkRequest` 是桥接层的交付边界；生产 Bundle
Worker 在后续独立阶段消费，桥接命令本身不运行 Worker 或生命周期。

`root` 参数只改变 benchmark 本地注册/输出根，用于受控会话测试；缺省行为和原 CLI 路径不变。
自然语言层不能绕过本层的连通性、地址分配、私有 ASN、软件选择器和资源预算检查，也不能直接构造
capability manifest。
进入本层前，桥接编译器会把应用空选择器确定性解析为单个 ASN/节点，并拒绝业务应用与受保护
`network_observer` 的资产交集；因此 manifest 中供盲测使用的观测资产不会同时成为业务故障目标。

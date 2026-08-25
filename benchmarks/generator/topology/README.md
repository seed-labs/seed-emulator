<!-- README_SYNC_REQUIRED -->

## Formal fault capability fixtures

Compiled manifests expose capability-bound targets for IPv6 connected-route
removal, BIRD OSPF area mutation, Compose network disconnection and declared
SoftwareSpec fault profiles. The compiler creates a bounded `benchmark6`
dummy interface under `2001:db8::/32`, enables the real SEED OSPF layer, maps
Compose attachments to project-scoped runtime network names, and copies only
validated software profile metadata. Bundle still performs independent target,
impact and recovery checks.

# 声明式拓扑生成层

> [!IMPORTANT]
> **README_SYNC_REQUIRED（强制联级同步）**：修改本目录 `.py` 时必须更新本 README 和
> `generator/README.md`；修改 `examples/` JSON 时必须逐级更新示例、本层和根 README。
> capability manifest、软件或故障绑定变化还要同步 Bundle、Fault 或 NL README。

## 当前实现状态（2026-08-26 审计）

本层当前 CLI 为 `plan/register/compile/validate/smoke/bind/test/preflight/inventory`。支持
tree、ring、mesh、random_connected 和 explicit 拓扑，确定性分配 ASN、LAN/IX/loopback
地址，执行资源预算与连通性检查，编译 SEED/Compose 产物，并生成软件、故障、测试可消费的
capability manifest。`nl-scene-generate` 只交付该 manifest，不启动 Docker；统一任意 NL
路径则使用独立隔离 Compose IR，不冒充本层受控 capability。

本层负责把 `TopologyRequest` 转换为经过预算、地址、ASN 和连通性检查的确定性
`TopologyPlan`，再适配 SEED Emulator 编译为 Docker Compose，并发布故障系统可消费的
capability manifest。

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
## 运行时隔离与网络语义绑定（2026-08-26）

拓扑 capability manifest 现在发布 `compose_project`。每个
`docker_network_disconnected` 绑定除网络、接口和本机地址外，还包含同一二层
网络内的 `peer_container` 与 `peer_ip`。Bundle 隔离器把基础 project、
容器和静态 IPv4 地址重绑定到本次 session；接口和对端拓扑关系保持不变，
IP 的主机位在新的非重叠子网中保持一致。

该对端绑定用于 `probe.docker_network_path`：恢复时必须同时证明 Docker
attachment 存在、声明接口持有正确地址，并能从目标容器到达编译期选择的
对端。它把拓扑级能力清单与数据面语义恢复连接起来。

`assets[].service` 是并行运行时的稳定间接标识；`assets[].container` 仅代表
基础编译产物中的容器名。Bundle 隔离器启动 session 后根据 Compose service
标签替换后者，并同步替换 fault binding 中的所有容器与对端引用。拓扑编译器
不接受由请求或 LLM 提供的运行时容器名。

容器控制目标继续使用发现到的真实运行时名称，容器内 hostname 探针通过
`runtime_session.container_services` 使用短 service 别名。由此既保持绑定
检查的资产归属语义，也避免长 Compose project 名超过 DNS label 限制。

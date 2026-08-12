# 声明式拓扑、四故障与无 AI 生命周期验收报告

## 结论

生成器已形成可运行闭环：声明式拓扑请求经过确定性规划、资源预算、地址/ASN 分配和连通性校验后由 SEED Emulator 编译；生成场景复用原安全门禁与盲测观测；规则代理在不调用 AI 的条件下完成四种单故障及一种双故障组合的注入、检测、修复、复验和清理。

## 实现范围

- 拓扑模型：AS 数量、每 AS 主机数、ring/full-mesh/chain/star/explicit 边、额外确定性边、地址池、ASN 起点、平台和资源预算。
- 规划门禁：容器、网络、链路、AS、内存、CPU 上限；分配与 fingerprint 漂移时 fail closed。
- 编译适配：SEED Emulator Base/Routing/eBGP，稳定 Compose 项目名，`nat-unprotected` 网关模式，Unfiltered 多跳路由传播，能力清单和故障绑定。
- 四种故障：容器停机、DNS nameserver 篡改、BIRD ASN 错配、scoped transit ACL。
- 组合故障：独立 BIRD ASN + scoped ACL，同点双故障、确定注入顺序、逆序清理。
- 安全门禁：健康基线、注入有效性、修复授权、blind observation 隔离、修复后验证、清理后验证、生成契约哈希。
- 构建可靠性：逐服务串行调度，BuildKit 内容缓存复用，支持离线 VM，避免大 Compose 并发构建竞态。

## 真实无 AI 验证

执行入口均为 `--agent rule --validate-only --reuse-running`；没有运行 MIMO 或任何外部 AI 调用。

| 场景 | 故障 | 结果 |
|---|---|---|
| `gen_container_stopped_9b2b4ac316_01` | 容器停机 | 修复验证通过 |
| `gen_dns_nameserver_fac593b874_01` | DNS nameserver | 修复验证通过 |
| `gen_bird_wrong_asn_9695fab1eb_01` | BIRD ASN | 修复验证通过 |
| `gen_random_complex_transit_acl_25af448cd5_01` | scoped ACL | 修复验证通过 |
| `gen_random_complex_dual_bgp_acl_5b3d8d80cf_01` | BIRD ASN + scoped ACL | 两组件注入、逆序清理、修复验证通过 |

失败的旧组合指纹 `395e...` 是路由关系从 Peer 改成 Unfiltered 后协议名契约漂移的安全拒绝证据；修正为能力一致的 `x_as*` 后生成新指纹 `5b3d...` 并通过。

## 拓扑级验证

- `small_ring`：6 个业务资产、8 个 Compose 服务，LAN/IX/BGP/全 AS 对矩阵通过。
- `scale_100`：100 个业务资产、102 个 Compose 服务真实启动；4 个 LAN 网关探针、4 条 IX 链路、4 个路由各 2 个 Established 会话、6 个 AS 对端到端探针全部通过；测试后项目容器残留为 0。
- `scale_500`、`scale_1000`、`scale_10000`：均完成确定性规划和 SEED 编译；当前 15 GiB/8 vCPU VM 的运行前门禁分别因资源/容器硬上限拒绝，没有冒险启动。
- 10,000 节点计划：50 AS、10,002 Compose 服务预算、643,200 MiB、502.5 CPU；证明生成能力，不声称当前 VM 可承载运行。

## 盲测观测

运行中的声明式小环由能力清单驱动选择路由器和每 AS DNS sensor，不依赖场景答案。最终证据为 `declarative_capability_driven` profile、39 个主动探针、102 条观测。超过 500 资产时切换为有界采样 profile，防止观测成本线性失控。

## 回归与残留

- `benchmarks/tests/test_*.py` 共 9 个脚本全部通过。
- 声明式 `decl_small_ring` 和 `decl_scale_100` 项目最终均为 0 容器残留。
- 原有非声明式拓扑及 `examples/` 的用户改动未修改、未清理。

## 证据文件

- `reports/TOPOLOGY_SCALE_100_SMOKE.json`
- `reports/TOPOLOGY_SMALL_RING_MATRIX.json`
- `reports/TOPOLOGY_SCALE_{100,500,1000,10000}_PREFLIGHT.json`
- `reports/DECLARATIVE_SMALL_RING_BLIND_OBSERVATION.json`
- `reports/FINAL_gen_*.md`
- `docs/DECLARATIVE_TOPOLOGY_GENERATOR.md`

## 已知边界

当前声明式模型提供常用图策略与显式边，不是任意 SEED layer/service 的通用 DSL；10,000 节点已经生成和编译，但其真实运行需要容量足够的宿主机或分布式执行后端。此边界由 preflight 明确阻断，不会退化为“生成即声称可运行”。

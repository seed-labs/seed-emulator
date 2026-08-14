# Multi-Agent BenchmarkBundle v1 设计与工作流

## 目标

这一层让不同 Agent 分别生产拓扑、软件、服务、工作负载、故障、测试、
Oracle 和评分产物，再由无 AI 的确定性编译器把它们组合为一个可审计的
Benchmark。Agent 不通过自由文本共享隐式状态，只交换带输入指纹的
`AgentArtifact v1`。

## 十二步实现映射

| 步骤 | 实现 |
|---|---|
| 1. Bundle 契约 | `models.py`、`specs.py`、`compiler.py` |
| 2. Agent 产物协议 | `artifacts.py`，原子存储与 SHA-256 来源证明 |
| 3. Coordinator | `coordinator.py`，DAG、租约、重试、恢复、外部 claim/complete/fail |
| 4. 应用与工作负载 | `ServiceSpec`、`WorkloadSpec`，HTTP/DNS/TCP/UDP/ICMP Driver |
| 5. 测试与 Oracle | `TestSpec`、`OracleSpec`、独立断言执行 |
| 6. 插件 SDK | `plugins.py`，版本、平台、能力、修改面、盲测与抽样声明 |
| 7. 故障平台统一 | 十个场景模板均有 FaultDriver 适配，多目标和时限恢复 |
| 8. 跨产物审查 | `security.py` 与编译器中的目标、能力、覆盖和冲突门禁 |
| 9. 公私拆包 | `BlindPolicy` 与 `public_bundle`/`private_bundle` |
| 10. 生命周期 CLI | `cli.py` 的 compile/review/validate/split/run/qualify |
| 11. Pilot | `pilot.py` 与 `validate_multi_agent_pilot.py` |
| 12. 分级规模验证 | `scale.py`，5/20/100/1,000/10,000 规划验证 |

## AgentArtifact 协议

每个外部 Agent 输出：

```json
{
  "schema_version": 1,
  "artifact_type": "service",
  "artifact_id": "web_services_v1",
  "producer": "service_agent",
  "input_fingerprints": ["<sha256>"],
  "capabilities_required": ["http.nginx.v1"],
  "payload": {"services": []},
  "warnings": [],
  "artifact_fingerprint": "<sha256>"
}
```

`input_fingerprints` 必须与 Coordinator 提供的输入完全相等。Artifact Store
默认不可覆盖；内容相同的重复提交是幂等操作，内容不同则拒绝。

## 外部 Agent 协作流程

1. 管理端用 `coordinate-init` 注册任务 DAG。
2. Agent 使用 `coordinate-claim --worker-id ...` 获取一个带租约的任务。
3. Agent 读取返回的输入 Artifact，不读取其他 Agent 的私有文件。
4. Agent 生成并签名输出 Artifact。
5. Agent 使用 `coordinate-complete` 提交；失败时使用 `coordinate-fail`。
6. Coordinator 验证租约、产物类型、ID 和输入指纹后原子发布。
7. Coordinator 或人工重启后，`coordinate-status` 回收过期租约。

## Bundle 编译门禁

编译器要求：

- 恰好一个已注册声明式拓扑；
- 软件、服务和 Probe 目标存在；
- 服务要求的能力实际安装在每个目标上；
- 工作负载指向已声明服务；
- FaultSpec 能在 Capability Manifest 上安全编译；
- 每个 `must_break` 和 `must_preserve` 都有 active 测试；
- 每个 `must_break` 都有 recovery 测试；
- Oracle 和评分只能引用已有测试；
- Public Bundle 不包含故障、答案、注入或恢复字段；
- 产物、拓扑和最终 Bundle 都有独立指纹。

## 生命周期

正式 Docker 生命周期固定为：

```text
服务就绪 → 工作负载预热 → baseline tests
→ FaultExecutor 注入并验证 → active tests
→ 逆序恢复 → recovery tests → 清理证据
```

运行前自动恢复能够匹配计划指纹的未完成 Journal。正式晋级要求至少两份
独立、默认盲测、无 AI、真实 `DockerLifecycleRunner` 收据。模拟 Pilot 只能
得到 `pilot_qualified`，绝不会被标记为正式晋级。

## 真实应用 Pilot 晋级证据

应用层 Pilot 现在同时保留快速的合约模拟验证和正式 Docker 验证。真实场景由
`generator/topology/examples/multi_agent_application_pilot.json` 声明，安装 Nginx、
BIND9、PostgreSQL 与独立观察端工具。`pilot.py` 从编译后的 capability manifest
绑定真实容器与地址，不依赖硬编码的 Compose 服务名。

正式生命周期使用 HTTP、DNS、PostgreSQL TCP 三类应用协议探针，组合注入三个
独立 `container.stopped` 故障，并验证观察端 `must_preserve`。恢复阶段先按故障
Journal 逆序恢复容器，再幂等协调服务就绪，最后重复协议级测试。2026-08-14 的
两轮真实、盲测、无 AI Docker 执行均通过，签发 `qualified` 记录；证据位于
`reports/MULTI_AGENT_APPLICATION_PILOT_REAL/`。合约模拟仍只能签发
`pilot_qualified`，不会冒充正式证据。

可重复验证命令：

```bash
python3 -m generator.topology.cli smoke \
  --topology-id multi_agent_application_pilot --keep-running
python3 tests/validate_real_multi_agent_pilot.py
```

## CLI

```bash
python3 -m generator.bundle.cli plugins
python3 -m generator.bundle.cli artifact-put --artifact A.json --store artifacts
python3 -m generator.bundle.cli coordinate-init --tasks tasks.json --store artifacts --state state.json
python3 -m generator.bundle.cli coordinate-claim --store artifacts --state state.json --worker-id topology_agent_1
python3 -m generator.bundle.cli compile --spec bundle.json --store artifacts --output compiled.json
python3 -m generator.bundle.cli review --bundle compiled.json
python3 -m generator.bundle.cli split --bundle compiled.json --public-output public.json --private-output private.json
python3 -m generator.bundle.cli run --bundle compiled.json --capabilities topology_manifest.json --journal-dir journals --output receipt.json
python3 -m generator.bundle.cli qualify --bundle compiled.json --receipt run1.json --receipt run2.json --output qualification.json
python3 -m generator.bundle.cli scale-validate --bundle compiled.json --output scale.json
```

## Pilot 与规模证据边界

三应用 Pilot 声明 Nginx、BIND9 和 PostgreSQL 服务、对应工作负载、三个独立
容器故障、`must_preserve` 观察者、基线/生效/恢复测试及加权评分。仓库内
Pilot 使用模拟运行器验证编译、协调、故障状态机和证据格式，不启动容器，
因此只产生 `pilot_qualified`。

100 节点真实 SEED 拓扑证据继续由
`reports/TOPOLOGY_SCALE_100_SMOKE.json` 提供。1,000 和 10,000 节点仍然只做
规划、性能与抽样验证，不能解释为已在当前 VM 全量部署。

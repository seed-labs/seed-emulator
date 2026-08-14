# Production Benchmark Generator v1

## 目标

这一层把已有的确定性 Bundle、故障平台和生命周期提升为一个可直接使用的生成
Agent：调用者提交一份 `BenchmarkRequest v1`，生成器运行九类 Worker、编译并
审查产物、拒绝歧义或重复场景、执行规模检查，并在获得正式 qualification 后
分离发布公共题面和私有答案。

核心入口：

```bash
cd /home/zvanadium/seed-emulator/benchmarks
python3 -m generator.bundle.cli generate \
  --request generator/bundle/examples/production_application_request.json \
  --capabilities generated/declarative/multi_agent_application_pilot/output/topology_manifest.json \
  --workspace reports/PRODUCTION_APPLICATION_GENERATION
```

生成过程不执行自由文本或 Agent 生成的宿主机命令。Agent 只输出受版本化 schema
约束的 `AgentArtifact`，Bundle 编译器和已有 FaultDriver 才能把声明转换为执行
计划。

## 六组能力

### 1. BenchmarkRequest 和一键入口

`request.py` 定义严格的 `BenchmarkRequest v1`，包含目标、应用模板、拓扑、规模、
难度、故障数量、种子、执行和发布策略。未知字段、路径穿越、非法规模、故障数
超过应用数都会在任务生成前被拒绝。

`generate` 可以安全重入。Coordinator、ArtifactStore、QualityIndex 和 BuildCache
都使用不可变指纹；崩溃后再次调用同一请求会复用完成的任务和相同 Bundle。

### 2. 九类 Worker

`workers.py` 提供：

1. TopologyAgentWorker
2. SoftwareAgentWorker
3. ServiceAgentWorker
4. WorkloadAgentWorker
5. FaultAgentWorker
6. TestAgentWorker
7. OracleAgentWorker
8. ScoringAgentWorker
9. SafetyReviewerAgentWorker

内置模式由 `generate` 在同一受控进程执行。分布式 Agent 使用 `worker-run`，并通过
按角色过滤的 Coordinator lease 领取任务。Coordinator 会核对 Artifact 类型、ID、
精确输入指纹和租约，错误角色无法误领任务。

### 3. 应用语义模板

`templates.py` 提供版本化 `ApplicationTemplate v1`。模板声明软件 ID、能力、apt
包、端口、幂等启动、真实健康探针、工作负载、测试探针、观察源和安全候选故障。
内置模板覆盖 Nginx、BIND9、PostgreSQL 和独立网络观察端。

模板 argv 是数组且每个元素都禁止 shell 控制字符；扩展模板可以通过 registry
加载 JSON，但不能注入 shell 程序。未知软件仍应显式增加模板或使用已有
`SoftwareSpec`/FaultDriver 插件，生成器不会猜测未知软件语义。

### 4. 自动质量门禁

`quality.py` 实现：

- 按 Driver、资产和 expectation 的确定性故障组合选择；
- `must_break` 可观测与可恢复检查；
- `must_preserve` 覆盖检查；
- 根因 expectation 唯一性；
- 故障数量和请求一致性；
- 基于规模、Driver 多样性、资产多样性、交互和观察通道的难度分；
- easy/medium/hard/expert 难度区间校准；
- 场景签名和 QualityIndex 去重。

质量失败会终止生成，不能进入 lifecycle 或发布。

### 5. 评分、版本和发布

`publishing.py` 的评分维度为诊断、修复、功能测试、时间效率、副作用和操作经济性。
每份 ScoreCard 有独立指纹。

正式发布要求：

- Bundle 编译安全通过；
- QualityReport 通过；
- qualification 状态为 `qualified`；
- 版本符合 SemVer；
- 同一 benchmark/version 不可变。

公共 Bundle 以 `0644` 写入 public root，私有答案以 `0600` 写入完全分离的 private
root。ReleaseRegistry 记录两侧 SHA、Bundle/契约/质量/qualification 指纹。

### 6. 分布式规模生产

`scheduler.py` 提供带原子状态锁的持久化队列、资源等级、规模上限、租约、重试、
过期回收和 quarantine。`ProductionWorkerRuntime` 只接受
`benchmark.generate` 数据任务，不执行任意 command，并把所有输入和工作目录限制
在管理员批准的 root 下。

BuildCache 采用输入内容寻址，缓存条目不可变且带校验指纹。CI matrix 固定为：

| 规模 | 模式 | 建议周期 |
|---:|---|---|
| 5 | real_full | per commit |
| 20 | plan_full | per commit |
| 100 | real_full | nightly |
| 1,000、10,000 | plan/performance/sampled | weekly |

1,000 和 10,000 不会在当前 VM 被错误标记为全量部署。

## 端到端数据流

```text
BenchmarkRequest
  -> 九角色 AgentTask DAG
  -> AgentArtifact Store
  -> lifecycle policy
  -> BundleCompiler + contract SHA
  -> QualityReport + duplicate index
  -> 5/20/100/1,000/10,000 scale report + cache
  -> optional real no-AI lifecycle + qualification
  -> optional public/private immutable release
```

## 外部 Worker 与生产队列

外部角色 Worker：

```bash
python3 -m generator.bundle.cli worker-run \
  --request request.json --capabilities topology_manifest.json \
  --store artifacts --state coordinator.json \
  --role service_agent --worker-id service_worker_01
```

生产 Worker：

```bash
python3 -m generator.bundle.cli schedule-run \
  --scheduler scheduler.json --allowed-root /srv/benchmark-jobs \
  --worker-id worker_01 --resource-class medium --max-scale 100
```

## 证据边界

合约测试可以证明生成、恢复、质量、评分、发布和调度控制面。正式 Benchmark 发布
仍必须有至少两次真实 Docker、盲测、无 AI、未污染的 lifecycle receipt；计划型或
模拟型测试不会自动升级为正式 qualification。

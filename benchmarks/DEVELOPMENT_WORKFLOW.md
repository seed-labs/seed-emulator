<!-- README_SYNC_REQUIRED -->

# Benchmark Agent 长期开发工作流

本文件是 `<seed-emulator-repo>/benchmarks` 新架构的实施约束。所有后续 Agent 在修改代码前必须先读
`benchmarks/AGENTS.md`、`benchmarks/README.md` 和本文件，并在实现变化时同步三者。

## 固定目标链

```text
NL / 结构化 BenchmarkRequest
→ 可选的 SEED 拓扑物化（全部 Docker 操作经 Agent Tool Service API）
→ 健康 RuntimeContext
→ Benchmark Agent 生成 BenchmarkPlan(state=draft)
→ 确定性编译和安全门禁
→ 基线 → 注入 → 故障验证 → 作者恢复 → 恢复验收
→ RuntimeBenchmarkBundle
→ 沙箱 Adapter → 被测 Agent → Adapter API trace
→ EvaluationRecord / ScoreReport
```

只读采集、故障设计、测试与恢复方案编译可以并行；同一 runtime target 的状态变更必须按持久化事件顺序
执行。Planner 和被测 Agent 均不得直接使用 Docker CLI、SDK、Socket、宿主 Shell 或 Tool Service 管理身份。

## 最少实现类型

只手写六个顶层模型：`BenchmarkRequest`、`RuntimeContext`、`BenchmarkPlan`、`ExecutionEvent`、
`RuntimeBenchmarkBundle`、`EvaluationRecord`。其余合同使用这六个文档中的字段和 JSON Schema `$defs`，
不得为流程图的每条连线创建类。

## 每个增量的顺序

1. 写清一个可验证的用户行为和失败条件。
2. 更新版本化 Schema、能力清单和安全预算。
3. 先实现确定性编译、绑定和拒绝路径。
4. 如需 Docker 能力，在 `seedemu-agent-tools` 的独立分支实现最小结构化工具；禁止通用 Shell 工具。
5. 为工具增加参数校验、project/session 绑定、前后状态、幂等键和恢复收据。
6. Benchmark 侧只通过 HTTP API 客户端调用工具。
7. 运行单元测试、API 契约测试、安全负例和真实 Docker 生命周期。
8. 同步代码目录及所有祖先 README，执行 README 覆盖门禁和 `git diff --check`。
9. 保存不含密钥的请求、计划、事件、Bundle、API trace、运行输出和内容指纹。

## 分层结构（Phase 0/1/1.5 落地）

```text
benchmark_agent/                应用层（出题侧）
├── cli.py                      表现层：run / nl-plan / nl-runtime-plan / runtime-projects 入口
├── models.py                   领域层：六个顶层模型
├── workflow.py                 应用层：物化 + 资格验证 + session/grant 编排 + 清理
├── evaluation.py               应用层：经 Adapter 的原生候选评测循环
├── inspect_runner.py           应用层：Inspect AI 工具循环与可重放 transcript
├── journal.py                  基础设施：append-only 事件日志（增量落盘）
├── scenario.py                 基础设施：场景文件加载与严格校验（单一场景数据来源）
├── config.py                   基础设施：candidate 模型配置（加载 config.json）
├── api.py                      基础设施：Tool Service HTTP 客户端
└── providers/                  基础设施：被测 Agent 接入协议（base / openai_compat，vendor 配置见 config.json）

scenarios/                      数据层：场景 JSON（拓扑、故障、动作合同、提示词、评分、命名）
└── b00_dns.json                当前唯一场景：B00 DNS resolver failure

benchmark_adapter/              沙箱层（评测期独立服务）
├── app.py                      FastAPI：动作白名单、转发、脱敏
├── grants.py                   grant spec 校验与本地策略（纯函数，可单测）
├── trace.py                    JSONL 动作轨迹
├── Dockerfile / compose.yaml   candidate 沙箱网络隔离（internal network）
└── __main__.py                 进程入口（--grant-spec / --port）

Tool Service（受信执行面）
├── api/routes/tools.py         Bearer grant 服务端授权（403 grant_violation）
├── tools/benchmark/            session / grant / 持久化状态 / 漂移检测
└── backends/docker.py          Docker 唯一操作路径
```

依赖方向：表现层 → 应用层 → 基础设施/领域层；沙箱层与执行面仅经 HTTP 授权链路交互；被测 Agent 与执行面无任何直连路径。

## 场景驱动的故障生命周期

持久化输入合同与代码文档分离：`scenarios/README.md` 是场景 JSON 的权威文档；本文件和
`benchmark_agent/README.md` 只维护实现工作流。`run_runtime_benchmark` 不得包含故障类型分支，而应执行
Scenario 声明并经 Tool Service 校验的 probe/inject/recover 工具。当前驱动覆盖 DNS resolver、container
stop、iptables OUTPUT drop 与 tc/netem。新增驱动不得在 workflow 中新增分支。

## 首个参考拓扑：B00

首个验收切片固定使用 B00 Mini Internet 的抽象结构，但 B00 不是系统中的硬编码拓扑：

1. 读取 B00 `example.yaml` 并固定来源指纹。
2. 通过 Tool Service 绑定或物化独立 Compose project。
3. 通过 Tool Service inventory 选择一个稳定 service ID。
4. 建立 DNS 基线，注入可逆的 resolver failure，并验证故障确实存在。
5. 由 MIMO 作为被测 Agent（仅为第一个接入示例），只通过 Adapter 暴露的结构化 API 进行观测与修复。
6. 根据 Adapter API trace、Tool Service receipts、故障态与恢复态探针生成评分。
7. 作者侧再次恢复或清理，证明环境没有残留污染。

## 被测 Agent 通用接入

评测目标是任意第三方 Agent 的网络问题修复能力，不绑定特定模型或供应商。MIMO 只是首个接入示例。
当前已提供 Inspect AI harness：Inspect 负责标准模型 Provider、工具循环和 transcript，四个 Inspect 工具只
包装 Adapter action；Adapter 继续负责 grant、目标绑定、脱敏和 API trace。新增模型必须复用同一
Adapter、Grant 与确定性评分合同，不得向 Inspect 注册 Shell、文件、Docker、Tool Service 或宿主执行工具。
MCP 形式的外部完整 Agent 接入仍是后续兼容目标。

## 完成门禁

- API key 只能来自环境变量（由 `config.json` 的 `api_key_env` 指定变量名），任何 artifact、异常和日志都不得包含密钥。
- 结构化输入和 MIMO 输出均须严格 Schema 校验；不合法输出不能触发工具调用。
- 目标只能从当前 Compose project 的服务端 allowlist 解析，客户端不能提交任意容器 ID。
- 所有 Docker 读取和写入均在 Tool Service receipts 中可追踪。
- DNS 注入、故障验证、MIMO 修复、恢复验收和最终清理必须各有真实运行证据。
- MIMO 无法访问 Docker Socket、Docker daemon 或 Tool Service 管理接口。
- 单元测试、API 测试、真实 B00 生命周期与 `git diff --check` 全部通过后才算完成。

# 多厂商 MCP 自然语言翻译层：设计与开发流程

## 目标

允许 Generator 通过统一 MCP Tool 接入多个模型厂商，把自然语言翻译成严格的声明式 benchmark
场景。LLM 只参与翻译；所有决定执行范围的事实都由本地能力快照、Schema、安全门禁、资源预算、
FaultDriver 和确定性编译器裁决。

MCP 不是统一的模型推理协议，因此本实现使用项目维护的单用途 Provider Gateway：Gateway 对外实现
同一个 MCP Tool，对内调用 MiMo 或任意 OpenAI-compatible 厂商原生 API。厂商适配不会进入拓扑、
故障或生命周期代码。

## 工作流

1. `nl-scene-plan` 检查原始自然语言并建立只读 Session。
2. 固化 Prompt、Scene Schema、能力目录、资源策略和 seed。
3. `MCPProvider` 从受信 profile 选择 Gateway；可选备用 profile 只处理传输故障。
4. 客户端与 Gateway 协商 MCP `2025-06-18`，并检查唯一 Tool 及其 Schema 指纹。
5. 调用 `translate_benchmark_scene`，Gateway 使用厂商原生结构化输出能力。
6. Gateway 返回 `structuredContent`，但该结果仍被视为不可信。
7. Generator 检查 Contract、请求绑定、响应指纹和最终 Scene JSON Schema。
8. 现有流程继续执行歧义、未知能力、地址/ASN、连通性、资源和故障能力检查。
9. 合法 Intent 确定性编译为 `TopologyRequest + BenchmarkRequest`；非法结果 fail closed。
10. plan-only 输出预览和一次性审批，不编译 SEED、不改变 Docker 状态。
11. 独立 `nl-scene-generate` 重新验签并交付 `Topology capability manifest`。
12. 后续九 Worker 与无 AI 生命周期不再调用模型，并保持 `ai_invoked=false`。

## 路由规则

支持显式 profile 和传输故障 fallback。不得把模型投票作为安全决策来源。

| 失败类型 | 是否 fallback | 结果 |
|---|---:|---|
| Gateway 无法启动、超时、断连 | 是 | 尝试下一受信 profile |
| 上游 HTTP 429 或 5xx | 是 | 尝试下一受信 profile |
| MCP 协议或 Tool Schema 不匹配 | 否 | 拒绝 |
| Contract、Scene Schema 或指纹失败 | 否 | 拒绝 |
| 未知能力或信息不足 | 否 | 扩展提案或澄清 |
| 资源、安全或策略拒绝 | 否 | 拒绝 |

## 威胁模型

MCP Server、厂商 API 和模型输出均属于不可信边界。主要风险包括提示注入、额外字段、伪造 Tool、
响应重放、超大/深层 JSON、Schema 降级、凭据泄露、fallback 绕过、任意子进程和模型直接执行。
对应控制包括：输入安全检查；固定 Tool/Schema；请求与响应指纹；本地双重验证；消息、stderr、超时
上限；受信内置 profile；无 shell 子进程；环境变量凭据；非传输错误禁止 fallback；MCP 不暴露执行
工具；最终审批与生命周期继续使用原有安全边界。

## 开发阶段与状态

| 阶段 | 交付物 | 状态 |
|---|---|---|
| 1 | 冻结 `benchmark-scene-mcp-v1` Contract | 已实现 |
| 2 | 建立不含密钥的 Provider Profile | 已实现 |
| 3 | MCP stdio 客户端和协议协商 | 已实现 |
| 4 | 单用途参考 Gateway | 已实现 |
| 5 | MiMo 与 OpenAI-compatible 厂商 Adapter | 已实现 |
| 6 | Contract、指纹和本地 Scene Schema 双重验证 | 已实现 |
| 7 | 只对传输错误生效的 fallback | 已实现 |
| 8 | CLI、缓存身份和 Session 审计 | 已实现 |
| 9 | 假 Gateway/确定性 MCP 集成测试 | 已实现 |
| 10 | MiMo 真实 MCP 冒烟测试 | 已验证 |
| 11 | 全量 NL 与 README 回归 | 已验证 |
| 12 | 远程集中式 Gateway | 非当前边界；需要独立认证与运维 ADR |

## 完成标准

- 同一个 `MCPProvider` 能连接 MiMo 和任意 OpenAI-compatible Gateway profile。
- 至少以 MiMo 完成一次真实 `nl-scene-plan` MCP 调用；其他真实厂商按用户授权免测。
- 厂商差异不进入 Intent、拓扑、故障或生命周期编译代码。
- 所有 MCP 返回值经过本地 Contract、JSON Schema 和安全门禁。
- MCP Gateway 没有 Docker、Shell、文件写入、故障注入或发布工具。
- 未知能力进入扩展提案，信息不足进入澄清，资源或安全越界 fail closed。
- fallback 不能绕过协议、Schema、安全或预算拒绝。
- `nl-scene-plan` 默认不改变 Docker 状态。
- 规范化 Intent 和 seed 可确定性编译为等价 manifest 计划。
- Session 保留 Prompt、模型、profile、MCP Contract、能力目录、Intent 和编译指纹。
- API 密钥不进入仓库、命令行、缓存、日志和报告。
- 下游无 AI 生命周期仍不调用模型。
- MCP 专项、NL 场景、README 和完整 Generator 回归全部通过。

## 当前限制

当前只启用本地 stdio Gateway。这是刻意的最小攻击面选择，不影响多厂商接入；不同厂商通过不同
profile 启动相同受审 Gateway。集中式 Streamable HTTP MCP 需要单独实现 OAuth/主机 allow-list、
TLS、重定向限制、多租户凭据隔离、网络出口策略和运维审计，不能仅把 URL 加入现有 CLI。

## 2026-08-25 验收记录

真实 MiMo MCP Session 位于：

```text
reports/nl_sessions/mcp_mimo_real_20260825_ready
```

结果为 `status=ready`、`provider=mcp:mimo`、`provider_invoked=true`、
`provider_cache_hit=false`、`validation_attempts=1`。MCP stdio Gateway 调用
`mimo-v2.5-pro`，耗时 12,424 ms，使用 1,847 input、468 output、2,315 total tokens；
审计记录显示没有 fallback。

模型产生 3 AS、每 AS 2 host 的 mesh，分别放置 nginx、bind9 和受保护 observer，绑定
`network.netem` 与 `container.stopped`。本地确定性规划得到 11 containers、6 networks、
768 MiB、0.6 CPU、3 links；地址/ASN、应用与 observer 隔离、FaultDriver、资源预算检查均通过。
预览明确记录 `plan_only_no_docker_state_change`、`execution_authorized=false`、
`publication_authorized=false`，未运行 `nl-scene-generate`。

专项测试覆盖正常 MCP、传输 fallback、协议错误不得 fallback、Plan-only 和 Session 审计。随后运行
全部 `tests/test_*.py`、`compileall`、benchmark `--list`、NL CLI 参数检查、README 门禁、密钥扫描和
`git diff --check`，均通过。其他真实厂商测试按用户要求免除；`openai-compatible` profile 与同一
Gateway/Contract 已实现并由确定性、失败与路由测试覆盖公共路径。

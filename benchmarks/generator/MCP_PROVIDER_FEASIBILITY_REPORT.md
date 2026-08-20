# Generator 外部模型 MCP 化可行性报告

日期：2026-08-20

范围：只读审计 `benchmarks/generator/` 现有实现并评估以 MiMo 为代表的外部模型接入方式；本报告不实现 MCP、不改变运行代码或依赖。

## 1. 结论

技术上可行，建议分阶段实施，但不建议把当前 `MiMoProvider -> Chat Completions API` 直接改成 MCP
Sampling。

推荐目标是增加 `MCPProvider`，让 Generator 作为 MCP client 调用一个受信的、单一用途的 Provider
Gateway tool；Gateway 在服务端继续调用 MiMo 或其他厂商 API，并返回候选结构化 JSON。Generator
现有 JSON、Schema、Intent、能力、安全、预算和确定性编译门禁全部保留，MCP 返回值仍视为不可信输入。

```text
Generator
  -> MCPProvider（MCP client）
  -> 受信 Provider Gateway 的 translate_scene tool
  -> MiMo / 其他厂商原生 API
  <- MCP structuredContent
  -> 现有严格 JSON + Draft 2020-12 Schema
  -> BenchmarkSceneIntent
  -> capability / policy / budget 门禁
  -> 确定性 TopologyRequest + BenchmarkRequest
```

综合评级：

| 维度 | 结论 |
|---|---|
| 技术可行性 | 高；现有 `LLMProvider.complete_structured()` 是明确替换点 |
| 安全可行性 | 中高；前提是 MCP 只替换 Provider 传输，不替换本地门禁 |
| 运维复杂度 | 中；远程 HTTP 模式需要服务身份、OAuth、WAF、可观测性和版本治理 |
| 短期收益 | 中；统一多厂商接入与审计，但比当前单一 HTTP adapter 更复杂 |
| 是否应立即全面替换 | 否；先增加可选 MCP Provider，保留 OpenAI-compatible/MiMo 回退 |

## 2. 关键概念澄清

MCP 主要标准化 AI 应用与外部资源、工具和上下文服务之间的协议，并不天然取代模型厂商推理 API。
MCP 2026-07-28 已将 Sampling 标记为 deprecated，官方给出的替代方向是直接集成 LLM provider API。
因此存在三种不同方案：

| 方案 | 含义 | 评价 |
|---|---|---|
| MCP Sampling | Generator MCP server 请求宿主替它调用模型 | 不推荐；新实现不应采用已弃用能力 |
| MCP Provider Gateway | Generator MCP client 调用一个封装厂商 API 的严格 tool | 推荐；MCP 管接入，厂商 API 管推理 |
| Generator MCP Server | 把 `catalog`、`nl-scene-plan` 等暴露给外部 MCP host | 可作为后续互操作层，但不等同于替换模型 API |

报告后续所称“MCP 化”均指第二种方案。

## 3. 当前实现审计

当前调用路径为：

```text
CLI --provider mimo
  -> MiMoProvider
  -> OpenAICompatibleProvider.complete_structured()
  -> POST /chat/completions
  -> ProviderResponse
  -> scene/session 再验证和编译
```

已具备、可以直接复用的边界：

- `LLMProvider` 已隔离厂商实现，调用方只依赖 `complete_structured(messages, output_schema, seed)`；
- `ProviderResponse` 已记录 provider、model、usage、延迟、响应指纹和验证尝试；
- 外部输出已执行大小、UTF-8、单 JSON object、重复键、深度、tool call 和本地 Schema 检查；
- `scene_session.py`、`session.py` 和 `unsafe_session.py` 已有 provider request/response/error 审计；
- LLM 只生成候选 Intent，不能签发审批、调用 Docker、构造 manifest 或绕过确定性编译；
- cache key 已绑定 provider/model/prompt/catalog/schema，可扩展绑定 MCP server/tool 身份。

当前缺口：

- 仓库没有 MCP client/server SDK 或协议实现；
- 没有 MCP endpoint、协议版本、server identity、tool 版本和 capability snapshot 契约；
- 没有 MCP transport 级超时、取消、重试、错误分类或审计字段；
- 没有远程 MCP OAuth/issuer/token audience 策略；
- 没有恶意 MCP server、tool catalog poisoning、协议降级或超大 structuredContent 测试；
- 当前 `pyproject.toml` 的 Black target 包含 Python 3.8/3.9/3.10，而官方 MCP Python SDK v2 要求
  Python 3.10+；VM 当前为 Python 3.12.3，运行上可用，但直接加入核心依赖会缩小现有工具链覆盖范围。

## 4. 推荐架构

### 4.1 MCPProvider client adapter

新增实现仍遵守现有接口：

```python
class MCPProvider(LLMProvider):
    def complete_structured(self, messages, output_schema, *, seed):
        ...
```

只允许调用固定 tool，例如：

```text
io.seedemu.benchmark/translate_scene_v1
```

tool 输入应只包含：

- prompt 版本和经过最小化的 messages；
-输出 JSON Schema 及其 SHA-256；
- seed；
-模型 allowlist 中的逻辑 model ID；
-请求、catalog 和能力快照指纹。

tool 输出只接受 MCP `structuredContent`，并由 tool `outputSchema` 描述。即使 MCP server 宣称输出已
符合 Schema，client 仍必须复用当前 `_strict_json_object`、Draft 2020-12 校验和后续领域门禁。
MCP `outputSchema` 是互操作契约，不是安全信任根。

### 4.2 Provider Gateway

Gateway 负责：

- 从自己的环境或 secret manager 读取 MiMo/其他厂商密钥；
- 将统一请求转换为厂商原生 API；
- 不向 Generator 暴露厂商密钥；
- 返回未经“智能修正”的候选 JSON与最小 usage 元数据；
- 固定厂商 base URL 和 model allowlist；
- 产生 server/tool/build 指纹和 trace ID。

Gateway 不应提供通用 HTTP、Shell、Docker、文件、资源读取或任意 tool passthrough。一个连接只允许
Provider tool，不能让模型自行选择其他 MCP tools。

### 4.3 传输选择

| 场景 | 推荐传输 | 原因 |
|---|---|---|
| 单机开发/CI | stdio | 不开放端口；凭据留在 Gateway 子进程环境；最小攻击面 |
| VM 内独立 sidecar | localhost Streamable HTTP | 进程隔离、可独立升级；必须仅绑定 127.0.0.1 |
| 集中式多厂商 Gateway | TLS Streamable HTTP | 支持统一治理；需要完整 OAuth、issuer/audience 和网关策略 |

建议以 MCP 2026-07-28 为目标版本。该版本使用无会话核心、`MCP-Protocol-Version`、`Mcp-Method` 和
`Mcp-Name` 自描述请求；若采用 SDK 自动兼容旧版本，生产配置仍应 pin 允许的协议版本，禁止静默降级到
未审计版本。

## 5. 安全模型

MCP 不会自动提供比当前 HTTP adapter 更强的安全保证。新增边界必须满足：

1. **Server allowlist**：固定 endpoint、TLS 身份、公钥/证书策略和 server identity；禁止用户文本指定 endpoint。
2. **Tool allowlist**：固定一个 Provider tool 名称和版本；忽略动态出现的其他 tools/resources/prompts。
3. **Schema pinning**：请求携带本地 Schema SHA-256；响应的 tool/outputSchema 指纹必须匹配审批前快照。
4. **双重验证**：MCP server 验证一次，Generator 本地再验证一次；任何不一致 fail closed。
5. **最小权限**：Provider tool 标记 read-only 仅用于说明；客户端不能信任 annotation，必须靠本地策略执行。
6. **无 tool chaining**：Gateway 不得让上游模型调用 MCP tool，也不得接受 tool/function call 结果。
7. **凭据隔离**：MiMo key 只在 Gateway；MCP bearer token 不能转发给上游模型或其他资源服务器。
8. **预算与限流**：保留响应大小、嵌套深度、token、超时和两次验证尝试上限；MCP 重试不得叠加成无限调用。
9. **审计关联**：记录 protocol、transport、endpoint identity、tool、server build、trace ID、Schema 指纹和结果指纹，不记录 token。
10. **网络保护**：远程 HTTP 验证 Origin、只允许 TLS、限制 DNS/重定向、禁止内网任意目标和 token passthrough。
11. **审批隔离**：MCP 只参与 plan；现有一次性 approval token、SEED 编译和无 AI 生命周期保持本地。
12. **故障隔离**：MCP 不可用、版本不匹配或输出异常只产生 `provider_error`，不能自动切换到更宽松 Provider。

## 6. 审计与数据模型调整建议

`provider_request.json` 建议增加：

```json
{
  "transport": "mcp_stdio|mcp_streamable_http",
  "protocol_version": "2026-07-28",
  "server_identity": "...",
  "server_build_fingerprint": "...",
  "tool_name": "io.seedemu.benchmark/translate_scene_v1",
  "tool_schema_sha256": "...",
  "request_trace_id": "..."
}
```

`provider_response.json` 建议增加：

- MCP JSON-RPC request ID 和 trace ID；
- tool result `isError`；
- structuredContent SHA-256；
- server/tool/schema 指纹匹配结果；
-协议/能力是否发生降级；
-传输重试与模型验证重试分别计数。

cache key 还应绑定 server identity、tool version、protocol version 和 tool schema 指纹；否则 Gateway 升级后
可能错误命中旧模型输出。

## 7. 实施顺序

### 阶段 0：契约冻结（1–2 人日）

- 定义 `MCPProviderConfig v1`、固定 tool input/output Schema 和错误分类；
- 决定 Python 3.10+ sidecar，避免改变 Generator 核心最低 Python 版本；
- 明确协议版本 pin 和回退策略。

### 阶段 1：无网络 PoC（2–3 人日）

- 实现 fake MCP transport 和确定性 Provider Gateway；
- 验证现有三条 NL 会话路径可以无改动消费 `MCPProvider`；
- 对等比较 HTTP Provider 与 MCP Provider 的规范化 Intent、指纹和状态。

### 阶段 2：stdio Gateway（3–5 人日）

- 使用隔离的 Python 3.10+ 环境和锁定版本的官方 SDK；
- Gateway 内调用 MiMo API；
- API key 仅进入 Gateway 环境；
- 加入子进程退出、stdout 污染、超时、取消和重启测试。

### 阶段 3：安全与回归（3–5 人日）

-覆盖恶意 tool list、错误 server identity、Schema 替换、重复键、超大/深层输出、tool call、协议降级；
-覆盖网络错误、MCP 错误、厂商错误和本地 policy rejection 的独立分类；
-运行现有自然语言、README 和完整 Generator 回归。

### 阶段 4：可选远程 HTTP（5–10 人日）

- TLS、OAuth resource metadata、issuer/audience 校验和 token 生命周期；
- Origin、DNS rebinding、重定向、代理、WAF、限流和 OpenTelemetry；
-故障演练与回滚到本地 HTTP Provider 的显式运维流程。

预计：本地生产可用 stdio 方案约 8–12 人日；远程集中式 Gateway 约 15–25 人日。估算不包含企业
身份系统接入和独立安全审计。

## 8. 验收标准

只有同时满足以下条件才可把 MCP Provider 标为可用：

- 相同 Provider Gateway build、model、prompt、catalog、Schema 和 seed 产生等价规范化 Intent；
- HTTP 与 MCP 两条路径进入同一 `BenchmarkSceneIntent` 和本地门禁，不存在 MCP 专用宽松路径；
-未知 tool、resource、prompt、server、协议版本和 outputSchema 全部 fail closed；
- MCP server 返回合法 JSON但公共地址、错误 ASN、断连图、越界选择器或超预算时仍被本地拒绝；
- MCP server 无法签发审批 token、启动 Docker、执行 Shell、调用生命周期或发布；
- API key、MCP token 和 Authorization header 不进入命令行、报告、cache 或错误消息；
-传输与模型验证重试均有独立硬上限；
- stdio 崩溃、HTTP 超时、401/403/429/5xx 和协议错误产生可审计 `provider_error`；
-全部现有 17 个测试文件通过，并新增 MCP 协议/攻击/回归集；
-真实 MiMo MCP Gateway plan 达到 `ready`，但 `docker_state_changed=false`；
-禁用 MCP 后原 `deterministic`、`mimo` 和 `openai-compatible` Provider 仍可使用。

## 9. 不推荐事项

- 不采用已弃用的 MCP Sampling 作为新模型调用主链；
- 不把 `nl-scene-generate`、Docker 或 Shell 作为第一阶段 MCP tool；
- 不信任 tool annotation、server-side outputSchema 或“readOnly”声明代替本地检查；
- 不让自然语言选择 MCP endpoint、tool 名、模型 base URL 或认证 scope；
- 不把整个 capability manifest、私有 oracle、审批 token 或修复答案发送给 Gateway；
- 不在 Generator 主进程中无版本上限安装 MCP SDK；
- 不删除现有直接 Provider，直到 MCP 路径通过长期回归和故障演练。

## 10. 最终建议

批准一个“并行可选、非替换式”的 MCP Provider Gateway PoC：保留现有 `MiMoProvider`，新增
`MCPProvider` 和隔离 stdio Gateway，以 plan-only 场景翻译为唯一功能。PoC 证明等价性、安全性和审计
完整性后，再决定是否引入远程 Streamable HTTP。

如果目标是让其他 Agent 使用 Generator，另行把 `catalog`、`nl-scene-plan` 和只读验证能力暴露为
Generator MCP server 更有价值；该方向应与“模型 Provider MCP 化”分成两个 ADR 和两个安全边界。

## 11. 依据与来源

仓库依据：

- `generator/nl/provider.py`：Provider 接口、MiMo/OpenAI-compatible adapter 和严格输出验证；
- `generator/nl/scene_session.py`：Provider 审计、Schema/安全/能力路由和 plan-only 会话；
- `generator/nl/scene_bridge.py`：确定性拓扑、预算、应用/观测器隔离和 manifest handoff；
- `generator/nl/cli.py`：Provider 选择和命令边界；
- `requirements.txt`、`pyproject.toml`：当前无 MCP 依赖及 Python 兼容声明。

外部一手资料：

- [MCP 2026-07-28 发布说明](https://blog.modelcontextprotocol.io/posts/2026-07-28/)：无会话核心、header 路由、授权强化，以及 Sampling 弃用并由直接模型 API 替代；
- [MCP 架构](https://modelcontextprotocol.io/specification/2025-06-18/architecture)：host/client/server 责任与 capability negotiation；
- [MCP Tools](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)：`inputSchema`、`outputSchema`、`structuredContent` 及客户端复验要求；
- [MCP Transport](https://modelcontextprotocol.io/specification/draft/basic/transports)：stdio、Streamable HTTP、Origin 和 DNS rebinding 防护；
- [MCP Authorization](https://modelcontextprotocol.io/specification/draft/basic/authorization)：OAuth resource metadata、authorization server discovery 和客户端要求；
- [官方 MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/blob/main/README.md)：v2 支持 2026-07-28，要求 Python 3.10+。

未发现 Xiaomi MiMo 官方提供可直接使用的 MCP 推理 endpoint；本报告因此假设由项目自建 Provider
Gateway 调用现有 MiMo OpenAI-compatible API，而不是假设厂商已经提供 MCP 服务。

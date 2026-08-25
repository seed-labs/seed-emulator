<!-- README_SYNC_REQUIRED -->

# MCP Provider Gateway

本层提供厂商无关、单工具、最小权限的 MCP 翻译通道。它既可服务推荐统一 `plan`，也兼容
`nl-plan`、`nl-scene-plan` 和 `nl-unsafe-plan`；MCP 不拥有 Docker 或 Shell 执行权限。

> [!IMPORTANT]
> **README_SYNC_REQUIRED（强制联级同步）**：修改本目录 `.py` 时必须更新本 README 和
> `generator/README.md`；若改变 Provider schema、profile 或 NL 数据流，还必须同步
> `generator/nl/README.md`。联级门禁由 `tests/test_generator_readmes.py` 强制执行。

## 数据流

```text
generator.nl CLI
 → MCPProvider
 → trusted MCPProfile
 → stdio MCPClient
 → local single-tool Gateway
 → vendor HTTPS structured completion
 → MCP result
 → NL 本地 JSON Schema / capability / policy / budget 检查
```

Gateway 的职责只是把 messages、output schema、seed 和模型配置发送给上游并返回结构化对象。
它不能审批、编译、启动容器、注入故障、评分或发布。

## 模块

| 模块 | 当前职责 |
|---|---|
| `contract.py` | MCP 请求、响应、错误和协议版本的严格合同 |
| `profile.py` | MiMo/OpenAI-compatible 受信 profile、模型、URL、环境变量和超时 |
| `client.py` | stdio 子进程、帧协议、超时、错误分类和审计 |
| `gateway.py` | 单翻译工具服务端及上游 HTTPS 调用 |
| `provider.py` | `LLMProvider` 适配、主 profile、限定 fallback 和审计元数据 |
| `__init__.py` | 公共导出 |

## 推荐使用

```bash
export MIMO_API_KEY='<runtime-only>'
python3 -m generator.nl.cli plan \
  --provider mcp \
  --mcp-profile mimo \
  --text "生成任意 benchmark，并包含故障恢复测试"
unset MIMO_API_KEY
```

兼容声明式 Scene：

```bash
python3 -m generator.nl.cli nl-scene-plan \
  --provider mcp --mcp-profile mimo \
  --text "生成6个AS的环形拓扑并注入DNS故障"
```

可选 fallback：

```text
--mcp-fallback-profile openai-compatible
```

只有进程启动、网络、429 或 5xx 等传输类失败允许 fallback。协议、JSON Schema、capability、
预算或安全策略拒绝必须 fail closed，不能换厂商重试绕过。

## 安全与审计

- profile 来自本地 allow-list，模型不能选择 endpoint、环境变量或 fallback。
- API Key 仅通过 profile 指定的环境变量进入 Gateway 子进程，不进入消息、响应、缓存或报告。
- MCP 返回仍由 NL 层执行单 JSON、重复键、大小、深度和 Draft 2020-12 Schema 校验。
- transport metadata、profile、模型、fallback、latency、usage 和 response fingerprint 进入会话证据。
- 推荐 `plan`、旧 `nl-*plan` 均默认 plan-only；执行需各自严格绑定的一次性审批。

## 验证

```bash
python3 tests/test_mcp_provider.py
python3 tests/test_unified_natural_language_generator.py
python3 tests/test_natural_language_scene_bridge.py
python3 tests/test_generator_readmes.py
```

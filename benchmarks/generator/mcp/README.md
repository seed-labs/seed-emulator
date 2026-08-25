<!-- README_SYNC_REQUIRED -->

# MCP Provider Gateway

本目录把多个模型厂商接到 Generator 的 `LLMProvider.complete_structured()` 边界。MCP 只替换
自然语言翻译的传输层；`BenchmarkSceneIntent v1` Schema、能力目录、歧义检查、资源预算、安全策略、
审批和确定性拓扑编译仍在 Generator 本地执行。MCP Gateway 没有 Shell、Docker、文件写入、故障注入、
生命周期或发布工具。

任何 Agent 修改本目录代码时，必须同步更新本 README；公共 CLI、Provider 接口或跨层数据流变化时，
还必须更新 `generator/nl/README.md` 和 `generator/README.md`，最后运行
`python3 tests/test_generator_readmes.py`。

## 数据流

```text
nl-scene-plan
  -> MCPProvider
  -> MCP 2025-06-18 stdio JSON-RPC
  -> translate_benchmark_scene
  -> trusted single-purpose Provider Gateway
  -> MiMo/OpenAI-compatible native API
  -> structuredContent
  -> local MCP contract validation
  -> existing local SceneIntent schema/security/budget gates
  -> deterministic TopologyRequest + BenchmarkRequest
  -> Topology capability manifest handoff
```

## 模块

| 文件 | 职责 |
|---|---|
| `contract.py` | `benchmark-scene-mcp-v1`、Tool 输入/输出 Schema、协议版本和指纹 |
| `profile.py` | 不含密钥的可信内置厂商 profile；只生成参数数组，不经过宿主 shell |
| `client.py` | 有界 MCP stdio 客户端、协议协商、Tool Schema 固定和错误分类 |
| `gateway.py` | 单用途 MCP Server；将 Tool 调用转给现有厂商 Provider |
| `provider.py` | `LLMProvider` 适配、二次本地验证、传输故障 fallback 和审计元数据 |

## 使用

MiMo 密钥只放入当前进程环境：

```bash
read -rs MIMO_API_KEY
export MIMO_API_KEY
python3 -m generator.nl.cli nl-scene-plan \
  --provider mcp \
  --mcp-profile mimo \
  --text "生成一个包含3个AS、每个AS 2台主机的环形网络，部署nginx并注入延迟故障"
unset MIMO_API_KEY
```

第二个已实现但不要求真实凭据验收的 profile 是 `openai-compatible`：

```bash
python3 -m generator.nl.cli nl-scene-plan \
  --provider mcp \
  --mcp-profile openai-compatible \
  --base-url https://provider.example/v1 \
  --api-key-env VENDOR_API_KEY \
  --model vendor-model \
  --text "..."
```

可选 fallback 只处理进程退出、超时、连接失败、HTTP 429/5xx 等传输/上游可用性问题：

```bash
python3 -m generator.nl.cli nl-scene-plan \
  --provider mcp --mcp-profile mimo \
  --mcp-fallback-profile openai-compatible \
  --text "..."
```

协议、Tool Schema、结构化输出、本地 Scene Schema、安全策略或预算拒绝永远不会触发 fallback。

## 安全与审计

- profile 只保存厂商、模型、环境变量名称、超时和非敏感 endpoint；不保存密钥值。
- Gateway 由参数数组启动，不使用 `shell=True`，当前只开放本地 stdio 传输。
- 客户端固定 MCP 协议版本、Tool 名称及输入/输出 Schema 指纹。
- 请求和响应均有大小限制；JSON 继续使用现有严格 UTF-8、重复键、NaN 和深度检查。
- Gateway 返回后，Generator 重新执行 MCP Contract 和最终 Scene JSON Schema 校验。
- 请求指纹防止响应跨 Session 重放；响应指纹防止 Intent 被替换。
- Session 记录 profile、协议、Tool Schema、实际厂商、fallback 尝试、usage 和 latency，不记录凭据。
- `nl-scene-plan` 保持 plan-only；真实 manifest 交付仍需要原有的一次性审批。

## 验证

```bash
python3 -m py_compile generator/mcp/*.py generator/nl/*.py
python3 tests/test_mcp_provider.py
python3 tests/test_natural_language_scene_bridge.py
python3 tests/test_generator_readmes.py
```

完整设计、开发顺序、威胁模型和完成标准见 `DEVELOPMENT_WORKFLOW.md`。

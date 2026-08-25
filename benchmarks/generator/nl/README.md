<!-- README_SYNC_REQUIRED -->

# Natural-Language Generator Gateway

本层把中文或英文需求转换为可审计 benchmark IR。LLM/MCP 只负责结构化翻译；本地代码负责
Schema、能力、预算、安全策略、审批、编译、执行和证据。

> [!IMPORTANT]
> **README_SYNC_REQUIRED（强制联级同步）**：修改本目录任意 `.py` 时，必须同时更新
> `generator/nl/README.md` 和 `generator/README.md`。若 Provider/MCP、Topology、Fault 或
> Bundle 合同受到影响，还必须更新对应层 README。`tests/test_generator_readmes.py` 会检查
> 本层到根层的完整祖先链，不再只检查同目录。

## 推荐统一入口

```bash
python3 -m generator.nl.cli plan \
  --provider mcp --mcp-profile mimo \
  --text "生成任意拓扑，安装所需软件，注入故障并测试恢复"

python3 -m generator.nl.cli generate \
  --plan reports/nl_sessions/<session>/benchmark_plan.json \
  --approval-token '<one-time-token>' \
  --acknowledge-arbitrary-code
```

`plan` 是唯一推荐的自然语言入口，默认 plan-only。输出包括完整 Compose、Dockerfile、场景
文件、Shell steps、资源预算、风险、指纹和一次性审批。`generate` 不再接收自然语言，只能执行
本 session 的已批准计划。

## 统一工作流

```text
text
 → inspect_natural_language
 → Provider/MCP strict structured response
 → duplicate-key/size/depth/Schema hardening
 → UnsafeScenarioPlan（arbitrary benchmark IR）
      topology = Compose networks/services
      software = Dockerfiles/files
      faults = inject/recover steps
      tests = baseline/observe/verify steps
 → compile_unsafe_policy
 → benchmark_plan.json + fingerprint + approval challenge
 → UnifiedNaturalLanguageExecutor
 → isolated Compose project
 → baseline → inject → observe → recover → verify
 → cleanup + evidence_manifest + scoring_preparation
```

五阶段顺序由模型合同和本地模型同时校验：baseline 必须早于 inject，observe（若存在）必须位于
inject 与 recover 之间，recover 必须早于 verify。旧 `exercise` phase 仅为历史计划兼容，不满足
统一工作流的 score-ready 条件。

## 当前 CLI

| 命令 | 作用 | Docker 状态 |
|---|---|---|
| `plan` | 推荐：生成任意 benchmark 并完成安全分析 | 不改变 |
| `generate` | 推荐：显式批准后隔离执行统一计划 | 改变后强制清理 |
| `nl-plan` | 兼容：已知能力 Intent → TopologyRequest/BenchmarkRequest | 不改变 |
| `nl-generate` | 兼容：批准 Intent 后运行生产 Bundle | 临时改变后清理 |
| `nl-scene-plan` | 兼容：任意声明式 Scene → 安全桥接预览 | 不改变 |
| `nl-scene-generate` | 兼容：注册/编译 topology capability manifest | 只写编译产物，不启动 Docker |
| `nl-unsafe-plan` | 兼容：原隔离任意代码计划 | 不改变 |
| `nl-unsafe-generate` | 兼容：原隔离执行器 | 临时改变后清理 |
| `catalog` | 输出当前应用、故障、拓扑和资源能力快照 | 不改变 |

## 模块索引

| 模块 | 当前职责 |
|---|---|
| `cli.py` | 上述 9 个子命令、Provider 参数和 NL 路径约束 |
| `unified.py` | 统一计划包装、后端绑定、防篡改、执行、证据清单与评分准备 |
| `provider.py` | `LLMProvider`、结构化响应硬化、MiMo/OpenAI-compatible Provider |
| `models.py` / `schema.py` | `BenchmarkIntent v1` 与严格 JSON Schema |
| `catalog.py` | capability snapshot 和指纹 |
| `prompts.py` / `clarification.py` | 受控 Intent prompt、歧义和扩展提案 |
| `compiler.py` | Intent → TopologyRequest/BenchmarkRequest 确定性编译 |
| `session.py` | 受控计划、审批执行和 blind/no-AI 回执验证 |
| `scene_models.py` / `scene_provider.py` | 声明式任意 Scene schema 与 Provider prompt |
| `scene_bridge.py` / `scene_session.py` | Scene 分析、编译、审批和 capability manifest 交付 |
| `unsafe_models.py` / `unsafe_provider.py` | 任意 benchmark IR、预算、文件和五阶段 steps |
| `unsafe_policy.py` | Compose/Dockerfile/Shell、资源和逃逸策略硬化 |
| `unsafe_session.py` | 计划缓存、审批、隔离 Compose 执行、日志、镜像和清理证据 |
| `security.py` | 自然语言 prompt-injection 与危险意图检查 |
| `audit.py` | 原子 JSON、规范化 SHA-256、合同和签名记录 |

## Provider 与响应硬化

Provider 必须返回单个 JSON 对象并匹配调用方提供的 Draft 2020-12 Schema。本地层限制响应大小、
UTF-8、嵌套深度、重复键、未知字段和修复重试，拒绝 tool call、Markdown 包装或 schema 外字段。
MCP 传输失败可按受信 profile fallback；Schema 或策略拒绝不能切换 Provider 绕过。

每次会话保存：输入文本哈希、seed、Prompt/version、Provider/model/transport、原始结构化响应、
能力或策略快照、规范化 IR、编译/安全结果、审批 challenge、执行证据和合同指纹。API Key 只从
指定环境变量读取，不写入 Prompt、会话或缓存。

## 隔离策略

任意路径禁止：

- host bind mount、Docker/Podman socket；
- privileged、host network/PID/IPC/user namespace；
- devices、host ports、external networks；
- Compose 主机环境插值和已知秘密变量；
- Dockerfile 远程 ADD、secret/SSH mount、不安全 frontend、动态 FROM 和远程 stage；
- 自动 qualification、promotion 或 publication。

执行器强制：独立 project/session label、内部 bridge network、只读 rootfs、drop ALL capabilities、
有限 NET_ADMIN/NET_RAW、CPU/内存/PIDs/tmpfs/镜像/输出/时间预算、预存在的基础镜像、运行时
`docker inspect` 二次验证、finally 清理和零残留检查。

## 评分准备与可信边界

成功执行生成：

- `unsafe_execution_result.json`：后端生命周期回执；
- `scoring_preparation.json`：phase coverage、测试数、临时分数；
- `evidence_manifest.json`：证据文件大小和 SHA-256；
- `benchmark_execution_result.json`：统一结果和所有核心指纹。

只有 `status=complete`、清理通过且包含 baseline/inject/recover/verify 时才
`scoring_status=ready`。任意代码始终 `promotion_eligible=false`；要自动晋级，必须转化为受控
SoftwareSpec/FaultDriver/TestSpec 并重新运行 Bundle qualification。

## 兼容 Scene 路径

`nl-scene-*` 不生成代码，只填写 topology、application placements、fault types、difficulty 和
预算。它经过 capability、资源、地址/ASN、连通性、placement 唯一性和 observer 隔离检查，
确定性编译并交付 topology capability manifest。交付 token 无权启动 Docker 或发布。

## 验证

```bash
python3 -m generator.nl.cli --help
python3 tests/test_unified_natural_language_generator.py
python3 tests/test_unsafe_natural_language_generator.py
python3 tests/test_natural_language_generator.py
python3 tests/test_natural_language_scene_bridge.py
python3 tests/run_nl_regression.py
python3 tests/test_mcp_provider.py
python3 tests/test_generator_readmes.py
```

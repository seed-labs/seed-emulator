<!-- README_SYNC_REQUIRED -->

# Natural-Language Generator Gateway

本层允许用户用中文或英文描述 benchmark 需求，并把不可信自然语言/LLM 输出转换成现有
确定性生成器能够验证的 `TopologyRequest` 和 `BenchmarkRequest`。LLM 只负责意图提取，
不拥有 Docker、FaultDriver、发布或修复执行权限。

> **强制同步规则（README_SYNC_REQUIRED）**：修改本目录任意 `.py` 文件时必须同步更新本
> README；改变 CLI、Intent schema、Provider、审批、审计或与 Bundle/Topology/Fault 层的
> 关系时，还必须同步更新 `generator/README.md` 和受影响层的 README。

## 工作流

```text
自然语言
  → 输入安全检查
  → capability snapshot
  → LLMProvider structured output
  → JSON Schema
  → BenchmarkIntent v1
  → 意图安全检查
  → 澄清或扩展提案
  → deterministic compiler
  → TopologyRequest + plan-only BenchmarkRequest
  → 九 Worker + 质量/安全/规模门禁（不启动 Docker）
  → preview + one-time approval challenge
  → nl-generate 显式授权
  → Docker 无 AI 盲测生命周期 × 2
  → qualification + optional publication
```

## 模块

| 文件 | 作用 |
|---|---|
| `models.py` | 严格、无执行权限的 `BenchmarkIntent v1` 和 canonical fingerprint |
| `schema.py` | LLM structured output 的 Draft 2020-12 JSON Schema |
| `provider.py` | `LLMProvider`、无密钥确定性 Provider、OpenAI-compatible 适配器 |
| `catalog.py` | 应用、FaultDriver、拓扑和资源策略的版本化动态快照 |
| `prompts.py` | 版本化系统提示和最小能力上下文 |
| `security.py` | prompt injection、权限绕过、答案/凭据窃取和宿主破坏检查 |
| `clarification.py` | 缺失字段、冲突和未知能力的确定性路由 |
| `compiler.py` | Intent 到现有 TopologyRequest/BenchmarkRequest 和预览的编译 |
| `audit.py` | 原子 JSON、记录指纹和独立 `nl_contract_sha256` |
| `session.py` | 会话、响应缓存、plan-only、一次性审批和真实执行 |
| `cli.py` | `nl-plan`、`nl-generate` 和 `catalog` 入口 |

## 快速使用

从 `benchmarks/` 目录运行：

```bash
python3 -m generator.nl.cli nl-plan \
  --text "生成一个包含 nginx 和 DNS 的 hard 场景，注入延迟和容器停止故障"
```

默认使用不需要 API Key 的 `deterministic-nl-v1`，输出状态、preview、session、
`approved_intent.json` 和只显示一次的 approval token。`nl-plan` 会真实运行九 Worker、质量
和规模门禁，但强制 `execute_lifecycle=false`、`publish=false`，不会启动 Docker。

需要真实模型时：

```bash
export BENCHMARK_LLM_API_KEY='<在本机设置，不写入仓库>'
python3 -m generator.nl.cli nl-plan \
  --provider openai-compatible \
  --model '<model-id>' \
  --base-url 'https://<provider>/v1' \
  --text '<自然语言需求>'
```

代码和审计记录只保存环境变量名称，不读取回显 API Key。

## 澄清和未知能力

缺少应用、难度或故障时，返回 `needs_clarification`（退出码 2），不会产生审批 token。
未知应用/故障/拓扑返回 `extension_required`，只生成需要 `ApplicationTemplate`、
`FaultDriver`、workload/probe 和无 AI 证据的扩展提案，不能执行。

默认仅把未指定规模安全地设为 5，并在 `assumptions` 中记录
`scale_defaulted_to_5`；其他关键字段不猜测。

## 显式授权执行

计划成功后运行输出中的命令参数：

```bash
python3 -m generator.nl.cli nl-generate \
  --intent reports/nl_sessions/<session>/approved_intent.json \
  --approval-token '<one-time-token>'
```

审批 token：

- 只在 `nl-plan` stdout 显示一次；
- 文件中只保存 SHA-256；
- 绑定 intent、plan 和 capability catalog 指纹；
- 24 小时过期；
- 在任何 Docker 状态变化前被原子标记为 consumed；
- 错误、重放、目录逃逸和 catalog 漂移都会拒绝。

`nl-generate` 只启动所选拓扑的精确 Compose 文件，并在 `finally` 中 down。生命周期回执
必须同时满足 `blind_mode=true`、`ai_invoked=false`、`passed=true`、
`topology_tainted=false`；任一字段缺失或不匹配都会 fail closed。

## 会话证据

```text
reports/nl_sessions/<session>/
├── input.json
├── security_input.json
├── capability_snapshot.json
├── provider_request.json
├── provider_response.json
├── normalized_intent.json
├── security_intent.json
├── clarification.json
├── approved_intent.json          # ready 时
├── preview.json                  # ready 时
├── approval_challenge.json       # 0600，仅 token hash
├── compiled/
├── bundle_plan/                  # 九 Worker、无 Docker
├── execution/                    # nl-generate 后
├── execution_result.json         # nl-generate 成功后
└── audit.json
```

相同规范化文本、Provider ID、模型、seed、prompt 版本和 catalog 指纹使用内容寻址缓存，保证
重复请求得到相同规范化 Intent；缓存只在 schema 校验成功后写入。

## 安全边界

- Intent schema 没有 shell、Docker、oracle、repair command 或 approval 字段。
- 未通过输入安全检查时 Provider 根本不会被调用。
- Provider 额外字段、非法 ID、超范围资源和未请求发布均 fail closed。
- `nl-plan` 无法通过 LLM 输出打开执行或发布。
- unknown capability 不能退化为自由 shell，只能生成扩展提案。
- 核心 generator contract 与 NL gateway contract 分开记录；每次会话保存两者的证据。
- private oracle 和标准修复不进入 Provider prompt 或 public preview。

## 验证

`tests/fixtures/nl_benchmark_cases.json` 是版本化长期回归集，覆盖中英文已知需求、关键字段
缺失、未知能力、prompt injection、schema 越权字段和盲测收据篡改。真实 Docker 验收另需检查
qualification 中至少两份无 AI、盲测、未污染且通过的收据。

```bash
python3 -m py_compile generator/nl/*.py
python3 tests/test_natural_language_generator.py
python3 tests/run_nl_regression.py
python3 tests/test_generator_readmes.py
```

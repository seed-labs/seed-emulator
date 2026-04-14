# seed-codex 真实激活面

这份文档只回答一个问题：

`scripts/seed-codex ui` 启动后，Codex 到底自动吃到了什么，东西分别在哪里。

## 一句话结论

当前 `seed-codex` 的独特性，主要来自四层：

1. `CODEX_HOME/config.toml` 里的项目专用 `developer_instructions`
2. 同一个 `config.toml` 里绑定的 SeedAgent / SeedOps MCP 工具白名单
3. 同步进专用 `CODEX_HOME/skills/` 的项目自带 Codex skills
4. repo 内部已有但 **不是** `seed-codex ui` 主路径的旧 YAML skill 系统

最容易混淆的是第 3 层和第 4 层。
第 3 层才是现在 `seed-codex ui` 真的会自动发现和使用的 Codex skills。
第 4 层是旧 BUILD-path agent graph 的内部技能模板，不是当前 attached-runtime 主路径。

## 现在去哪里看

先跑：

```bash
./scripts/seed-codex inspect
```

这条命令会直接打印当前 active stack：

- `CODEX_HOME`
- `config.toml`
- system prompt 来源
- MCP server 与 enabled tools
- project Codex skills 来源与已安装状态
- project plugin 状态
- legacy internal skills 状态

如果老师只追问一句：

“`seed-codex` 为什么不是普通 Codex？”

现在最短、最准确的回答就是：

- 它不是靠口头约定，而是靠专用 `CODEX_HOME`
- 这个 `CODEX_HOME` 里有项目生成的 `config.toml`
- 这个 `config.toml` 里写死了项目级 `developer_instructions` 和 MCP 工具白名单
- 项目自己的 Codex skills 会自动同步进这个 `CODEX_HOME/skills`
- 当前没有 project plugin，不能乱讲 plugin 是核心

## 自动激活顺序

这条链现在是确定的，不是猜的：

1. 你在 repo 根跑 `./scripts/seed-codex ui`
2. 它转发到 `subrepos/seed-agent/scripts/seed-codex`
3. `up` / `ui` 会调用 `render_codex_seed_config.py`，把项目专用配置写进 `subrepos/seed-agent/.codex-seed-agent/config.toml`
4. 同时调用 `seed_codex_assets.py sync`，把 `subrepos/seed-agent/codex_skills/*` 同步进 `subrepos/seed-agent/.codex-seed-agent/skills/*`
5. 最后带着：
   - `CODEX_HOME=subrepos/seed-agent/.codex-seed-agent`
   - `--profile seed_codex_ops`
   启动真实的 Codex

所以自动激活的东西不是散落在 README 里，而是集中落在：

- 项目专用 `CODEX_HOME/config.toml`
- 项目专用 `CODEX_HOME/skills/*`

## 真实来源表

| 层 | 现在是否主路径 | 源文件/目录 | 运行时位置 | 说明 |
|---|---|---|---|---|
| system prompt / developer instructions | 是 | `subrepos/seed-agent/scripts/render_codex_seed_config.py` | `subrepos/seed-agent/.codex-seed-agent/config.toml` | `seed-codex` 最核心的项目特化提示词 |
| SeedAgent MCP 白名单 | 是 | `subrepos/seed-agent/scripts/render_codex_seed_config.py` | 同上 | 高层入口：`seed_agent_run/plan/task_*` |
| SeedOps MCP 白名单 | 是 | `subrepos/seed-agent/scripts/render_codex_seed_config.py` | 同上 | 只读支撑面，不是默认主路径 |
| project Codex skills | 是 | `subrepos/seed-agent/codex_skills/*` | `subrepos/seed-agent/.codex-seed-agent/skills/*` | 由 `scripts/seed-codex up` 自动同步 |
| legacy YAML skills | 否 | `subrepos/seed-agent/skills/*` | 不进入 `CODEX_HOME/skills` | 旧 BUILD-path skill system |
| project-local Codex plugins | 否 | 当前没有 | 当前没有 | 现在没有项目自定义 plugin 层 |
| marketplace cache plugins | 否 | 无项目行为意义 | `CODEX_HOME/.tmp/plugins` | 只是 Codex marketplace/cache，不是 seed-codex 的项目逻辑来源 |

## 现在自动激活的 system prompt 在哪

源头在：

- `subrepos/seed-agent/scripts/render_codex_seed_config.py`

真正生效的是写入后的：

- `subrepos/seed-agent/.codex-seed-agent/config.toml`

`scripts/seed-codex up` 会生成/刷新这个文件。
`scripts/seed-codex ui` 会带着：

- `CODEX_HOME=subrepos/seed-agent/.codex-seed-agent`
- `--profile seed_codex_ops`

去启动 Codex。

所以真正生效的是专用 `CODEX_HOME` 里的配置，不是仓库里某个 README。

## 现在自动激活的 project Codex skills 在哪

源目录：

- `subrepos/seed-agent/codex_skills/seed-runtime-operator`
- `subrepos/seed-agent/codex_skills/seed-task-runtime-loop`
- `subrepos/seed-agent/codex_skills/seed-behavior-verification`

同步目标：

- `subrepos/seed-agent/.codex-seed-agent/skills/seed-runtime-operator`
- `subrepos/seed-agent/.codex-seed-agent/skills/seed-task-runtime-loop`
- `subrepos/seed-agent/.codex-seed-agent/skills/seed-behavior-verification`

同步动作由：

- `subrepos/seed-agent/scripts/seed_codex_assets.py sync`

完成，而 `scripts/seed-codex up` 会自动触发它。

### 这三个 skill 的分工

- `seed-runtime-operator`
  - 解决“已运行网络接管、运行态理解、工具路径选择”
- `seed-task-runtime-loop`
  - 解决“任务式 begin/reply/execute/status 闭环”
- `seed-behavior-verification`
  - 解决“演示前验证、fallback 判定、证据复核”

## 为什么之前会找不到

因为以前实际只有：

- 项目专用 `developer_instructions`
- MCP 工具白名单

但没有一层明确的、项目自带的 Codex skills 自动同步入口。

这会导致两件事：

1. 你能说 `seed-codex` 是项目特化的，但很难指出 skill 到底在哪里
2. 仓库里旧的 `subrepos/seed-agent/skills/*` 很容易被误认成当前 attached-runtime 的 skill 面

现在这两个问题已经拆开了。

## 怎么证明它不是只多了几句 prompt

最小证明链就是三条命令：

```bash
./scripts/seed-codex inspect
./scripts/seed-codex probe-context --attach-output-dir <OUTPUT_DIR> --model gpt-5.4 --reasoning-effort low
./scripts/seed-codex verify --attach-output-dir <OUTPUT_DIR>
```

三条命令分别证明：

- `inspect`
  - 现在到底激活了什么
- `probe-context`
  - 模型真的能通过 Codex + MCP 接管运行时，不是只会闲聊
- `verify`
  - 规划、策略门、运行和证据链至少做了一次闭环检查

## plugin 到底在哪里

当前项目 **没有** project-local Codex plugin。

要直说：

- `CODEX_HOME/.tmp/plugins` 下面那套东西不是 `seed-codex` 的项目逻辑
- 它是 Codex marketplace/cache
- 它不等于“SEED 项目自带 plugin”

所以如果老师问：

“seed-codex 的 plugin 在哪？”

当前准确答案是：

- 现在主路径没有项目自定义 plugin
- 现在的特化主要靠 `config.toml + MCP + project Codex skills`
- plugin 层目前还是空位，不是这套系统真正依赖的核心

## 旧 skill system 到底是什么

这些文件：

- `subrepos/seed-agent/skills/core/*.yaml`
- `subrepos/seed-agent/skills/patterns/*.yaml`
- `subrepos/seed-agent/skills/scenarios/*.yaml`

配套代码：

- `subrepos/seed-agent/agent/skills/loader.py`
- `subrepos/seed-agent/agent/skills/renderer.py`
- `subrepos/seed-agent/agent/nodes/router.py`
- `subrepos/seed-agent/agent/nodes/skill_executor.py`

这是旧 BUILD-path agent graph 的内部技能模板。

它的用途是：

- 识别 `stub_as`
- 渲染成 `create_as(...)`
- 走旧图执行器

它不是当前 `seed-codex ui -> SeedAgent MCP -> SeedOps MCP -> running network` 这条 attached-runtime 主路径。

所以现在要把它视为：

- 仍然存在
- 仍然可测
- 但属于 legacy / build-oriented surface

## 现在工具与 skill 规划应该怎么讲

### 工具规划

高层主路径：

- `seed_agent_run`
- `seed_agent_plan`
- `seed_agent_policy_check`
- `seed_agent_task_*`

低层支撑面：

- `seedops_capabilities`
- `workspace_*`
- `inventory_list_nodes`
- `routing_*`
- `ops_logs`
- `job_*`
- `artifact_*`

原则：

- 默认先高层，后低层
- 低层只用于补证据和定位，不作为默认主路径

### skill 规划

现在应拆成两套，不混讲：

1. `Codex skills`
   - 面向 `seed-codex ui`
   - attached-runtime 主路径
   - 负责行为约束、工作流选择、验证套路
2. `legacy internal YAML skills`
   - 面向旧 BUILD graph
   - 负责拓扑搭建模板
   - 不拿来证明 attached-runtime 智能体能力

## 让它“真的做对事情”的关键

不是再堆更多 prompt，而是三件事一起成立：

1. 有明确的高层主路径
   - `seed_agent_run/plan/task_*`
2. 有项目自带 skill 把“怎么做”收紧
   - attached-runtime
   - task loop
   - behavior verification
3. 有验证闭环证明它不是碰巧答对
   - `scripts/seed-codex inspect`
   - `scripts/seed-codex probe-context`
   - `scripts/seed-codex verify`
   - 任务式 `begin/execute/status`

## 现在的硬边界

- 当前没有项目自定义 plugin 层
- legacy YAML skills 仍然存在，容易混淆，但不应继续当作 attached-runtime 主路径卖点
- `seed_agent_run` 仍可能落到 `template_fallback`
- 所以 live 展示时，应把“验证链”也纳入展示，而不是只展示最终一句回答

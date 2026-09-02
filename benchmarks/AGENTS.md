# Benchmark Agent 工作要求

本文件适用于 `benchmarks/` 及其全部子目录。

## README 强制联级同步

`README_SYNC_REQUIRED`

1. 修改任何 `.py`、声明式 `.json`、schema、CLI 或工具接口时，必须同步修改同目录
   `README.md`，并逐级修改全部祖先 README，直到 `benchmarks/README.md`。
2. 新增包含代码或声明式规范的目录时，必须同时创建含 `README_SYNC_REQUIRED` 标记的
   `README.md`。
3. 删除或移动代码时，必须更新原目录、目标目录以及祖先 README 中的模块索引和流程图。
4. 跨层接口变更必须同步所有生产者、消费者和安全边界说明，不得只更新定义方。
5. 根 README 必须同时维护“精简总体流程图”和“详尽总体流程图”：精简图保留模块职责与
   健康基线→故障→观测→恢复的时序，详尽图保留接口、执行边界和实现细节；任一架构变更都必须
   同步检查两图。未实现能力必须明确标为目标设计。
6. 所有 Agent 只能通过 MCP 和 Agent Tool Service 访问或修改 SEED Python 与 Docker；禁止
   在 Agent 控制面加入直接文件、Shell、Python subprocess 或 Docker 执行旁路。
7. 面向大规模拓扑时必须使用服务端分页、聚合、子图和 TargetSelector，不得把完整拓扑送入
   LLM 上下文。
8. 新增代码后必须建立 README 覆盖与联级门禁，并在提交前运行相关测试及
   `git diff --check -- benchmarks`。

## 安全边界

- Agent 是不可信规划面；Benchmark 控制面和 Candidate Adapter 承担计划与授权策略；Agent Tool Service 只是确定性工具适配层。
- Benchmark 控制面必须为写操作绑定 session、基础版本指纹、资源预算、幂等键、审计记录和回滚计划；Tool Service 只保留参数、目标、超时和执行正确性所需的最低校验。
- Python 修改与 Docker 修改必须先 preview，后 apply；验证失败时必须恢复或标记污染。
- 当前阶段不实现 benchmark 发布。

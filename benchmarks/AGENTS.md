# Benchmark Agent 工作要求

本文件适用于 `benchmarks/` 下的所有开发与测试。完整场景规范见 `docs/NEW_SCENARIO_DEVELOPMENT_GUIDE.md`，开始工作前必须阅读。

## 强制工作流

1. 修改范围只能位于 `benchmarks/`；临时脚本必须放入 `benchmarks/tests/`。
2. 正式 MIMO 测试默认使用 `--blind`，不得向 Agent 暴露场景名称、描述、预期类别、注入命令、目标容器、标准修复或专属提示。
3. `--no-blind` 只用于定向开发调试，不能作为最终自主修复成绩。
4. Agent 多轮问询只能执行经过只读白名单审查的诊断命令；所有状态变更只能通过最终 `repair_commands` 和场景白名单执行。
   修复命令中的重定向、管道、`;` 或 `&&` 必须完整位于 `docker exec <container> sh -c '<payload>'` 的引用参数内，禁止落到 VM 宿主 shell。
5. 诊断与修复独立评分。类别错误不能阻止安全修复尝试；纯查询命令不能计作修复；至少一条命令实际执行且独立验证通过才算修复成功。
6. 状态采集必须包含 stopped/exited 容器，不依赖容器顺序；盲测初始输入只提供健康基线与故障后状态的差异，每条观测必须记录采集命令、容器、资产/接口和输出来源。
7. `--max-turns` 默认 20，允许范围 1–1000；不得在场景中另建不同上限的 Agent。高上限只用于用户明确要求的长时测试。
8. 无论 Agent 成败都执行标准清理和拓扑重建；污染无法清除时停止批次。
9. 报告必须由统一 CLI 生成，并记录 Prompt 模式、轮数上限、结构化根因字段、诊断命令审计、每次修复尝试、拒绝原因、白名单执行、独立验证和隔离结果。
10. CLI 会自动将 stdout 和 stderr 同时输出到终端及 `benchmarks/logs/BENCHMARK_CLI_<timestamp>_<pid>.log`；不得关闭或绕过该审计日志。

## 完成前验证

- 运行相关 `py_compile`；
- 运行 `benchmarks/tests/` 中相关回归测试；
- 运行 `benchmark_cli.py --list` 和参数边界测试；
- 先做无 AI 生命周期测试，再做默认盲测；
- 检查报告、日志、标准清理、拓扑隔离及 `git diff --check -- benchmarks`。

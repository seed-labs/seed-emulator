# 2026-08-26 Generator 组会材料

本目录记录从 `c62cc4944e11bf150fad2f10046c7bc8479a5f21` 到
`feature/benchmark-generator-agent` 当前阶段的功能、复现命令与真实证据。

建议讲解顺序：

1. 阅读 `REPORT.md` 的“汇报结论”和两张 Mermaid 图；
2. 展示 `provider_evidence/.../provider_response.json`，证明 MiMo 通过 MCP 只输出结构化场景；
3. 展示 `lifecycle_matrix_summary.json`，证明七类场景全部 qualified；
4. 展示 `raw/lifecycle_details.json` 中 baseline/active/recovery 输出；
5. 展示 `parallel_isolation/*/isolation.json`，证明同拓扑 session 的容器和子网重绑定；
6. 按 `REPORT.md` 第 5 节现场手动复现。

核心文件：

- `REPORT.md`：完整汇报稿；
- `raw/`：命令原始输出和精简证据；
- `provider_evidence/`：真实 MiMo MCP 会话；
- `lifecycles/`：七类完整 Docker 生命周期；
- `parallel_isolation/`：同拓扑双 Bundle 并行运行；
- `lifecycle_matrix_summary.json`：机器可读结论。

本目录不包含 API Key、密码或有效的一次性审批 token。

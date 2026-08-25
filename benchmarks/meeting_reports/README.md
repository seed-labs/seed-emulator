<!-- README_SYNC_REQUIRED -->

# Generator 组会报告归档

`meeting_reports/` 用于按时间保存 Benchmark Generator 的组会汇报材料与可复核证据。
每次汇报必须创建独立的 `<YYYYMMDD_HHMMSS_TZ>/` 目录，避免覆盖历史结果。

每个时间目录至少应包含：

- 总结报告与架构流程图；
- 可从 `benchmarks/` 目录手动执行的复现命令；
- 静态回归和真实 Docker 生命周期的原始输出；
- 生命周期 workspace 中的 `summary.json`、`qualification.json`、回执和隔离证据；
- 基准提交、被汇报提交和生成器合同指纹。

报告不得保存 API Key、密码、SSH 私钥或一次性审批 token。计划结果必须标记为
plan-only；只有真实运行且能够核验原始回执的结果才能标记为 Docker 生命周期通过或
正式晋级。

修改 Generator 代码的 Agent 在准备组会材料时，应新增时间目录，不得修改旧报告来
重写历史证据。修改归档约定时必须同步更新本 README。

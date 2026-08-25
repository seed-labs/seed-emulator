<!-- README_SYNC_REQUIRED -->

# Declarative topology specifications

本目录保存可审计、可复现的拓扑输入与确定性编译结果。

每个拓扑子目录通常包含：

- `request.json`：用户声明的拓扑、资源和部署要求。
- `plan.json`：经过校验、分配和连通性分析后的确定性计划。

`plan.json` 应由编译器生成，不应手工漂移；相同规范化请求和 seed 应产生等价结果。新增 schema 字段时必须同步更新 `generator/topology/`、能力清单、测试和本 README。

大型拓扑先做规划和预算验证，再按既定策略进行真实或抽样生命周期验证。

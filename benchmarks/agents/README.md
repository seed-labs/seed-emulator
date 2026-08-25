<!-- README_SYNC_REQUIRED -->

# Runtime benchmark agents

该目录是 benchmark **运行期诊断与修复**层，不是 `generator/` 中负责生成规范和产物的 Worker 层。

## 文件职责

- `base.py`：Agent 抽象接口和共享数据结构。
- `agent.py`：基础诊断 Agent 实现。
- `ai_agent.py`：模型驱动的诊断、修复和审计流程。
- `improved_ai_agent.py`：增强的多轮诊断实现。
- `observations.py`：健康基线与故障后状态采集。
- `injector.py`：受场景白名单约束的故障注入适配。

## 维护约束

新增 Agent 能力必须保持诊断命令只读、修复命令受白名单控制，并保留 blind 输入边界。接口或文件职责变化时同步更新本 README 和上级 `benchmarks/README.md`。

相关回归位于 `../tests/`；至少执行与改动对应的 Agent、blind、安全命令和生命周期测试。

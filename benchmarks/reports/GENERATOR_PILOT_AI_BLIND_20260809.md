# Benchmark 测试报告 - AI Agent

**日期**: 2026-08-09 18:05:29

## 测试汇总

- **Agent 类型**: ai
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260809_175921_4085688.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `b00_generator_pilot`
- **已测试**: 1
- **主榜计分场景**: 0
- **类别正确**: 0/1
- **完整根因正确**: 0/1
- **修复验证通过**: 0/1
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 1 | 0 | 0/1 | 0/1 |

## Agent 修复能力评估

- **修复评估场景**: 1
- **Agent 提交修复**: 0/1
- **至少一条命令通过白名单并执行**: 0/1
- **Agent 修复验证通过**: 0/1

## 跨场景隔离与安全清理

- **标准清理验证通过**: 1/1
- **场景后拓扑重建成功**: 1/1
- **仍处于污染状态**: 0

> 修复验证仅统计 Agent 生成且通过白名单审查后实际执行的命令；场景标准 fix 仅用于失败后的安全清理。

## API 资源消耗汇总

- **API 总调用次数**: 3
- **Prompt Tokens 总计**: 7,580
- **Completion Tokens 总计**: 1,480
- **Token 总计**: 9,060
- **总延迟**: 74.9s
- **估算成本**: $0.0181

## 详细结果

| 序号 | 场景 | Track | 难度 | 故障类型 | 诊断结果 | 可信度 | 类别正确 | 完整根因 | 修复验证 | 耗时 | API调用 | Token | 延迟 |
|------|------|-------|------|----------|----------|--------|----------|----------|----------|------|---------|-------|------|
| 1 | gen_container_stopped_509ac469a8_01 | robustness | basic | container_not_running | unknown | 0% | ✗ | ✗ | ✗ | 187s | 3 | 9060 | 74.9s |

## 修复门控详情

| 场景 | Agent 诊断 | 提交修复 | 命令执行 | 修复验证 |
|------|------------|----------|----------|----------|
| gen_container_stopped_509ac469a8_01 | unknown | ✗ | ✗ | ✗ |

## API 调用详情（每场景）

### 场景 1: gen_container_stopped_509ac469a8_01

| 轮次 | 延迟(ms) | Prompt Tokens | Completion Tokens | Total Tokens | 状态 |
|------|----------|---------------|-------------------|--------------|------|
| 1 | 50940 | 2449 | 987 | 3436 | OK |
| 2 | 11829 | 2531 | 234 | 2765 | OK |
| 3 | 12109 | 2600 | 259 | 2859 | OK |

- **场景调用数**: 3
- **场景Token**: 9,060
- **场景延迟**: 74.9s


## Agent 实际修复命令审计

### 场景 1: gen_container_stopped_509ac469a8_01

- 根因判断: 结构化响应熔断：连续 3 次未通过本地 schema；最后错误: Unterminated string starting at: line 2 column 5 (char 6)
- Track/难度: robustness/basic
- 场景派生种子: 7016665955126067933
- 生成 Suite: `b00_generator_pilot`
- 生成指纹: `509ac469a80bbd598097495c52becc047d7f2b069604181481030b12dd1d09a1`
- 生成契约: `387abfdc30a62b7b3050487b5264dffb23eeb5821ce6cb3008f22c3164799f4f`
- 主榜计分: 否
- 分轨原因: generated suite b00_generator_pilot; promote only after live validation
- 目标容器: []
- 故障资产:
- 错误值:
- 期望值:
- 根因字段评分: 0% {'category': False, 'target_container': False, 'artifact': False, 'faulty_value': False, 'expected_value': False}
- 诊断问询轮数: 3
- 修复尝试轮数: 0
- 只读诊断命令执行: 0
- 非只读诊断命令拒绝: 0
- 提议命令: 0
- 实际执行: 0
- 白名单拒绝: 0
- 功能验证: 失败

- 标准清理验证: 通过
- 拓扑隔离重建: 通过
- 污染状态: 否

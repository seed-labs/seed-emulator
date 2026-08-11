# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-12 02:25:29

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260812_022114_613125.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `complex_fault_generator_pilot`
- **已测试**: 3
- **主榜计分场景**: 0
- **类别正确**: 0/3
- **完整根因正确**: 0/3
- **修复验证通过**: 3/3
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 3 | 0 | 0/3 | 3/3 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_dual_dns_network_7adff3a0cc_01 | B00_mini_internet | multiple_faults | unknown | ✗ | ✓ |
| 2 | gen_cascading_network_bgp_612a60dac2_01 | B00_mini_internet | wrong_docker_network | unknown | ✗ | ✓ |
| 3 | gen_dual_bgp_ospf_eee5f977ec_01 | B00_mini_internet | multiple_faults | unknown | ✗ | ✓ |

# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-12 00:27:35

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260812_002530_236259.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `random_complex_generator_pilot`
- **已测试**: 5
- **主榜计分场景**: 0
- **类别正确**: 0/5
- **完整根因正确**: 0/5
- **修复验证通过**: 5/5
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 5 | 0 | 0/5 | 5/5 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_random_complex_transit_acl_7fdefe8ac6_01 | RANDOM_COMPLEX_INTERNET | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 2 | gen_random_complex_transit_acl_72b8e46bcc_01 | RANDOM_COMPLEX_INTERNET | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 3 | gen_random_complex_transit_acl_de983543fe_01 | RANDOM_COMPLEX_INTERNET | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 4 | gen_random_complex_transit_acl_4147c096f0_01 | RANDOM_COMPLEX_INTERNET | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 5 | gen_random_complex_transit_acl_ee1cba6fcc_01 | RANDOM_COMPLEX_INTERNET | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |

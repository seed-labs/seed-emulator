# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-12 19:28:22

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260812_192705_887741.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `declarative_small_ring_pilot`
- **已测试**: 1
- **主榜计分场景**: 0
- **类别正确**: 0/1
- **完整根因正确**: 0/1
- **修复验证通过**: 1/1
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 1 | 0 | 0/1 | 1/1 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_random_complex_dual_bgp_acl_5b3d8d80cf_01 | DECLARATIVE_small_ring | multiple_faults | unknown | ✗ | ✓ |

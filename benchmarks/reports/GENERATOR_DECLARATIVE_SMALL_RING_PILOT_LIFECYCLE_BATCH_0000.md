# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-15 01:55:04

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260815_015031_415912.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `declarative_small_ring_pilot`
- **已测试**: 5
- **主榜计分场景**: 0
- **类别正确**: 0/5
- **完整根因正确**: 0/5
- **修复验证通过**: 5/5
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| network_control_plane | 3 | 0 | 0/3 | 3/3 |
| network_functional | 2 | 0 | 0/2 | 2/2 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_container_stopped_9b2b4ac316_01 | DECLARATIVE_small_ring | container_not_running | unknown | ✗ | ✓ |
| 2 | gen_dns_nameserver_fac593b874_01 | DECLARATIVE_small_ring | dns_failure | unknown | ✗ | ✓ |
| 3 | gen_bird_wrong_asn_9695fab1eb_01 | DECLARATIVE_small_ring | wrong_asn | unknown | ✗ | ✓ |
| 4 | gen_random_complex_transit_acl_25af448cd5_01 | DECLARATIVE_small_ring | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 5 | gen_random_complex_dual_bgp_acl_5b3d8d80cf_01 | DECLARATIVE_small_ring | multiple_faults | unknown | ✗ | ✓ |

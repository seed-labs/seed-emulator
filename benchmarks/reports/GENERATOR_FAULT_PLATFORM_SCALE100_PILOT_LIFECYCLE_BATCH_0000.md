# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-14 19:46:20

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260814_193807_204238.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `fault_platform_scale100_pilot`
- **已测试**: 6
- **主榜计分场景**: 0
- **类别正确**: 0/6
- **完整根因正确**: 0/6
- **修复验证通过**: 6/6
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 6 | 0 | 0/6 | 6/6 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_container_stopped_fd39f992dc_01 | DECLARATIVE_scale_100 | container_not_running | unknown | ✗ | ✓ |
| 2 | gen_dns_nameserver_d11be2b882_01 | DECLARATIVE_scale_100 | dns_failure | unknown | ✗ | ✓ |
| 3 | gen_bird_wrong_asn_1f008d8236_01 | DECLARATIVE_scale_100 | wrong_asn | unknown | ✗ | ✓ |
| 4 | gen_random_complex_transit_acl_5f028cd1aa_01 | DECLARATIVE_scale_100 | randomized_transit_acl_shadowing | unknown | ✗ | ✓ |
| 5 | gen_random_complex_dual_bgp_acl_0a5642ff82_01 | DECLARATIVE_scale_100 | multiple_faults | unknown | ✗ | ✓ |
| 6 | gen_netem_impairment_b458723158_01 | DECLARATIVE_scale_100 | network_impairment | unknown | ✗ | ✓ |

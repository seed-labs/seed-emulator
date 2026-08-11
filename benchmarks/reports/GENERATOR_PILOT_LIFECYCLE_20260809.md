# Benchmark 测试报告 - RULE Agent

**日期**: 2026-08-09 17:51:29

## 测试汇总

- **Agent 类型**: rule
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260809_174125_3992811.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **已测试**: 4
- **主榜计分场景**: 0
- **类别正确**: 0/4
- **完整根因正确**: 0/4
- **修复验证通过**: 4/4
- **完整根因准确率**: 0.0%

## 分轨结果

| Track | 场景数 | 主榜计分 | 完整根因 | 修复通过 |
|---|---:|---:|---:|---:|
| robustness | 4 | 0 | 0/4 | 4/4 |

## 详细结果

| 序号 | 场景 | 拓扑 | 故障类型 | 诊断结果 | 诊断正确 | 修复验证 |
|------|------|------|----------|----------|----------|----------|
| 1 | gen_container_stopped_509ac469a8_01 | B00_mini_internet | container_not_running | unknown | ✗ | ✓ |
| 2 | gen_dns_nameserver_e183f64b8f_01 | B00_mini_internet | dns_failure | unknown | ✗ | ✓ |
| 3 | gen_ipv6_connected_route_592c26befc_01 | B00_mini_internet | ipv6_route_missing | unknown | ✗ | ✓ |
| 4 | gen_bird_wrong_asn_696d67d19c_01 | B00_mini_internet | wrong_asn | unknown | ✗ | ✓ |

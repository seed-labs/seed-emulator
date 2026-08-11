# Benchmark 测试报告 - AI Agent

**日期**: 2026-08-12 01:15:07

## 测试汇总

- **Agent 类型**: ai
- **控制台日志**: `/home/zvanadium/seed-emulator/benchmarks/logs/BENCHMARK_CLI_20260812_010533_483422.log`
- **测试模式**: 盲测
> 盲测不会向 Agent 提供场景名称、预期类别、故障注入、目标容器、参考修复或场景专属提示。

- **AI 最大问询轮数**: 20
- **场景变体种子**: `BENCHMARK_SEED=0`
- **生成 Suite**: `random_complex_generator_pilot`
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

## Agent 修复能力评估

- **修复评估场景**: 1
- **Agent 提交修复**: 1/1
- **至少一条命令通过白名单并执行**: 1/1
- **Agent 修复验证通过**: 1/1

## 跨场景隔离与安全清理

- **标准清理验证通过**: 1/1
- **场景后拓扑重建成功**: 1/1
- **仍处于污染状态**: 0

> 修复验证仅统计 Agent 生成且通过白名单审查后实际执行的命令；场景标准 fix 仅用于失败后的安全清理。

## API 资源消耗汇总

- **API 总调用次数**: 2
- **Prompt Tokens 总计**: 8,635
- **Completion Tokens 总计**: 3,543
- **Token 总计**: 12,178
- **总延迟**: 148.3s
- **估算成本**: $0.0244

## 详细结果

| 序号 | 场景 | Track | 难度 | 故障类型 | 诊断结果 | 可信度 | 类别正确 | 完整根因 | 修复验证 | 耗时 | API调用 | Token | 延迟 |
|------|------|-------|------|----------|----------|--------|----------|----------|----------|------|---------|-------|------|
| 1 | gen_random_complex_transit_acl_7fdefe8ac6_01 | robustness | advanced | randomized_transit_acl_shadowing | firewall_misconfiguration | 95% | ✗ | ✗ | ✓ | 237s | 2 | 12178 | 148.3s |

## 修复门控详情

| 场景 | Agent 诊断 | 提交修复 | 命令执行 | 修复验证 |
|------|------------|----------|----------|----------|
| gen_random_complex_transit_acl_7fdefe8ac6_01 | firewall_misconfiguration | ✓ | ✓ | ✓ |

## API 调用详情（每场景）

### 场景 1: gen_random_complex_transit_acl_7fdefe8ac6_01

| 轮次 | 延迟(ms) | Prompt Tokens | Completion Tokens | Total Tokens | 状态 |
|------|----------|---------------|-------------------|--------------|------|
| 1 | 77329 | 4283 | 1854 | 6137 | OK |
| 2 | 70969 | 4352 | 1689 | 6041 | OK |

- **场景调用数**: 2
- **场景Token**: 12,178
- **场景延迟**: 148.3s


## Agent 实际修复命令审计

### 场景 1: gen_random_complex_transit_acl_7fdefe8ac6_01

- 根因判断: 在 as111brd-router0-10.111.0.254 的 iptables OUTPUT 链中存在一条注释为 'SEED_RANDOM_COMPLEX_ACL' 的规则，该规则以 ICMP 端口不可达的方式拒绝了从 10.201.0.111 到 10.201.0.113 的特定 ICMP 流量，这违反了该容器 OUTPUT 链应为 ACCEPT 的预期状态，可能阻断了网络路径上的必要连通性。
- Track/难度: robustness/advanced
- 场景派生种子: 1499143090136023249
- 生成 Suite: `random_complex_generator_pilot`
- 生成指纹: `7fdefe8ac67c9a45e825cdda345e222798a3833ac80d29c3efd926b83f2b7452`
- 生成契约: `d65f0d4b907004a4cbb4ac51cf363cf6c2d067ee44bda51af607b088e2a7a684`
- 主榜计分: 否
- 分轨原因: generated suite random_complex_generator_pilot; promote only after live validation
- 目标容器: ['as111brd-router0-10.111.0.254']
- 故障资产: iptables OUTPUT chain
- 错误值: -A OUTPUT -s 10.201.0.111/32 -d 10.201.0.113/32 -p icmp -m length --length 84 -m comment --comment SEED_RANDOM_COMPLEX_ACL -j REJECT --reject-with icmp-port-unreachable
- 期望值: -P OUTPUT ACCEPT
- 多根因结构: `[{"category": "firewall_misconfiguration", "target_container": ["as111brd-router0-10.111.0.254"], "artifact": "iptables OUTPUT chain", "faulty_value": "-A OUTPUT -s 10.201.0.111/32 -d 10.201.0.113/32 -p icmp -m length --length 84 -m comment --comment SEED_RANDOM_COMPLEX_ACL -j REJECT --reject-with icmp-port-unreachable", "expected_value": "-P OUTPUT ACCEPT"}]`
- 根因字段评分: 40% {'category': False, 'target_container': True, 'artifact': True, 'faulty_value': False, 'expected_value': False}
- 诊断问询轮数: 2
- 修复尝试轮数: 1
- 只读诊断命令执行: 0
- 非只读诊断命令拒绝: 0
- 提议命令: 1
- 实际执行: 1
- 白名单拒绝: 0
- 功能验证: 通过

- 标准清理验证: 通过
- 拓扑隔离重建: 通过
- 污染状态: 否

```sh
docker exec as111brd-router0-10.111.0.254 iptables -D OUTPUT -s 10.201.0.111/32 -d 10.201.0.113/32 -p icmp -m length --length 84 -m comment --comment SEED_RANDOM_COMPLEX_ACL -j REJECT --reject-with icmp-port-unreachable
```

修复闭环尝试：

- 尝试 1: executed=1, rejected=0, verified=True

# SEED-Emulator Benchmark 项目报告

## 项目概述

### 项目背景

SEED-Emulator 是一个用于构建互联网仿真环境的开源框架，广泛用于网络安全教学和研究。随着 AI 代理（Agent）在网络自动化中的应用逐渐增多，如何评估 AI 代理在网络故障诊断中的能力成为一个重要问题。

本项目构建了一套完整的 Benchmark 系统，用于评估 AI 代理在 SEED-Emulator 互联网仿真环境中的故障诊断和修复能力。

### 项目目标

1. **构建标准化测试环境**：基于 SEED-Emulator 构建可复现的网络拓扑环境
2. **设计多类故障场景**：覆盖 9 种常见网络故障类型
3. **实现自动化测试流程**：故障注入 → 诊断 → 修复 → 验证
4. **支持多种诊断方式**：规则型代理（Rule-based）和 AI 代理
5. **生成结构化报告**：量化评估 AI 代理的诊断能力

### 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    Benchmark 系统                        │
├─────────────────────────────────────────────────────────┤
│  命令行接口 (CLI)                                       │
│  ├── benchmark_cli.py - 主入口                          │
│  └── manager.py - 交互式管理器                          │
├─────────────────────────────────────────────────────────┤
│  场景层 (Scenarios)                                     │
│  ├── base.py - 场景基类                                 │
│  ├── wrong_asn.py - 错误 ASN                           │
│  ├── service_not_running.py - 服务未运行                │
│  ├── dns_failure.py - DNS 故障                          │
│  ├── missing_bgp_peering.py - BGP 对等缺失             │
│  ├── missing_ospf_adjacency.py - OSPF 邻接缺失         │
│  ├── wrong_docker_network.py - Docker 网络错误          │
│  ├── route_reflector_misconfig.py - 路由反射器配置错误  │
│  ├── mpls_label_problem.py - MPLS 标签问题             │
│  └── ipv6_route_missing.py - IPv6 路由缺失             │
├─────────────────────────────────────────────────────────┤
│  代理层 (Agents)                                        │
│  ├── base.py - 代理基类                                 │
│  ├── agent.py - 规则型代理                              │
│  ├── ai_agent.py - AI 代理 (MIMO)                       │
│  └── injector.py - 故障注入器                           │
├─────────────────────────────────────────────────────────┤
│  报告层 (Reports)                                       │
│  └── reports/ - 测试报告目录                            │
└─────────────────────────────────────────────────────────┘
```

---

## 场景覆盖

### 场景列表

| 场景 | 拓扑 | 故障类型 | 说明 |
|------|------|----------|------|
| wrong_asn_01 | B00_mini_internet | wrong_asn | 错误 ASN 配置 |
| service_not_running_01 | B00_mini_internet | service_not_running | 服务未运行 |
| dns_failure_01 | B00_mini_internet | dns_failure | DNS 故障 |
| missing_bgp_peering_01 | B00_mini_internet | missing_bgp_peering | BGP 对等缺失 |
| missing_ospf_adjacency_01 | B00_mini_internet | missing_ospf_adjacency | OSPF 邻接缺失 |
| wrong_docker_network_01 | B00_mini_internet | wrong_docker_network | Docker 网络错误 |
| route_reflector_misconfig_01 | R02_bgp_free_core_mpls | route_reflector_misconfig | 路由反射器配置错误 |
| mpls_label_problem_01 | B31_mini_internet_mpls | mpls_label_problem | MPLS 标签问题 |
| ipv6_route_missing_01 | B00_mini_internet | ipv6_route_missing | IPv6 路由缺失 |

### 拓扑说明

| 拓扑 | 路由协议 | 容器数量 | 说明 |
|------|----------|----------|------|
| B00_mini_internet | BIRD | ~10 | 基础互联网仿真 |
| R02_bgp_free_core_mpls | FRR | ~15 | BGP 自由核心 + MPLS |
| B31_mini_internet_mpls | FRR | ~20 | 带 MPLS 的互联网仿真 |

---

## 测试流程

### 测试架构

```
┌─────────────────┐
│   注入故障      │ ← 场景注入器
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI/规则诊断   │ ← 诊断代理
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   修复故障      │ ← 修复逻辑
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   验证修复      │ ← 验证逻辑
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   生成报告      │ ← 报告生成器
└─────────────────┘
```

### 智能拓扑切换

- **同拓扑场景**：只重置环境，不重新编译
- **不同拓扑场景**：清理环境 → 编译 → 启动新拓扑

### Agent 类型

| Agent | 说明 | 特点 |
|-------|------|------|
| rule | 规则型代理 | 基于预定义规则，快速准确 |
| ai | AI 代理 (MIMO) | 使用大语言模型，灵活性强 |

---

## 测试结果

### Rule-based Agent 测试

**测试时间**：2026-07-23

**测试结果**：9/9 场景全部通过 ✓

| 场景 | 故障类型 | 诊断 | 修复验证 |
|------|----------|------|----------|
| wrong_asn_01 | wrong_asn | ✓ | ✓ |
| service_not_running_01 | service_not_running | ✓ | ✓ |
| dns_failure_01 | dns_failure | ✓ | ✓ |
| missing_bgp_peering_01 | missing_bgp_peering | ✓ | ✓ |
| missing_ospf_adjacency_01 | missing_ospf_adjacency | ✓ | ✓ |
| wrong_docker_network_01 | wrong_docker_network | ✓ | ✓ |
| route_reflector_misconfig_01 | route_reflector_misconfig | ✓ | ✓ |
| mpls_label_problem_01 | mpls_label_problem | ✓ | ✓ |
| ipv6_route_missing_01 | ipv6_route_missing | ✓ | ✓ |

### AI Agent 测试

**测试时间**：2026-07-23

**测试结果**：

| 指标 | 结果 |
|------|------|
| Agent 类型 | MIMO AI |
| 已测试 | 9 |
| 诊断正确 | 1/9 |
| 修复验证通过 | 8/9 |
| 诊断准确率 | 11.1% |

**详细结果**：

| 序号 | 场景 | 拓扑 | 故障类型 | AI 诊断 | 诊断正确 | 修复验证 |
|------|------|------|----------|---------|----------|----------|
| 1 | wrong_asn_01 | B00_mini_internet | wrong_asn | missing_ospf_adjacency | ✗ | ✓ |
| 2 | service_not_running_01 | B00_mini_internet | service_not_running | missing_ospf_adjacency | ✗ | ✓ |
| 3 | dns_failure_01 | B00_mini_internet | dns_failure | missing_ospf_adjacency | ✗ | ✓ |
| 4 | missing_bgp_peering_01 | B00_mini_internet | missing_bgp_peering | missing_ospf_adjacency | ✗ | ✓ |
| 5 | missing_ospf_adjacency_01 | B00_mini_internet | missing_ospf_adjacency | missing_ospf_adjacency | ✓ | ✓ |
| 6 | wrong_docker_network_01 | B00_mini_internet | wrong_docker_network | missing_bgp_peering | ✗ | ✓ |
| 7 | route_reflector_misconfig_01 | R02_bgp_free_core_mpls | route_reflector_misconfig | missing_ospf_adjacency | ✗ | ✓ |
| 8 | mpls_label_problem_01 | B31_mini_internet_mpls | mpls_label_problem | unknown | ✗ | ✓ |
| 9 | ipv6_route_missing_01 | B00_mini_internet | ipv6_route_missing | data_insufficient | ✗ | ✗ |

---

## 问题分析

### AI 代理诊断问题

1. **诊断准确率低**：AI 将大多数场景误诊为 `missing_ospf_adjacency`
2. **数据不足**：场景 9 无法获取足够数据进行诊断
3. **修复验证高**：规则型修复逻辑正确 (8/9)

### 根本原因

1. **提示词不足**：当前提示词未充分描述各故障类型的特征
2. **模型限制**：MIMO v2.5 模型在网络故障诊断方面能力有限
3. **数据收集**：部分场景的数据收集逻辑不完善

### 改进建议

1. **优化提示词**：增加更多故障特征描述和诊断示例
2. **升级模型**：尝试更强的模型 (MIMO v2.5-pro)
3. **完善数据**：增强数据收集的完整性
4. **增加训练**：使用故障诊断数据集进行微调

---

## 技术实现

### 关键技术点

1. **Docker 容器管理**：使用 docker exec 执行容器内命令
2. **BIRD/FRR 路由器**：支持两种路由守护进程
3. **故障注入**：通过修改配置文件注入故障
4. **智能拓扑切换**：根据场景需求自动切换拓扑
5. **CLI 接口**：支持命令行批量测试

### 代码结构

```
benchmarks/
├── benchmark_cli.py        # CLI 入口
├── manager.py              # 交互式管理器
├── scenarios/              # 场景目录
│   ├── __init__.py         # 包初始化
│   ├── base.py             # 场景基类
│   └── *.py                # 9 个场景文件
├── agents/                 # 代理目录
│   ├── base.py             # 代理基类
│   ├── agent.py            # 规则型代理
│   ├── ai_agent.py         # AI 代理
│   └── injector.py         # 故障注入器
├── reports/                # 报告目录
│   └── *.md                # 测试报告
└── BENCHMARK_GUIDE.md      # 使用指南
```

---

## 使用指南

### 环境准备

```bash
# 启动 VM
ssh -i ~/.ssh/id_vm -p 2222 zvanadium@192.168.56.101

# 进入 benchmark 目录
cd ~/seed-emulator/benchmarks
```

### 命令行使用

```bash
# 列出所有场景
python3 benchmark_cli.py --list

# 测试单个场景
python3 benchmark_cli.py --agent rule --scenario wrong_asn_01
python3 benchmark_cli.py --agent ai --scenario wrong_asn_01

# 测试多个场景
python3 benchmark_cli.py --agent ai --scenario wrong_asn_01,dns_failure_01

# 测试所有场景
python3 benchmark_cli.py --agent rule --all
python3 benchmark_cli.py --agent ai --all

# 测试指定拓扑
python3 benchmark_cli.py --agent ai --topology B00_mini_internet

# 指定报告路径
python3 benchmark_cli.py --agent ai --all --report /tmp/my_report.md
```

### 交互式使用

```bash
python3 manager.py
```

菜单选项：
1. 查看所有场景
2. 测试单个场景
3. 测试所有场景
4. 测试指定拓扑的场景
5. 退出

### 查看报告

```bash
ls ~/seed-emulator/benchmarks/reports/
cat ~/seed-emulator/benchmarks/reports/BENCHMARK_AI_REPORT.md
```

---

## 项目总结

### 成果

1. ✅ 构建了完整的 Benchmark 系统
2. ✅ 实现了 9 种故障场景的自动化测试
3. ✅ 支持规则型和 AI 型两种诊断代理
4. ✅ 实现了智能拓扑切换
5. ✅ 提供了 CLI 和交互式两种使用方式
6. ✅ 生成了结构化测试报告

### 待改进

1. ⚠️ AI 代理诊断准确率较低 (11.1%)
2. ⚠️ 部分场景数据收集不完善
3. ⚠️ 提示词需要进一步优化

### 后续工作

1. 优化 AI 提示词，提高诊断准确率
2. 尝试更强的 AI 模型
3. 增加更多故障场景
4. 实现自动化回归测试
5. 集成到 CI/CD 流程

---

## 附录

### 故障类型详细说明

| 故障类型 | 注入方法 | 验证方法 | 修复方法 |
|----------|----------|----------|----------|
| wrong_asn | 修改 BIRD 配置中的 ASN | 检查 BGP 状态 | 恢复 ASN 配置 |
| service_not_running | 停止容器 | 检查容器状态 | 启动容器 |
| dns_failure | 修改 DNS 配置 | 检查 DNS 配置 | 恢复 DNS 配置 |
| missing_bgp_peering | 注释 BGP 协议 | 检查 BGP 状态 | 恢复 BGP 协议 |
| missing_ospf_adjacency | 修改 OSPF 区域 | 检查 OSPF 配置 | 恢复 OSPF 区域 |
| wrong_docker_network | 断开网络接口 | 检查网络连通性 | 恢复网络接口 |
| route_reflector_misconfig | 禁用路由反射器 | 检查路由反射器配置 | 启用路由反射器 |
| mpls_label_problem | 禁用 MPLS | 检查 MPLS 状态 | 启用 MPLS |
| ipv6_route_missing | 删除 IPv6 路由 | 检查 IPv6 路由 | 恢复 IPv6 路由 |

### 相关链接

- SEED-Emulator 仓库：https://github.com/seed-labs/seed-emulator
- BIRD 官网：https://bird.network.cz/
- FRR 官网：https://frrouting.org/

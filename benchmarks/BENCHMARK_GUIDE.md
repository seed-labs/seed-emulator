# SEED-Emulator Benchmark 使用指南

## 1. 环境准备

**前置条件：**
- 安装 Docker 和 Docker Compose
- 安装 Python 3.8+
- 克隆 SEED-Emulator 仓库

**启动 VM：**
```bash
ssh -i ~/.ssh/id_vm -p 2222 zvanadium@192.168.56.101
```

## 2. 文件结构

```
~/seed-emulator/benchmarks/
├── manager.py              # 管理器 - 交互式界面
├── benchmark_cli.py        # CLI - 命令行调用（主入口）
├── scenarios/              # 场景目录
│   ├── __init__.py         # 包初始化（13个场景注册表）
│   ├── base.py             # 场景基类
│   ├── wrong_asn.py                # 场景1
│   ├── service_not_running.py      # 场景2
│   ├── dns_failure.py              # 场景3
│   ├── missing_bgp_peering.py      # 场景4
│   ├── missing_ospf_adjacency.py   # 场景5
│   ├── wrong_docker_network.py     # 场景6
│   ├── route_reflector_misconfig.py # 场景7
│   ├── mpls_label_problem.py       # 场景8
│   ├── ipv6_route_missing.py       # 场景9
│   ├── dual_fault_bgp_ospf.py      # 场景10: 双重故障
│   ├── dual_fault_dns_network.py   # 场景11: 双重故障
│   ├── cascading_bgp_to_ospf.py    # 场景12: 级联故障
│   └── cascading_network_to_bgp.py # 场景13: 级联故障
├── agents/                 # 代理目录
│   ├── base.py             # 代理基类
│   ├── agent.py            # 规则型代理
│   ├── ai_agent.py         # AI代理 (MIMO) — 含API资源监控
│   └── injector.py         # 故障注入器
├── reports/                # 报告目录
│   └── *.md                # 测试报告
├── BENCHMARK_GUIDE.md      # 使用指南
├── COMPLEX_SCENARIOS_GUIDE.md  # 复杂场景指南
├── report.md               # 最终测试报告
├── proof_cn.md             # 中文验证报告
└── proof_en.md             # 英文验证报告
```

## 3. 使用方式

### 方式一：交互式管理器

```bash
cd ~/seed-emulator/benchmarks
python3 manager.py
```

菜单选项：
1. 查看所有场景
2. 测试单个场景
3. 测试所有场景
4. 测试指定拓扑的场景
5. 退出

### 方式二：命令行 CLI

```bash
cd ~/seed-emulator/benchmarks
```

**列出所有场景：**
```bash
python3 benchmark_cli.py --list
```

**测试单个场景（规则型代理）：**
```bash
python3 benchmark_cli.py --agent rule --scenario wrong_asn_01
```

**测试单个场景（AI代理，含API资源监控）：**
```bash
python3 benchmark_cli.py --agent ai --scenario cascading_network_to_bgp_01
```

**测试多个场景：**
```bash
python3 benchmark_cli.py --agent ai --scenario dual_fault_bgp_ospf_01,dual_fault_dns_network_01,cascading_bgp_to_ospf_01,cascading_network_to_bgp_01
```

**测试所有场景：**
```bash
python3 benchmark_cli.py --agent rule --all
python3 benchmark_cli.py --agent ai --all
```

**测试指定拓扑：**
```bash
python3 benchmark_cli.py --agent ai --topology B00_mini_internet
python3 benchmark_cli.py --agent rule --topology R02_bgp_free_core_mpls
```

**指定报告路径：**
```bash
python3 benchmark_cli.py --agent ai --all --report /tmp/my_report.md
```

## 4. 场景说明

### 基础场景 (1-9)

| 场景 | 拓扑 | 故障类型 | 说明 |
|------|------|----------|------|
| wrong_asn_01 | B00 | wrong_asn | 错误 ASN 配置 |
| service_not_running_01 | B00 | service_not_running | 服务未运行 |
| dns_failure_01 | B00 | dns_failure | DNS 故障 |
| missing_bgp_peering_01 | B00 | missing_bgp_peering | BGP 对等缺失 |
| missing_ospf_adjacency_01 | B00 | missing_ospf_adjacency | OSPF 邻接缺失 |
| wrong_docker_network_01 | B00 | wrong_docker_network | Docker 网络错误 |
| route_reflector_misconfig_01 | R02 | route_reflector_misconfig | 路由反射器配置错误 |
| mpls_label_problem_01 | B31 | mpls_label_problem | MPLS 标签问题 |
| ipv6_route_missing_01 | B00 | ipv6_route_missing | IPv6 路由缺失 |

### 复杂场景 (10-13)

| 场景 | 拓扑 | 故障类型 | 说明 |
|------|------|----------|------|
| dual_fault_bgp_ospf_01 | B00 | wrong_asn | 双重故障: BGP ASN 错误 + OSPF 区域错误 |
| dual_fault_dns_network_01 | B00 | dns_failure | 双重故障: DNS 错误 + 网络断开 |
| cascading_bgp_to_ospf_01 | B00 | wrong_asn | 级联故障: BGP 故障导致 OSPF 路由消失 |
| cascading_network_to_bgp_01 | B00 | wrong_docker_network | 级联故障: 网络断开导致 BGP 会话断开 |

## 5. 测试流程

每个场景的测试流程：

```
┌─────────────────┐
│   注入故障      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   AI/规则诊断   │  ← AI Agent 记录 API Token、延迟、调用次数
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   修复故障      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   验证修复      │  ← 轮询检测，最多10次 × 5s
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   生成报告      │  ← AI模式含API消耗统计
└─────────────────┘
```

## 6. 拓扑重启优化

### 首次启动
- `docker-compose up -d` 后**轮询BGP收敛**（最多120s，检测到Established即结束）
- 不再使用固定的 `sleep(90)`

### 同拓扑场景切换
- 跳过完整的清理环境（`docker stop/rm`）
- 直接用 `docker-compose down && up -d` 快速重启
- 轮询BGP收敛（最多60s）

### 不同拓扑切换
- 完整清理 → 编译 → 启动 → 轮询BGP收敛

```python
def wait_for_bgp_convergence(max_wait=120):
    """轮询检测 as2brd-r101 的 BGP Established 会话数"""
    while elapsed < max_wait:
        established = count_established_sessions()
        if established >= 1:
            return  # 收敛完成
        time.sleep(5)
```

## 7. Agent 类型

| Agent | 说明 | API监控 | 用法 |
|-------|------|---------|------|
| rule | 规则型代理 | - | `--agent rule` |
| ai | AI 代理 (MIMO) | Token/延迟/调用次数 | `--agent ai` |

## 8. AI Agent 资源监控

运行 `--agent ai` 时，自动记录每个场景的API资源消耗：

| 指标 | 说明 |
|------|------|
| API 调用次数 | 诊断过程中的 API 调用总数 |
| Prompt Tokens | 发送到模型的 prompt token 总量 |
| Completion Tokens | 模型生成的 completion token 总量 |
| 总 Token | Prompt + Completion |
| 平均延迟 | 每次 API 调用的平均响应时间 |
| 估算成本 | 基于 $0.002/1K tokens 估算 |

报告中包含：
- **API 资源消耗汇总**：所有场景的 token/延迟/成本合计
- **详细结果表**：每场景的 API 调用数、Token、延迟列
- **API 调用详情**：每场景每轮的 prompt/completion tokens 和延迟明细

## 9. 报告位置

默认报告保存在 `~/seed-emulator/benchmarks/reports/` 目录：

```bash
ls ~/seed-emulator/benchmarks/reports/
# BENCHMARK_AI_REPORT.md
# BENCHMARK_RULE_REPORT.md
```

AI Agent 报告示例：

```markdown
## API 资源消耗汇总
- **API 总调用次数**: 6
- **Prompt Tokens 总计**: 27,121
- **Token 总计**: 32,469
- **估算成本**: $0.0649

## 详细结果
| 序号 | 场景 | 故障类型 | 诊断结果 | 可信度 | API调用 | Token | 延迟 |
|------|------|----------|----------|--------|---------|-------|------|
| 1 | cascading_network_to_bgp_01 | wrong_docker_network | missing_bgp_peering | 95% | 6 | 32,469 | 46.8s |
```

## 10. 故障类型说明

| 故障类型 | 注入方法 | 验证方法 | 修复方法 |
|----------|----------|----------|----------|
| wrong_asn | 修改 BIRD 配置中的 ASN | 检查 BGP 状态 | 恢复 ASN 配置 |
| service_not_running | 停止容器 | 检查容器状态 | 启动容器 |
| dns_failure | 修改 DNS 配置 | 检查 DNS 配置 | 恢复 DNS 配置 |
| missing_bgp_peering | 注释 BGP 协议 | 检查 BGP 状态 | 恢复 BGP 协议 |
| missing_ospf_adjacency | 修改 OSPF 区域 | 检查 OSPF 配置 | 恢复 OSPF 区域 |
| wrong_docker_network | 断开网络接口 | 检查 Docker 网络状态 | 恢复网络接口 |
| route_reflector_misconfig | 禁用路由反射器 | 检查路由反射器配置 | 启用路由反射器 |
| mpls_label_problem | 禁用 MPLS | 检查 MPLS 状态 | 启用 MPLS |
| ipv6_route_missing | 删除 IPv6 路由 | 检查 IPv6 路由 | 恢复 IPv6 路由 |

## 11. 常见问题

**Q: 场景测试失败怎么办？**
A: 检查容器是否正在运行，检查命令是否正确执行。

**Q: 如何调试场景？**
A: 使用 `docker exec` 手动执行命令，查看输出。参见 COMPLEX_SCENARIOS_GUIDE.md。

**Q: 如何添加新拓扑？**
A: 在 SEED-Emulator 中创建新的拓扑，在 `benchmark_cli.py` 的 `get_topology_path()` 和 `build_topology()` 中注册。

**Q: 如何扩展诊断代理？**
A: 编辑 `agents/agent.py`（规则型）或 `agents/ai_agent.py`（AI型），添加新的故障检测逻辑。

**Q: 如何添加新场景？**
A: 在 `scenarios/` 目录下创建新的场景文件，继承 `BaseScenario` 类，在 `__init__.py` 中注册。

**Q: AI 诊断结果不正确？**
A: AI 代理的诊断质量取决于 system prompt 和初始网络状态收集。可以调整 `ai_agent.py` 中的：
- `get_system_prompt()` — 优化故障检测引导
- `collect_network_state()` — 调整初始数据收集范围
- `max_turns` — 调整交互轮次上限

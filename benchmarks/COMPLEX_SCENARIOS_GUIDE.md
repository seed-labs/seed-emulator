# SEED-Emulator Benchmark 复杂场景设计指南

## 概述

本文档为 SEED-Emulator Benchmark 系统提供复杂场景设计指南，旨在扩展故障诊断测试的复杂度和覆盖范围。

---

## 场景分类总览

| 类别 | 场景数量 | 复杂度范围 | 说明 |
|------|----------|------------|------|
| 多故障叠加 | 2 | ⭐⭐⭐ | 同时发生两个独立故障 |
| 级联故障 | 2 | ⭐⭐⭐⭐ | 一个故障引发另一个故障 |
| 性能降级 | 2 | ⭐⭐⭐-⭐⭐⭐⭐⭐ | 不是完全故障，而是性能下降 |
| 安全相关 | 2 | ⭐⭐⭐⭐-⭐⭐⭐⭐⭐ | 访问控制或路由策略错误 |
| 复杂路由 | 2 | ⭐⭐⭐⭐⭐ | 多协议路由交互 |

---

## 详细场景设计

### 1. 多故障叠加场景

#### 场景 10: dual_fault_bgp_ospf

**基本信息**
- **场景名称**: `dual_fault_bgp_ospf_01`
- **故障类型**: `dual_fault_bgp_ospf`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐

**故障描述**
同时注入两个独立故障：
1. BGP ASN 配置错误（修改 AS 号）
2. OSPF 区域配置错误（修改 area ID）

**诊断挑战**
- 需要同时识别两个独立故障
- 两个故障可能相互干扰诊断
- 需要区分哪个是主要故障，哪个是次要故障

**修复挑战**
- 需要按正确顺序修复（通常先修复 BGP，再修复 OSPF）
- 修复一个故障可能影响另一个故障的表现
- 需要验证两个故障都已修复

**实现要点**
```python
class DualFaultBgpOspfScenario(BaseScenario):
    name = "dual_fault_bgp_ospf_01"
    description = "双重故障: BGP ASN 错误 + OSPF 区域错误"
    topology = "B00_mini_internet"
    fault_type = "dual_fault_bgp_ospf"

    def get_inject_cmd(self) -> str:
        # 同时注入两个故障
        return """
            # 故障1: 修改 BGP ASN
            docker exec as2brd-r100-10.100.0.2 sed -i 's/as 2;/as 999;/g' /etc/bird/bird.conf &&
            docker exec as2brd-r100-10.100.0.2 birdc configure &&

            # 故障2: 修改 OSPF 区域
            docker exec as2brd-r100-10.100.0.2 sed -i 's/area 0/area 99/g' /etc/bird/bird.conf &&
            docker exec as2brd-r100-10.100.0.2 birdc configure
        """

    def get_verify_cmd(self) -> str:
        return "docker exec as2brd-r100-10.100.0.2 birdc show protocols"

    def get_fix_cmd(self) -> str:
        # 修复两个故障
        return """
            # 修复1: 恢复 BGP ASN
            docker exec as2brd-r100-10.100.0.2 sed -i 's/as 999;/as 2;/g' /etc/bird/bird.conf &&

            # 修复2: 恢复 OSPF 区域
            docker exec as2brd-r100-10.100.0.2 sed -i 's/area 99/area 0/g' /etc/bird/bird.conf &&
            docker exec as2brd-r100-10.100.0.2 birdc configure
        """

    def check_verified(self, output: str) -> bool:
        # 验证两个故障都已修复
        return "Bad peer AS" not in output and "area 0" in output
```

---

#### 场景 11: dual_fault_dns_network

**基本信息**
- **场景名称**: `dual_fault_dns_network_01`
- **故障类型**: `dual_fault_dns_network`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐

**故障描述**
同时注入两个独立故障：
1. DNS 配置错误（修改 resolv.conf）
2. 网络接口断开（断开 Docker 网络）

**诊断挑战**
- 需要区分是 DNS 问题还是网络问题
- 网络问题可能掩盖 DNS 问题
- 需要检查多个层面的配置

**修复挑战**
- 需要先修复网络，再修复 DNS
- 修复网络后才能验证 DNS 修复
- 需要验证网络连通性和 DNS 解析

**实现要点**
```python
class DualFaultDnsNetworkScenario(BaseScenario):
    name = "dual_fault_dns_network_01"
    description = "双重故障: DNS 错误 + 网络断开"
    topology = "B00_mini_internet"
    fault_type = "dual_fault_dns_network"

    def get_inject_cmd(self) -> str:
        # 同时注入两个故障
        return """
            # 故障1: 修改 DNS 配置
            docker exec as150h-host_0-10.150.0.71 sh -c 'echo "nameserver 192.0.2.1" > /etc/resolv.conf' &&

            # 故障2: 断开网络
            docker network disconnect output_net_150_net0 as150brd-router0-10.150.0.254
        """

    def get_verify_cmd(self) -> str:
        return "docker exec as150h-host_0-10.150.0.71 cat /etc/resolv.conf"

    def get_fix_cmd(self) -> str:
        # 先修复网络，再修复 DNS
        return """
            # 修复1: 恢复网络
            docker network connect output_net_150_net0 as150brd-router0-10.150.0.254 &&

            # 修复2: 恢复 DNS
            docker exec as150h-host_0-10.150.0.71 sh -c 'echo "nameserver 10.153.0.73" > /etc/resolv.conf'
        """

    def check_verified(self, output: str) -> bool:
        # 验证 DNS 配置正确
        return "10.153.0.73" in output
```

---

### 2. 级联故障场景

#### 场景 12: cascading_bgp_to_ospf

**基本信息**
- **场景名称**: `cascading_bgp_to_ospf_01`
- **故障类型**: `cascading_bgp_to_ospf`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐

**故障描述**
BGP 故障导致 OSPF 路由消失：
1. 注入 BGP ASN 错误
2. BGP 会话断开
3. 依赖 BGP 的 OSPF 路由消失

**诊断挑战**
- 需要识别根因是 BGP 而非 OSPF
- OSPF 状态可能看起来正常，但路由缺失
- 需要理解 BGP 和 OSPF 的依赖关系

**修复挑战**
- 修复 BGP 后 OSPF 应该自动恢复
- 需要验证 OSPF 路由是否重新出现
- 可能需要等待路由收敛

**实现要点**
```python
class CascadingBgpToOspfScenario(BaseScenario):
    name = "cascading_bgp_to_ospf_01"
    description = "级联故障: BGP 故障导致 OSPF 路由消失"
    topology = "B00_mini_internet"
    fault_type = "cascading_bgp_to_ospf"

    def get_inject_cmd(self) -> str:
        # 注入 BGP 故障
        return """
            docker exec as2brd-r100-10.100.0.2 sed -i 's/as 2;/as 999;/g' /etc/bird/bird.conf &&
            docker exec as2brd-r100-10.100.0.2 birdc configure
        """

    def get_verify_cmd(self) -> str:
        # 检查 OSPF 路由是否消失
        return "docker exec as2brd-r100-10.100.0.2 birdc show route table master"

    def get_fix_cmd(self) -> str:
        # 修复 BGP 故障
        return """
            docker exec as2brd-r100-10.100.0.2 sed -i 's/as 999;/as 2;/g' /etc/bird/bird.conf &&
            docker exec as2brd-r100-10.100.0.2 birdc configure
        """

    def check_verified(self, output: str) -> bool:
        # 验证 OSPF 路由是否恢复
        return "10.0.0.0" in output or "ospf" in output.lower()
```

---

#### 场景 13: cascading_network_to_bgp

**基本信息**
- **场景名称**: `cascading_network_to_bgp_01`
- **故障类型**: `cascading_network_to_bgp`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐

**故障描述**
网络接口问题导致 BGP 会话断开：
1. 断开 Docker 网络接口
2. BGP 会话因网络不可达而断开
3. 路由表清空

**诊断挑战**
- 需要识别是网络层问题而非 BGP 配置问题
- BGP 状态显示 "Active" 或 "Idle"，但原因不同
- 需要检查网络接口状态

**修复挑战**
- 需要先修复网络接口
- BGP 会话应该自动重新建立
- 需要等待 BGP 会话收敛

**实现要点**
```python
class CascadingNetworkToBgpScenario(BaseScenario):
    name = "cascading_network_to_bgp_01"
    description = "级联故障: 网络断开导致 BGP 会话断开"
    topology = "B00_mini_internet"
    fault_type = "cascading_network_to_bgp"

    def get_inject_cmd(self) -> str:
        # 断开网络接口
        return "docker network disconnect output_net_ix_ix100 as2brd-r100-10.100.0.2"

    def get_verify_cmd(self) -> str:
        # 检查 BGP 状态
        return "docker exec as2brd-r100-10.100.0.2 birdc show protocols"

    def get_fix_cmd(self) -> str:
        # 恢复网络接口
        return "docker network connect output_net_ix_ix100 as2brd-r100-10.100.0.2"

    def check_verified(self, output: str) -> bool:
        # 验证 BGP 会话是否恢复
        return "Established" in output
```

---

### 3. 性能降级场景

#### 场景 14: performance_mpls_latency

**基本信息**
- **场景名称**: `performance_mpls_latency_01`
- **故障类型**: `performance_mpls_latency`
- **拓扑**: B31_mini_internet_mpls
- **复杂度**: ⭐⭐⭐

**故障描述**
MPLS 标签问题导致高延迟：
1. 禁用 MPLS LDP
2. 流量回退到 IP 路由
3. 延迟显著增加

**诊断挑战**
- 需要检测延迟而非完全故障
- 需要测量网络延迟
- 需要识别是 MPLS 问题而非其他原因

**修复挑战**
- 启用 MPLS 后需要验证延迟是否降低
- 需要对比修复前后的延迟
- 可能需要等待 MPLS 邻居重新建立

**实现要点**
```python
class PerformanceMplsLatencyScenario(BaseScenario):
    name = "performance_mpls_latency_01"
    description = "性能降级: MPLS 问题导致高延迟"
    topology = "B31_mini_internet_mpls"
    fault_type = "performance_mpls_latency"

    def get_inject_cmd(self) -> str:
        # 禁用 MPLS LDP
        return """
            docker exec as8r-core0-10.8.0.253 vtysh -c 'configure terminal' -c 'no mpls ldp' -c 'end' -c 'write memory'
        """

    def get_verify_cmd(self) -> str:
        # 检查延迟
        return "docker exec as150h-host_0-10.150.0.71 ping -c 5 10.160.0.71"

    def get_fix_cmd(self) -> str:
        # 启用 MPLS LDP
        return """
            docker exec as8r-core0-10.8.0.253 vtysh -c 'configure terminal' -c 'mpls ldp' -c 'end' -c 'write memory'
        """

    def check_verified(self, output: str) -> bool:
        # 验证延迟是否降低（小于 100ms）
        import re
        match = re.search(r'avg = (\d+\.\d+)/', output)
        if match:
            avg_latency = float(match.group(1))
            return avg_latency < 100
        return False
```

---

#### 场景 15: performance_bgp_route_flap

**基本信息**
- **场景名称**: `performance_bgp_route_flap_01`
- **故障类型**: `performance_bgp_route_flap`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐⭐

**故障描述**
BGP 路由震荡导致网络不稳定：
1. 间歇性断开 BGP 会话
2. 路由频繁变化
3. 网络连接不稳定

**诊断挑战**
- 需要检测路由变化频率
- 故障是间歇性的，难以捕捉
- 需要监控路由表变化

**修复挑战**
- 需要稳定 BGP 会话
- 可能需要调整 BGP 定时器
- 需要验证路由是否稳定

**实现要点**
```python
class PerformanceBgpRouteFlapScenario(BaseScenario):
    name = "performance_bgp_route_flap_01"
    description = "性能降级: BGP 路由震荡"
    topology = "B00_mini_internet"
    fault_type = "performance_bgp_route_flap"

    def get_inject_cmd(self) -> str:
        # 间歇性断开 BGP 会话
        return """
            # 循环断开和恢复 BGP 会话
            for i in $(seq 1 5); do
                docker exec as2brd-r100-10.100.0.2 birdc disable p_rs100
                sleep 2
                docker exec as2brd-r100-10.100.0.2 birdc enable p_rs100
                sleep 2
            done
        """

    def get_verify_cmd(self) -> str:
        # 检查路由稳定性
        return "docker exec as2brd-r100-10.100.0.2 birdc show route count"

    def get_fix_cmd(self) -> str:
        # 稳定 BGP 会话
        return """
            docker exec as2brd-r100-10.100.0.2 birdc enable p_rs100
            sleep 10
        """

    def check_verified(self, output: str) -> bool:
        # 验证路由数量稳定
        return "routes" in output.lower()
```

---

### 4. 安全相关场景

#### 场景 16: security_acl_block

**基本信息**
- **场景名称**: `security_acl_block_01`
- **故障类型**: `security_acl_block`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐

**故障描述**
ACL 阻止特定流量：
1. 配置 ACL 阻止特定 IP 流量
2. 路由器丢弃匹配的数据包
3. 特定目的地不可达

**诊断挑战**
- 需要识别是安全策略问题
- 需要检查 ACL 配置
- 需要理解 ACL 规则逻辑

**修复挑战**
- 需要修改 ACL 规则
- 需要验证特定流量是否恢复
- 需要确保不引入安全漏洞

**实现要点**
```python
class SecurityAclBlockScenario(BaseScenario):
    name = "security_acl_block_01"
    description = "安全问题: ACL 阻止特定流量"
    topology = "B00_mini_internet"
    fault_type = "security_acl_block"

    def get_inject_cmd(self) -> str:
        # 配置 ACL 阻止特定流量
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'access-list 100 deny ip 10.150.0.0 0.0.0.255 any' -c 'access-list 100 permit ip any any' -c 'end' -c 'write memory'
        """

    def get_verify_cmd(self) -> str:
        # 检查 ACL 配置
        return "docker exec as2brd-r100-10.100.0.2 vtysh -c 'show access-list'"

    def get_fix_cmd(self) -> str:
        # 删除 ACL 规则
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'no access-list 100' -c 'end' -c 'write memory'
        """

    def check_verified(self, output: str) -> bool:
        # 验证 ACL 规则已删除
        return "access-list 100" not in output
```

---

#### 场景 17: security_routing_policy

**基本信息**
- **场景名称**: `security_routing_policy_01`
- **故障类型**: `security_routing_policy`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐⭐

**故障描述**
路由策略错误导致路由丢失：
1. 配置 route-map 过滤特定路由
2. 路由表缺少特定路由
3. 流量无法到达特定目的地

**诊断挑战**
- 需要理解路由策略逻辑
- 需要分析 route-map 配置
- 需要识别是策略问题而非配置错误

**修复挑战**
- 需要修改路由策略
- 需要验证路由是否恢复
- 需要确保策略逻辑正确

**实现要点**
```python
class SecurityRoutingPolicyScenario(BaseScenario):
    name = "security_routing_policy_01"
    description = "安全问题: 路由策略错误导致路由丢失"
    topology = "B00_mini_internet"
    fault_type = "security_routing_policy"

    def get_inject_cmd(self) -> str:
        # 配置 route-map 过滤路由
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'route-map FILTER deny 10' -c 'match ip address prefix-list FILTER_LIST' -c 'exit' -c 'ip prefix-list FILTER_LIST seq 5 deny 10.150.0.0/24' -c 'ip prefix-list FILTER_LIST seq 100 permit 0.0.0.0/0 le 32' -c 'end' -c 'write memory'
        """

    def get_verify_cmd(self) -> str:
        # 检查路由表
        return "docker exec as2brd-r100-10.100.0.2 vtysh -c 'show ip route'"

    def get_fix_cmd(self) -> str:
        # 删除 route-map
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'no route-map FILTER' -c 'no ip prefix-list FILTER_LIST' -c 'end' -c 'write memory'
        """

    def check_verified(self, output: str) -> bool:
        # 验证路由是否恢复
        return "10.150.0.0" in output
```

---

### 5. 复杂路由场景

#### 场景 18: complex_route_redistribution

**基本信息**
- **场景名称**: `complex_route_redistribution_01`
- **故障类型**: `complex_route_redistribution`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐⭐

**故障描述**
OSPF 到 BGP 路由重分发错误：
1. 配置错误的路由重分发规则
2. OSPF 路由无法正确分发到 BGP
3. BGP 邻居缺少 OSPF 路由

**诊断挑战**
- 需要理解多协议路由交互
- 需要检查重分发配置
- 需要验证路由是否正确分发

**修复挑战**
- 需要正确配置重分发规则
- 需要验证路由是否正确分发
- 可能需要清除并重新分发路由

**实现要点**
```python
class ComplexRouteRedistributionScenario(BaseScenario):
    name = "complex_route_redistribution_01"
    description = "复杂路由: OSPF 到 BGP 重分发错误"
    topology = "B00_mini_internet"
    fault_type = "complex_route_redistribution"

    def get_inject_cmd(self) -> str:
        # 配置错误的重分发规则
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'router bgp 2' -c 'redistribute ospf' -c 'end' -c 'write memory'
        """

    def get_verify_cmd(self) -> str:
        # 检查 BGP 路由
        return "docker exec as2brd-r100-10.100.0.2 vtysh -c 'show ip bgp'"

    def get_fix_cmd(self) -> str:
        # 修复重分发规则
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'router bgp 2' -c 'no redistribute ospf' -c 'redistribute ospf metric 100' -c 'end' -c 'write memory'
        """

    def check_verified(self, output: str) -> bool:
        # 验证路由是否正确分发
        return "ospf" in output.lower() or "10.0.0.0" in output
```

---

#### 场景 19: complex_route_map

**基本信息**
- **场景名称**: `complex_route_map_01`
- **故障类型**: `complex_route_map`
- **拓扑**: B00_mini_internet
- **复杂度**: ⭐⭐⭐⭐⭐

**故障描述**
Route-map 配置错误导致路由过滤：
1. 配置 route-map 过滤特定路由
2. 路由表缺少特定路由
3. 流量无法到达特定目的地

**诊断挑战**
- 需要分析 route-map 逻辑
- 需要理解路由过滤规则
- 需要识别是 route-map 问题

**修复挑战**
- 需要修改 route-map 规则
- 需要验证路由是否恢复
- 需要确保 route-map 逻辑正确

**实现要点**
```python
class ComplexRouteMapScenario(BaseScenario):
    name = "complex_route_map_01"
    description = "复杂路由: Route-map 配置错误"
    topology = "B00_mini_internet"
    fault_type = "complex_route_map"

    def get_inject_cmd(self) -> str:
        # 配置错误的 route-map
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'route-map POLICY deny 10' -c 'match ip address prefix-list BLOCK' -c 'exit' -c 'ip prefix-list BLOCK seq 5 deny 10.150.0.0/24' -c 'ip prefix-list BLOCK seq 100 permit 0.0.0.0/0 le 32' -c 'end' -c 'write memory'
        """

    def get_verify_cmd(self) -> str:
        # 检查路由表
        return "docker exec as2brd-r100-10.100.0.2 vtysh -c 'show ip route'"

    def get_fix_cmd(self) -> str:
        # 删除 route-map
        return """
            docker exec as2brd-r100-10.100.0.2 vtysh -c 'configure terminal' -c 'no route-map POLICY' -c 'no ip prefix-list BLOCK' -c 'end' -c 'write memory'
        """

    def check_verified(self, output: str) -> bool:
        # 验证路由是否恢复
        return "10.150.0.0" in output
```

---

## 实施建议

### 推荐实施顺序

#### 第一阶段: 中等复杂度（1-2 小时）

1. **场景 10**: dual_fault_bgp_ospf
2. **场景 11**: dual_fault_dns_network

**目标**: 测试多故障诊断能力

#### 第二阶段: 高复杂度（2-4 小时）

3. **场景 12**: cascading_bgp_to_ospf
4. **场景 13**: cascading_network_to_bgp

**目标**: 测试级联故障诊断能力

#### 第三阶段: 专家级（4+ 小时）

5. **场景 14**: performance_mpls_latency
6. **场景 16**: security_acl_block

**目标**: 测试性能和安全诊断能力

### 测试策略

1. **单场景测试**: 先测试单个场景，确保基本功能正常
2. **组合测试**: 测试多个场景组合，验证兼容性
3. **压力测试**: 连续运行所有场景，验证稳定性
4. **AI 诊断测试**: 使用 AI 代理测试所有场景，评估诊断能力

### 预期成果

| 阶段 | 场景数量 | 预期诊断准确率 | 预期修复成功率 |
|------|----------|----------------|----------------|
| 第一阶段 | 2 | 20-30% | 80-90% |
| 第二阶段 | 4 | 30-40% | 70-80% |
| 第三阶段 | 6 | 40-50% | 60-70% |

---

## 附录

### 故障类型映射

| 故障类型 | 场景编号 | 复杂度 | 拓扑 |
|----------|----------|--------|------|
| dual_fault_bgp_ospf | 10 | ⭐⭐⭐ | B00_mini_internet |
| dual_fault_dns_network | 11 | ⭐⭐⭐ | B00_mini_internet |
| cascading_bgp_to_ospf | 12 | ⭐⭐⭐⭐ | B00_mini_internet |
| cascading_network_to_bgp | 13 | ⭐⭐⭐⭐ | B00_mini_internet |
| performance_mpls_latency | 14 | ⭐⭐⭐ | B31_mini_internet_mpls |
| performance_bgp_route_flap | 15 | ⭐⭐⭐⭐⭐ | B00_mini_internet |
| security_acl_block | 16 | ⭐⭐⭐⭐ | B00_mini_internet |
| security_routing_policy | 17 | ⭐⭐⭐⭐⭐ | B00_mini_internet |
| complex_route_redistribution | 18 | ⭐⭐⭐⭐⭐ | B00_mini_internet |
| complex_route_map | 19 | ⭐⭐⭐⭐⭐ | B00_mini_internet |

### 诊断优先级建议

1. **首先检查**: 网络接口状态
2. **然后检查**: BGP 会话状态
3. **接着检查**: OSPF 邻居状态
4. **然后检查**: 路由表内容
5. **最后检查**: 安全策略配置

### 修复顺序建议

1. **网络层**: 先修复网络接口问题
2. **路由协议**: 再修复路由协议问题
3. **安全策略**: 最后修复安全策略问题
4. **验证**: 每修复一个层面后验证功能

---

**文档版本**: v1.0
**最后更新**: 2026-07-23
**作者**: Sisyphus

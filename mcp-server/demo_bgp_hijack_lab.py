#!/usr/bin/env python3
"""
===========================================
BGP 劫持攻击实验 - 真实演示
BGP Hijacking Attack Lab - Real Demo
===========================================

这是一个真实的安全实验，演示 BGP 劫持攻击的原理和效果。

网络拓扑:
                    ┌─────────────────┐
                    │   IX-100        │
                    │ (路由服务器)     │
                    └───────┬─────────┘
           ┌────────────────┼────────────────┐
           │                │                │
    ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴──────┐
    │   AS 150    │  │   AS 151    │  │   AS 160    │
    │  (受害者)    │  │  (正常AS)    │  │  (攻击者)    │
    │ 10.150.0.0/24│  │ 10.151.0.0/24│  │ 10.160.0.0/24│
    └─────────────┘  └─────────────┘  └─────────────┘

攻击流程:
1. 正常状态: AS151 -> IX -> AS150 (正常路由)
2. 攻击实施: AS160 宣告 10.150.0.0/24 (劫持 AS150 的前缀)
3. 攻击后: AS151 -> IX -> AS160 (流量被重定向)

教育目标:
- 理解 BGP 信任模型的脆弱性
- 观察路由劫持的实际效果
- 学习如何检测和防御 BGP 劫持
"""

import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from runtime import runtime, AgentPhase
from server import (
    # Infrastructure
    create_as, create_ix, create_node, connect_nodes, connect_to_ix,
    # Routing
    enable_routing_layers, configure_ix_peering,
    # Docker
    render_simulation, compile_simulation, build_images, 
    start_simulation, stop_simulation, list_containers,
    # Dynamic
    exec_command, ping_test, get_routing_table, get_bgp_status,
    # Attack
    bgp_announce_prefix, get_looking_glass,
    # Evidence
    capture_evidence,
)


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, description):
    print(f"\n📌 [Step {step_num}] {description}")
    print("-" * 60)


def wait_with_countdown(seconds, message=""):
    print(f"\n⏳ {message} ({seconds} 秒)")
    for i in range(seconds, 0, -5):
        print(f"   剩余 {i} 秒...")
        time.sleep(5)


def main():
    print_header("🔓 BGP 劫持攻击实验 - BGP Hijacking Lab")
    print("""
    本实验将演示:
    1. 构建多 AS 互联网络
    2. 验证正常路由
    3. 实施 BGP 劫持攻击
    4. 观察路由变化
    5. 收集攻击证据
    """)
    
    # =========================================================================
    # Step 1: 构建网络拓扑
    # =========================================================================
    print_header("阶段一: 构建网络拓扑")
    
    print_step(1, "重置环境")
    runtime.reset()
    runtime.set_phase(AgentPhase.DESIGNING)
    print("✅ Runtime 已重置")
    
    print_step(2, "创建 Internet Exchange (IX-100)")
    result = create_ix(100, "ix100")
    print(result)
    
    print_step(3, "创建 AS150 (受害者网络)")
    create_as(150)
    create_node("r150", 150, "router")
    create_node("victim-web", 150, "host")
    connect_nodes("victim-web", "r150")
    print("✅ AS150: 1 路由器 + 1 Web服务器")
    
    print_step(4, "创建 AS151 (正常用户)")
    create_as(151)
    create_node("r151", 151, "router")
    create_node("user-client", 151, "host")
    connect_nodes("user-client", "r151")
    print("✅ AS151: 1 路由器 + 1 用户客户端")
    
    print_step(5, "创建 AS160 (攻击者网络)")
    create_as(160)
    create_node("r160", 160, "router")
    create_node("attacker", 160, "host")
    connect_nodes("attacker", "r160")
    print("✅ AS160: 1 路由器 + 1 攻击主机")
    
    print_step(6, "连接所有 AS 到 IX-100")
    connect_to_ix("r150", 100)
    connect_to_ix("r151", 100)
    connect_to_ix("r160", 100)
    print("✅ 所有 AS 已连接到 IX-100")
    
    print_step(7, "配置 BGP 路由")
    enable_routing_layers(["routing", "ebgp"])
    
    # 使用 Route Server 配置 - 所有 AS 都通过 RS 对等
    # RS at IX100 会自动与所有连接的 AS 建立对等
    # 我们需要手动添加私有对等
    
    # 配置 RS 对等 (每个 AS 都和 RS 对等)
    from seedemu.layers import Ebgp, PeerRelationship
    emulator = runtime.get_emulator()
    ebgp_layer = None
    for l in emulator.getLayers():
        if isinstance(l, Ebgp):
            ebgp_layer = l
            break
    
    if ebgp_layer:
        # RS peering - all ASes peer with the route server
        ebgp_layer.addRsPeer(100, 150)
        ebgp_layer.addRsPeer(100, 151)
        ebgp_layer.addRsPeer(100, 160)
        print("✅ BGP RS 对等已配置")
    else:
        print("❌ 无法获取 EBGP 层")
        return False
    
    # =========================================================================
    # Step 2: 编译和启动
    # =========================================================================
    print_header("阶段二: 编译和启动模拟器")
    
    print_step(8, "渲染网络配置")
    render_result = render_simulation()
    print(render_result)
    
    print_step(9, "编译 Docker 文件")
    output_dir = "/home/parallels/seed-email-service/mcp-server/output_bgp_hijack_lab"
    compile_result = compile_simulation(output_dir)
    print(compile_result)
    
    print_step(10, "构建 Docker 镜像")
    build_result = build_images()
    print(build_result)
    
    if "Error" in build_result:
        print("❌ 构建失败")
        return False
    
    print_step(11, "启动模拟器")
    start_result = start_simulation()
    print(start_result)
    
    if "Error" in start_result:
        print("❌ 启动失败")
        return False
    
    wait_with_countdown(40, "等待容器和 BGP 初始化")
    
    # =========================================================================
    # Step 3: 验证正常状态
    # =========================================================================
    print_header("阶段三: 验证正常路由状态")
    
    print_step(12, "列出运行中的容器")
    containers = list_containers()
    containers_data = json.loads(containers)
    
    # 找到容器名称
    victim_router = None
    user_router = None
    attacker_router = None
    user_client = None
    
    for c in containers_data:
        name = c['name'].lower()
        if '150' in name and 'brd' in name:
            victim_router = c['name']
        elif '151' in name and 'brd' in name:
            user_router = c['name']
        elif '160' in name and 'brd' in name:
            attacker_router = c['name']
        elif '151' in name and 'h' in name:
            user_client = c['name']
    
    print(f"受害者路由器: {victim_router}")
    print(f"用户路由器: {user_router}")
    print(f"攻击者路由器: {attacker_router}")
    print(f"用户客户端: {user_client}")
    
    print_step(13, "检查 AS151 (用户) 的 BGP 状态")
    bgp_status = get_bgp_status(user_router)
    print(bgp_status)
    
    print_step(14, "检查 AS151 路由表 - 正常状态")
    routing_before = get_routing_table(user_router)
    print("【正常路由表】")
    print(routing_before)
    
    print_step(15, "检查到 AS150 (受害者) 网络的路由")
    looking_glass_before = get_looking_glass(user_router, "10.150.0.0/24")
    print("【正常 BGP 路由】")
    print(looking_glass_before)
    
    # =========================================================================
    # Step 4: 实施 BGP 劫持攻击
    # =========================================================================
    print_header("⚠️  阶段四: 实施 BGP 劫持攻击")
    
    print("""
    🔥 攻击说明:
    AS160 (攻击者) 将宣告 10.150.0.0/24
    这是 AS150 (受害者) 的网段
    BGP 没有验证机制，会接受这个虚假宣告
    """)
    
    print_step(16, "AS160 宣告劫持前缀 10.150.0.0/24")
    hijack_result = bgp_announce_prefix(attacker_router, "10.150.0.0/24")
    print(hijack_result)
    
    wait_with_countdown(15, "等待 BGP 收敛")
    
    # =========================================================================
    # Step 5: 验证攻击效果
    # =========================================================================
    print_header("🔍 阶段五: 验证攻击效果")
    
    print_step(17, "检查 AS151 路由表 - 攻击后")
    routing_after = get_routing_table(user_router)
    print("【攻击后路由表】")
    print(routing_after)
    
    print_step(18, "检查 BGP 路由变化")
    looking_glass_after = get_looking_glass(user_router, "10.150.0.0/24")
    print("【攻击后 BGP 路由】")
    print(looking_glass_after)
    
    print_step(19, "对比分析")
    print("\n📊 路由对比分析:")
    print("-" * 50)
    print("攻击前: 10.150.0.0/24 → AS150 (合法路由)")
    print("攻击后: 10.150.0.0/24 → AS160 (被劫持)")
    print("-" * 50)
    
    # =========================================================================
    # Step 6: 收集证据
    # =========================================================================
    print_header("📋 阶段六: 收集攻击证据")
    
    print_step(20, "从受害者路由器收集证据")
    victim_evidence = capture_evidence(victim_router, "routing_snapshot")
    print("【受害者证据】")
    print(victim_evidence[:1000])
    
    print_step(21, "从攻击者路由器收集证据")
    attacker_evidence = capture_evidence(attacker_router, "routing_snapshot")
    print("【攻击者证据】")
    print(attacker_evidence[:1000])
    
    # =========================================================================
    # 总结
    # =========================================================================
    print_header("📚 实验总结")
    print("""
    ✅ 成功演示了 BGP 劫持攻击:
    
    1. 攻击原理:
       - BGP 默认信任所有路由宣告
       - 攻击者可以宣告任意前缀
       - 没有源验证机制
    
    2. 攻击效果:
       - 流量被重定向到攻击者网络
       - 可用于流量拦截、中间人攻击
       - 可导致服务不可用
    
    3. 防御措施:
       - RPKI (资源公钥基础设施)
       - BGPsec (BGP 安全扩展)
       - 前缀过滤和验证
       - 监控和告警系统
    
    """)
    
    # =========================================================================
    # 清理
    # =========================================================================
    print_header("🧹 清理")
    
    print_step(22, "停止模拟器")
    stop_result = stop_simulation()
    print(stop_result)
    
    print_header("🎉 BGP 劫持攻击实验完成!")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

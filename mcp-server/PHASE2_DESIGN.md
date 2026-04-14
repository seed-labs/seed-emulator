# MCP Server Tools - Phase 2 Design

> Note (2026-02-10): The SeedOps "Phase 2" implemented in this repository focuses on
> **jobs / YAML playbooks / artifacts / snapshots / collector** for operating already-running networks.
> See `docs/user_manual/mcp_seedops.md` for the up-to-date user-facing guide.
>
> The sections below describe an additional roadmap for extending build-time/service tools, which is
> orthogonal to SeedOps automation.

## 已完成的工具 (Phase 1)

### 基础设施层 (5个)
- `create_as(asn)` - 创建自治系统
- `create_ix(asn, name)` - 创建互联网交换点
- `create_node(name, asn, role)` - 创建路由器或主机
- `connect_nodes(node1, node2)` - 连接节点（自动检测同AS或跨AS）
- `connect_to_ix(node, ix_asn)` - 将路由器连接到IXP

### 路由层 (3个)
- `enable_routing_layers(layers)` - 启用路由层 (routing, ospf, ebgp, ibgp, mpls)
- `configure_direct_peering(asn1, asn2, relationship)` - 配置直连BGP peering
- `configure_ix_peering(ix_asn, asn1, asn2, relationship)` - 配置IXP BGP peering

### 服务层 (2个)
- `install_service(node, type, params)` - 安装服务 (WebService, DNS)
- `render_simulation()` - 渲染仿真配置

### Docker工具 (5个)
- `compile_simulation(output_dir)` - 编译为Docker Compose
- `build_images()` - 构建Docker镜像
- `start_simulation()` - 启动容器
- `stop_simulation()` - 停止容器
- `list_containers()` - 列出容器

### 动态运行时工具 (5个)
- `exec_command(container, command)` - 执行容器命令
- `get_logs(container, tail)` - 获取容器日志
- `ping_test(src, dst, count)` - 测试连通性
- `get_routing_table(container)` - 获取路由表
- `get_bgp_status(container)` - 获取BGP状态

---

## Phase 2 计划工具

### 1. 扩展服务工具 (Service Tools Extension)

#### 1.1 Email服务 (EmailService)
```python
@mcp.tool()
def install_email_service(
    domain: str,           # 邮件域名，如 "example.com"
    asn: int,              # 所属AS
    ip: str,               # 邮件服务器IP
    gateway: str,          # 默认网关
    mode: str = "dns",     # "transport" 或 "dns" 模式
    hostname: str = "mail" # 主机名，如 mail.example.com
) -> str:
    """安装邮件服务器（基于docker-mailserver）。"""
```

#### 1.2 DHCP服务 (DHCPService)
```python
@mcp.tool()
def install_dhcp_service(
    node_name: str,        # DHCP服务器节点名
    ip_range_start: int = 100,  # DHCP地址池起始
    ip_range_end: int = 200     # DHCP地址池结束
) -> str:
    """在节点上安装DHCP服务器。"""
```

#### 1.3 Tor服务 (TorService)
```python
@mcp.tool()
def install_tor_node(
    node_name: str,
    role: str = "relay"  # "da" (directory authority), "relay", "exit", "client", "hs" (hidden service)
) -> str:
    """安装Tor节点。"""

@mcp.tool()
def configure_hidden_service(
    hs_node: str,          # 隐藏服务节点
    target_node: str,      # 目标服务节点
    target_port: int = 80  # 目标端口
) -> str:
    """配置Tor隐藏服务。"""
```

#### 1.4 DNS缓存服务 (DomainNameCachingService)
```python
@mcp.tool()
def install_dns_cache(
    node_name: str,
    upstream_dns: str = "8.8.8.8"
) -> str:
    """在节点上安装DNS缓存/递归解析器。"""
```

### 2. 网络配置工具 (Network Configuration)

#### 2.1 网络属性设置
```python
@mcp.tool()
def configure_network(
    asn: int,
    network_name: str,
    latency_ms: int = 0,      # 延迟（毫秒）
    bandwidth_mbps: int = 0,   # 带宽限制
    packet_loss: float = 0.0   # 丢包率 (0-1)
) -> str:
    """配置网络属性（延迟、带宽、丢包）。"""
```

#### 2.2 防火墙规则
```python
@mcp.tool()
def add_firewall_rule(
    node_name: str,
    rule_type: str,        # "allow", "deny", "drop"
    protocol: str = "all", # "tcp", "udp", "icmp", "all"
    port: int = 0,         # 0 = 所有端口
    direction: str = "in"  # "in", "out"
) -> str:
    """为节点添加防火墙（iptables）规则。"""
```

### 3. 状态管理工具 (State Management)

#### 3.1 保存/加载仿真
```python
@mcp.tool()
def save_simulation(filepath: str) -> str:
    """将当前仿真状态保存到文件。"""

@mcp.tool()
def load_simulation(filepath: str) -> str:
    """从文件加载仿真状态。"""
```

#### 3.2 拓扑导出
```python
@mcp.tool()
def export_topology(format: str = "json") -> str:
    """导出当前拓扑结构。支持格式: json, graphviz, mermaid"""
```

#### 3.3 生成可执行Python脚本
```python
@mcp.tool()
def export_python_script(filepath: str) -> str:
    """将当前会话的操作导出为可重放的Python脚本。"""
```

### 4. 增强动态工具 (Enhanced Dynamic Tools)

#### 4.1 流量捕获
```python
@mcp.tool()
def capture_traffic(
    container_name: str,
    interface: str = "eth0",
    duration_seconds: int = 10,
    filter: str = ""  # tcpdump过滤器
) -> str:
    """在容器中捕获网络流量。"""
```

#### 4.2 网络诊断
```python
@mcp.tool()
def traceroute(
    src_container: str,
    dst_ip: str
) -> str:
    """从源容器执行traceroute到目标IP。"""

@mcp.tool()
def get_interface_stats(container_name: str) -> str:
    """获取容器的网络接口统计信息。"""
```

#### 4.3 服务健康检查
```python
@mcp.tool()
def check_service_health(
    container_name: str,
    service_type: str  # "web", "dns", "mail", "tor"
) -> str:
    """检查容器内服务的健康状态。"""
```

### 5. 高级路由工具 (Advanced Routing)

#### 5.1 BGP路由策略
```python
@mcp.tool()
def add_bgp_filter(
    asn: int,
    neighbor_asn: int,
    filter_type: str,  # "import", "export"
    prefixes: list[str],  # 要过滤的前缀列表
    action: str = "deny"  # "allow", "deny"
) -> str:
    """添加BGP路由过滤策略。"""
```

#### 5.2 静态路由
```python
@mcp.tool()
def add_static_route(
    node_name: str,
    destination: str,  # CIDR格式，如 "10.0.0.0/8"
    next_hop: str
) -> str:
    """在节点上添加静态路由。"""
```

---

## 实施优先级

### 高优先级 (High Priority)
1. **Email服务** - 与项目名称"seed-email-service"相关
2. **网络属性配置** - 对仿真真实性很重要
3. **拓扑导出** - 帮助用户理解和保存工作
4. **traceroute** - 基本网络诊断

### 中优先级 (Medium Priority)
5. **DHCP服务** - 企业网络常用
6. **DNS缓存** - DNS架构完整性
7. **流量捕获** - 网络分析必备
8. **保存/加载仿真** - 工作持久化

### 低优先级 (Low Priority)
9. **Tor服务** - 特定安全场景
10. **防火墙规则** - 安全测试
11. **BGP过滤** - 高级路由场景
12. **静态路由** - 特殊网络配置

---

## 下一步行动

1. 从**Email服务**开始实施（符合项目主题）
2. 添加**网络配置**工具
3. 实现**拓扑导出**功能
4. 补充**traceroute**诊断工具

是否需要我开始实施这些工具？

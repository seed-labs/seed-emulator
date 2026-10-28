# 5G NR Seed-Emulator：基于 SEED 的 5G 移动性管理仿真

> 基于 SEED-Emulator，采用 Python 模块化设计，独立仿真 5G 网络 UE 注册及移动切换流程。

---

## 📖 项目简介

本项目构建了一个完整的 5G 网络仿真系统，包含 5G 核心网（AMF/SMF/UPF）、多个 gNB 基站、UE 终端，以及模拟互联网的 AS 拓扑。系统实现了从 UE 注册、PDU 会话建立、GTP-U 隧道封装，到 N6 NAT 出口的全链路仿真，并在此基础上实现了基于 Make-before-Break 的平滑移动性切换。

---

## 🏗️ 系统架构

### 拓扑分层

```
┌─────────────────────────────────────────────────────────┐
│  AS2/3/4/11/12：模拟互联网骨干（Transit AS）              │
│  提供 BGP 路由，使 gNB 和核心网通过"公网"互通              │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│  AS150：5G 核心网                                        │
│  AMF（接入与移动性管理）+ SMF（会话管理）+                 │
│  UPF（用户面功能）+ EventBus（信令总线）                  │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│  AS151~155：gNB 基站侧                                   │
│  11 个 gNB 分布在 5 个 AS 中，模拟不同地市的基站           │
└─────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────────┐
│  AS160：UE 终端侧（孤岛网络，无直接 Internet 出口）        │
│  UE 必须通过 gNB 的数据面隧道才能访问外部网络              │
└─────────────────────────────────────────────────────────┘
```

### 网元职责

| 网元 | 角色 | 关键功能 |
| :--- | :--- | :--- |
| **AMF** | 接入与移动性管理 | UE 注册、认证、N2 切换信令协调 |
| **SMF** | 会话管理 | PDU 会话建立、IP 分配、TEID 分配、路径切换 |
| **UPF** | 用户面功能 | GTP-U 解封装、N6 NAT、下行隧道转发 |
| **EventBus** | 信令总线 | ZMQ ROUTER 消息代理，N1/N2/N4/N11 接口语义 |
| **gNB** | 基站 | RRC 层、GTP-U 端点、切换处理 |
| **UE** | 终端 | NAS 状态机、RRC 连接、业务数据收发 |
| **RANLinkManager** | 数据面编排器 | Docker 网络管理、路由配置、隧道推送、切换执行 |

---

## ✨ 功能特性

### 1. 完整的 5G 控制面 + 数据面仿真

- **控制面**：基于 ZMQ 的 EventBus 实现 AMF/SMF/gNB/UE 之间的异步信令交互
- **数据面**：基于 GTP-U 隧道的用户面封装，精确模拟 N3/N6 接口
- **NAT 出口**：UPF 执行 MASQUERADE，精确模拟公共互联网场景
- **防火墙**：阻止外部主动访问 UE，符合真实 5G 公共互联网行为

### 2. Make-before-Break 平滑切换

采用 **PREPARE → COMMIT → GRACE → CLEANUP** 四阶段模型：

- **PREPARE**：按需建立目标 gNB 链路（不改变当前默认路由）
- **COMMIT**：原子替换默认路由指针（<10ms 内核操作）
- **GRACE**：旧链路保留 5 秒，让残留包排空
- **CLEANUP**：延迟释放旧链路（代际号保护，避免竞态）

### 3. 三种移动模型

- **random**：随机游走，每步 20% 概率改变方向
- **highway**：高速公路，保持方向，边界反射
- **manhattan**：曼哈顿，正交方向，随机转向

---

## 🚀 运行方式

### 1. 编译拓扑

```bash
python emulator/application.py
```

生成 `output/docker-compose.yml`。

### 2. 启动容器

```bash
cd output
docker-compose up -d --build
```

等待所有容器启动并完成初始注册。

### 3. 运行仿真

```bash
cd ..
python simulator/mobility_simulator.py run --model random --steps 20
```

**参数说明**：
- `--model`：移动模型（`random` / `highway` / `manhattan`）
- `--steps`：仿真步数

### 4. 清理环境

```bash
python simulator/mobility_simulator.py cleanup
cd output && docker compose down -v && cd ..
rm -rf output/
```

---

## 📁 目录结构

```
B33_wifi_network/
├── emulator/
│   └── application.py               # 拓扑构建脚本
├── output/                          # Docker Compose 输出
│   └── docker-compose.yml
├── runtime/
│   └── ran_link_manager.py          # 数据面编排器
├── simulator/
│   ├── mobility_simulator.py        # 移动性仿真主程序
│   ├── ue_ip_map.json               # SMF 分配的 UE IP 映射
│   ├── amf.py                       # AMF 实现
│   ├── smf.py                       # SMF 实现
│   ├── upf.py                       # UPF 实现
│   ├── gnb.py                       # gNB 实现
│   ├── ue.py                        # UE 实现
│   └── event_bus.py                 # EventBus 实现
└── wheels/                          # Python 离线安装包
```

---

## 🔑 关键机制说明

### UE 会话 IP 的分配与保持不变

```
UE 注册 → AMF 认证 → SMF 分配 IP（一次性） → 后续切换复用
```

- **SMF 维护 IP 池**：`10.60.0.2 ~ 10.60.0.253`
- **首次分配**：从池中取出一个，记录到 `ue_ip_map.json`
- **后续复用**：无论切换多少次，SMF 都不会重新分配
- **会话 IP 挂载**：RANLinkManager 通过 `ip addr add` 将 IP 配置到 UE 数据面接口

### TCP 连接保持的核心

**TCP 连接的身份是五元组**：

```
(源 IP, 源端口, 目的 IP, 目的端口, 协议)
= (10.60.0.2, 50000, 10.100.0.2, 9999, TCP)
```

切换时：
- **不变的部分**：UE 会话 IP、源端口、目的 IP、目的端口、协议、GTP-U TEID、UPF NAT 映射
- **变化的部分**：当前 gNB、gNB 物理地址、UE 数据面网卡、默认路由指针

**只要五元组不变，TCP 就认为连接连续**，底层路径切换对 TCP 完全透明。

### 切换的四阶段

```
PREPARE → COMMIT → GRACE → CLEANUP
   │         │        │        │
   │         │        │        └─ 5 秒后删除旧链路
   │         │        └────────── 旧链路保留，让残留包排空
   │         └─────────────────── 原子替换默认路由（<10ms）
   └───────────────────────────── 预建目标 gNB 链路（不改变当前路由）
```

**PREPARE**：`_prepare_link()` 建立新链路，不动默认路由
**COMMIT**：`ip route replace default` 原子切换路由指针
**GRACE**：后台线程 `sleep(5)` 保留旧路径
**CLEANUP**：删除旧路由、断开旧网络、使 IP 缓存失效

### 数据包路径（UE → 外部服务器）

```
UE ──原始 IP──▶ gNB ──GTP-U 隧道──▶ UPF ──NAT──▶ 外部服务器
                       (UDP 2152)
```

**上行**：
1. UE 生成 TCP SYN 包（`src=10.60.0.2`）
2. gNB 通过策略路由将包送入 TUN 设备
3. gNB Python 进程封装 GTP-U（TEID 标识 UE）
4. UPF 解封装，执行 NAT（`src=10.60.0.2` → `src=10.150.0.5`）
5. 从 N6 接口发出

**下行**：
1. 外部服务器回包（`dst=10.150.0.5`）
2. UPF 反向 NAT（`dst=10.150.0.5` → `dst=10.60.0.2`）
3. UPF 封装 GTP-U 发给当前 gNB
4. gNB 解封装，通过 TUN 设备 + 路由转发给 UE
5. UE 收到原始 IP 包，交给 TCP socket

---

## 🧪 验证方法

### 1. 验证 UE 能访问外部

```bash
docker exec -it <ue-000容器ID> ping 10.100.0.2
```

预期：收到 ICMP 回复。

### 2. 验证外部无法主动访问 UE

```bash
docker exec -it <as2brd-r100容器ID> ping 10.60.0.2
```

预期：100% 丢包（NAT + 防火墙双重阻隔）。

### 3. 验证 GTP-U 隧道

```bash
# 在 gNB 容器内抓包
docker exec -it <gnb-000容器ID> tcpdump -i eth1 -n udp port 2152
```

预期：看到发往 UPF 的 UDP 2152 包，内含 GTP-U 头。

### 4. 验证 TCP 保持

运行仿真，观察日志：

```json
{"event": "TCPConnectionPersisted", "ue_id": "ue-000", "from_gnb": "gnb-000", "to_gnb": "gnb-004"}
```

### 5. 验证 NAT 会话

```bash
docker exec -it <upf-000容器ID> conntrack -L -s 10.60.0.0/24
```

预期：看到 UE 的 NAT 映射表项。

---



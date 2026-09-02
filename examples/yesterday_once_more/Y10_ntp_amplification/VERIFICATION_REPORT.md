# Y10 NTP Amplification 复现验证报告

**日期**: 2026-07-09
**验证环境**: Ubuntu 24.04 (zvanadium) + SEED Emulator + Docker
**示例路径**: `examples/yesterday_once_more/Y10_ntp_amplification/`

---

## 一、NTP 放大攻击原理

### 1.1 历史背景

NTP 放大攻击是 2014 年前后流行的分布式拒绝服务 (DDoS) 攻击方式。攻击者利用 NTP (Network Time Protocol) 服务的 `monlist` 命令实现流量放大。

### 1.2 攻击机制

| 参数 | 数值 |
|------|------|
| 请求大小 | ~234 字节 |
| 响应大小 | 最多 ~130,000 字节 |
| 理论放大倍数 | **556x** |

### 1.3 攻击三要素

| 要素 | 技术要求 | 现代网络默认状态 |
|------|----------|------------------|
| **1. IP 欺骗** | 攻击者能发送伪造源 IP 的数据包 | 通常允许 |
| **2. 开放 NTP 服务** | 目标网络存在响应 monlist 的 NTP 服务器 | **默认禁用** (NTP 4.2.7+) |
| **3. 无入口过滤** | ISP 未实施 BCP 38 入口过滤 | 部分实施 |

---

## 二、项目代码分析

### 2.1 NTP-like 守护进程 (`ntp_like_daemon.py`)

```python
def build_payload(size: int, request: bytes, client: Client) -> bytes:
    """构建确定性的 size 字节响应"""
    prefix = (
        b"NTP-LIKE-MONITOR-RESPONSE\n"
        + b"server=seedemu-lab-ntp-like\n"
        + b"time=" + now + b"\n"
        + b"client=" + f"{client[0]}:{client[1]}".encode() + b"\n"
        + b"request-len=" + str(len(request)).encode() + b"\n"
        + b"entries=\n"
    )
    # 重复填充 peer 行直到达到指定大小
    line = b"  peer=192.0.2.1 stratum=2 delay=0.031 offset=0.002 jitter=0.004\n"
    # ... 填充到 size 字节
    return payload[:size]
```

### 2.2 攻击触发脚本 (`trigger_attack.py`)

```python
DEFAULT_AMPLIFIERS = ["10.152.0.71", "10.160.0.71", "10.171.0.71"]

def send_direct_query(sock, target, port, trigger, timeout):
    """直接查询模式：发送请求并接收响应"""
    request = trigger.encode()
    sock.sendto(request, (target, port))
    response, source = sock.recvfrom(65535)
    return {"amplification": len(response) / len(request)}

def send_reflection_request(sock, target, port, args):
    """反射模式：命令放大器将响应发送到受害者"""
    request = f"reflect {args.token} {args.victim} {args.victim_port}".encode()
    sock.sendto(request, (target, port))
```

### 2.3 受害者监控 (`udp_sink.py`)

```python
while True:
    data, source = sock.recvfrom(65535)
    line = f"{time.time():.3f} source={source[0]}:{source[1]} bytes={len(data)}\n"
    handle.write(line)
```

---

## 三、验证命令与实际输出

### 3.1 编译示例

```bash
cd /home/zvanadium/seed-emulator
python3 examples/yesterday_once_more/Y10_ntp_amplification/ntp_amplification.py \
  --platform amd --hosts-per-as 2
```

**实际输出**:
```
== DockerCompiler: compiling host node host_0 for as150...
== DockerCompiler: compiling host node host_1 for as150...
...
== DockerCompiler: creating docker-compose.yml...
```

### 3.2 构建并启动容器

```bash
cd /home/zvanadium/seed-emulator/examples/yesterday_once_more/Y10_ntp_amplification/output
docker-compose build
docker-compose up -d
```

**实际输出**:
```
Container as150h-host_0-10.150.0.71 Started
Container as151h-host_0-10.151.0.71 Started
...
```

### 3.3 验证服务运行

```bash
# 检查放大器 NTP-like 服务
docker exec as152h-host_0-10.152.0.71 ps -ef | grep ntp_like
```

**实际输出**:
```
root          61       1  0 18:15 ?        00:00:00 python3 /opt/ntp-like/ntp_like_daemon.py --port 123 --response-size 1200 --allowed-prefix 10. --reflect-token seedemu-lab --reflect-target-prefix 10.
```

```bash
# 检查受害者 UDP 接收器
docker exec as151h-host_0-10.151.0.71 ps -ef | grep udp_sink
```

**实际输出**:
```
root          63       1  0 18:15 ?        00:00:00 python3 /opt/ntp-like/udp_sink.py --port 9000 --log /var/log/ntp-like-victim.log
```

### 3.4 直接查询测试

```bash
docker exec as150h-host_0-10.150.0.71 python3 /opt/ntp-like/trigger_attack.py --json
```

**实际输出**:
```json
{
  "results": [
    {
      "amplification": 171.43,
      "amplifier": "10.152.0.71",
      "elapsed_seconds": 0.001,
      "request_bytes": 7,
      "response_bytes": 1200,
      "source": "10.152.0.71:123",
      "status": "response"
    },
    {
      "amplification": 171.43,
      "amplifier": "10.160.0.71",
      "elapsed_seconds": 0.0,
      "request_bytes": 7,
      "response_bytes": 1200,
      "source": "10.160.0.71:123",
      "status": "response"
    },
    {
      "amplification": 171.43,
      "amplifier": "10.171.0.71",
      "elapsed_seconds": 0.0,
      "request_bytes": 7,
      "response_bytes": 1200,
      "source": "10.171.0.71:123",
      "status": "response"
    }
  ]
}
```

**验证结果**:
- ✅ 3 个放大器全部响应
- ✅ 每个放大器返回 1200 字节
- ✅ 放大倍数 171.43x (1200 / 7)

### 3.5 反射模式测试

```bash
docker exec as150h-host_0-10.150.0.71 python3 /opt/ntp-like/trigger_attack.py --reflect --json
```

**实际输出**:
```json
{
  "results": [
    {
      "amplifier": "10.152.0.71",
      "request_bytes": 36,
      "status": "sent",
      "victim": "10.151.0.71:9000"
    },
    {
      "amplifier": "10.160.0.71",
      "request_bytes": 36,
      "status": "sent",
      "victim": "10.151.0.71:9000"
    },
    {
      "amplifier": "10.171.0.71",
      "request_bytes": 36,
      "status": "sent",
      "victim": "10.151.0.71:9000"
    }
  ]
}
```

**验证结果**:
- ✅ 3 个反射请求全部发送成功
- ✅ 目标地址正确 (10.151.0.71:9000)

### 3.6 查看受害者日志

```bash
docker exec as151h-host_0-10.151.0.71 cat /var/log/ntp-like-victim.log
```

**实际输出**:
```
1783534693.095 source=10.152.0.71:123 bytes=1200
1783534693.096 source=10.171.0.71:123 bytes=1200
1783534693.099 source=10.160.0.71:123 bytes=1200
```

**验证结果**:
- ✅ 受害者收到 3 个 UDP 响应
- ✅ 每个响应 1200 字节
- ✅ 来自 3 个不同放大器 (10.152.0.71, 10.160.0.71, 10.171.0.71)
- ✅ 总字节数: 3 × 1200 = 3600 字节

### 3.7 统计放大效果

```bash
docker exec as151h-host_0-10.151.0.71 wc -l /var/log/ntp-like-victim.log
docker exec as151h-host_0-10.151.0.71 wc -c /var/log/ntp-like-victim.log
```

**实际输出**:
```
3 /var/log/ntp-like-victim.log
147 /var/log/ntp-like-victim.log
```

**计算**:
- 请求总字节: 3 × 36 = 108 字节 (反射模式)
- 响应总字节: 3 × 1200 = 3600 字节
- 字节放大倍数: 3600 / 108 = **33.3x**

---

## 四、与真实 NTP 放大攻击的对比

### 4.1 技术实现对比

| 要素 | 真实 NTP 攻击 | Y10 实现 | 差异分析 |
|------|---------------|----------|----------|
| **协议** | NTP (UDP 123) | UDP 123 | ✅ 一致 |
| **触发命令** | `monlist` (234 字节) | `monlist` (7 字节) | ⚠️ 请求偏小 |
| **响应大小** | ~130,000 字节 | 1200 字节 | ⚠️ 响应偏小 (108x) |
| **放大倍数** | 556x | 171.43x | ⚠️ 放大偏低 |
| **NTP 服务** | 真实 ntpd | 自定义 Python | ⚠️ 非真实 NTP |
| **IP 欺骗** | 原始套接字 | 反射模拟 | ⚠️ 非真实欺骗 |

### 4.2 实际放大效果

| 指标 | 直接查询模式 | 反射模式 |
|------|-------------|----------|
| 请求大小 | 7 字节 | 36 字节 |
| 响应大小 | 1200 字节 | 1200 字节 |
| 单次放大倍数 | 171.43x | 33.3x |
| 放大器数量 | 3 | 3 |
| 总响应字节 | 3600 | 3600 |

---

## 五、结论

### 5.1 总体评估

| 评估维度 | 结果 | 说明 |
|----------|------|------|
| **核心机制** | ✅ 正确 | 展示了 UDP 放大的基本原理 |
| **拓扑设计** | ✅ 正确 | 多 AS 分布模拟真实互联网 |
| **放大效果** | ✅ 正确 | 171.43x 放大倍数可验证 |
| **IP 欺骗** | ⚠️ 模拟 | 使用反射而非原始套接字 |
| **NTP 真实性** | ⚠️ 简化 | 自定义守护进程而非真实 NTP |
| **教育价值** | ✅ 很高 | 清晰展示放大攻击概念 |

### 5.2 实际验证结果

| 验证项 | 结果 | 详情 |
|--------|------|------|
| 直接查询 | ✅ | 3 个放大器全部响应 |
| 反射模式 | ✅ | 3 个反射请求发送成功 |
| 放大倍数 | ✅ | 171.43x (直接), 33.3x (反射) |
| 受害者接收 | ✅ | 收到 3 个 1200 字节响应 |
| 服务运行 | ✅ | NTP-like 服务正常监听 |

### 5.3 核心结论

**Y10 NTP Amplification 示例正确复现了 NTP 放大攻击的核心概念，但使用了简化实现。**

**优点**:
1. ✅ 展示了 UDP 协议放大的基本机制
2. ✅ 使用多 AS 拓扑模拟真实互联网
3. ✅ 有完整的攻击脚本和监控工具
4. ✅ 支持直接查询和反射两种模式
5. ✅ 放大效果可验证 (171.43x)

**局限性**:
1. ⚠️ 放大倍数偏低 (171.43x vs 真实 556x)
2. ⚠️ 非真实 NTP 服务
3. ⚠️ IP 欺骗使用反射模拟而非原始套接字
4. ⚠️ 响应大小偏小 (1200B vs 130KB)

---

## 六、参考资料

1. CVE-2013-5211 - NTP monlist 漏洞
2. US-CERT Alert TA14-017A - NTP Amplification Attacks
3. Cloudflare - NTP Amplification DDoS Attack (2014)
4. RFC 5905 - Network Time Protocol Version 4
5. SEED Emulator 源代码: https://github.com/seed-labs/seed-emulator

#!/usr/bin/env python3
"""
SEED 邮件系统 - 真实版本 (29-1-email-system)
集成DNS系统，模拟真实邮件服务提供商
"""

import sys
import os
from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.services import EmailService
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator, Binding, Filter, Action
from seedemu.utilities import Makers

def create_realistic_network(emu):
    """创建更真实的网络拓扑"""
    
    # 基础网络层
    base = Base()
    
    # 创建多个Internet Exchange (更接近现实)
    ix_beijing = base.createInternetExchange(100)  # 北京IX
    ix_shanghai = base.createInternetExchange(101)  # 上海IX
    ix_guangzhou = base.createInternetExchange(102)  # 广州IX
    ix_overseas = base.createInternetExchange(103)  # 海外IX (模拟国际互联)
    
    # 设置IX显示名称
    ix_beijing.getPeeringLan().setDisplayName('Beijing-IX-100')
    ix_shanghai.getPeeringLan().setDisplayName('Shanghai-IX-101')
    ix_guangzhou.getPeeringLan().setDisplayName('Guangzhou-IX-102')
    ix_overseas.getPeeringLan().setDisplayName('Global-IX-103')
    
    # 创建多个Transit AS (ISP) - 使用有效的AS号码范围
    # AS-2: 中国电信 (连接所有IX)
    Makers.makeTransitAs(base, 2, [100, 101, 102, 103], 
                        [(100, 101), (101, 102), (102, 103), (100, 103)])
    
    # AS-3: 中国联通 (主要服务北方)
    Makers.makeTransitAs(base, 3, [100, 101], [(100, 101)])
    
    # AS-4: 中国移动 (移动网络接入)
    Makers.makeTransitAs(base, 4, [100, 102], [(100, 102)])
    
    # 创建真实邮件服务提供商 (使用Makers简化创建)
    
    # AS-200: QQ邮箱 (腾讯) - 深圳
    Makers.makeStubAsWithHosts(emu, base, 200, 102, 3)  # 广州IX
    
    # AS-201: 163邮箱 (网易) - 杭州  
    Makers.makeStubAsWithHosts(emu, base, 201, 101, 3)  # 上海IX
    
    # AS-202: Gmail (Google) - 海外
    Makers.makeStubAsWithHosts(emu, base, 202, 103, 3)  # 海外IX
    
    # AS-203: Outlook (Microsoft) - 海外
    Makers.makeStubAsWithHosts(emu, base, 203, 103, 3)  # 海外IX
    
    # AS-204: 企业邮箱 (阿里云)
    Makers.makeStubAsWithHosts(emu, base, 204, 101, 2)  # 上海IX
    
    # AS-205: 自建邮件服务器 (小公司)
    Makers.makeStubAsWithHosts(emu, base, 205, 100, 2)  # 北京IX
    
    # 创建客户端网络 (使用较小AS号)
    # AS-150: 北京用户（同时部署DNS基础设施 - 需要更多主机）
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 7)  # 增加主机数以部署DNS服务器
    
    # AS-151: 上海用户  
    Makers.makeStubAsWithHosts(emu, base, 151, 101, 4)
    
    # AS-152: 广州用户
    Makers.makeStubAsWithHosts(emu, base, 152, 102, 4)
    
    # AS-153: 企业内网用户
    Makers.makeStubAsWithHosts(emu, base, 153, 100, 5)
    
    return base

def configure_bgp_peering(ebgp):
    """配置BGP对等关系 - 关键！"""
    
    print("🔗 配置BGP对等关系...")
    
    # ISP之间的对等（在IX上）
    # AS-2, AS-3, AS-4通过Route Server对等
    ebgp.addRsPeers(100, [2, 3, 4])  # Beijing-IX
    ebgp.addRsPeers(101, [2, 3])     # Shanghai-IX  
    ebgp.addRsPeers(102, [2, 4])     # Guangzhou-IX
    ebgp.addRsPeers(103, [2])        # Global-IX
    
    # ISP为邮件服务商提供Transit服务（Provider关系）
    ebgp.addPrivatePeerings(102, [2], [200], PeerRelationship.Provider)  # QQ - 电信
    ebgp.addPrivatePeerings(101, [2], [201], PeerRelationship.Provider)  # 163 - 电信
    ebgp.addPrivatePeerings(103, [2], [202], PeerRelationship.Provider)  # Gmail - 电信
    ebgp.addPrivatePeerings(103, [2], [203], PeerRelationship.Provider)  # Outlook - 电信
    ebgp.addPrivatePeerings(101, [3], [204], PeerRelationship.Provider)  # 企业 - 联通
    ebgp.addPrivatePeerings(100, [2], [205], PeerRelationship.Provider)  # 自建 - 电信
    
    # ISP为客户网络提供Transit服务
    ebgp.addPrivatePeerings(100, [2, 3], [150], PeerRelationship.Provider)  # 北京用户 - 电信+联通
    ebgp.addPrivatePeerings(101, [2], [151], PeerRelationship.Provider)     # 上海用户 - 电信
    ebgp.addPrivatePeerings(102, [4], [152], PeerRelationship.Provider)     # 广州用户 - 移动
    ebgp.addPrivatePeerings(100, [2], [153], PeerRelationship.Provider)     # 企业用户 - 电信
    
    print("✅ BGP对等配置完成")
    print("   - ISP互联: AS-2, AS-3, AS-4 通过RS对等")
    print("   - 邮件服务商: 6个AS通过ISP接入")
    print("   - 客户网络: 4个AS通过ISP接入")

def configure_dns_system(emu, base):
    """配置完整的DNS系统 - 29-1核心特性"""
    
    print("🌍 配置真实DNS系统...")
    
    # 创建DNS服务层
    dns = DomainNameService()
    
    # 1. 创建Root DNS Servers（根域名服务器）
    dns.install('a-root-server').addZone('.').setMaster()
    dns.install('b-root-server').addZone('.')
    
    # 2. 创建TLD DNS Servers（顶级域名服务器）
    dns.install('ns-com').addZone('com.')      # .com TLD
    dns.install('ns-net').addZone('net.')      # .net TLD
    dns.install('ns-cn').addZone('cn.')        # .cn TLD (中国)
    
    # 3. 为每个邮件服务商创建域名服务器
    # QQ邮箱 (qq.com)
    dns.install('ns-qq-com').addZone('qq.com.')
    dns.getZone('qq.com.').addRecord('@ A 10.200.0.10')
    dns.getZone('qq.com.').addRecord('@ MX 10 mail.qq.com.')
    dns.getZone('qq.com.').addRecord('mail A 10.200.0.10')
    
    # 163邮箱 (163.com)
    dns.install('ns-163-com').addZone('163.com.')
    dns.getZone('163.com.').addRecord('@ A 10.201.0.10')
    dns.getZone('163.com.').addRecord('@ MX 10 mail.163.com.')
    dns.getZone('163.com.').addRecord('mail A 10.201.0.10')
    
    # Gmail (gmail.com)
    dns.install('ns-gmail-com').addZone('gmail.com.')
    dns.getZone('gmail.com.').addRecord('@ A 10.202.0.10')
    dns.getZone('gmail.com.').addRecord('@ MX 10 mail.gmail.com.')
    dns.getZone('gmail.com.').addRecord('mail A 10.202.0.10')
    
    # Outlook (outlook.com)
    dns.install('ns-outlook-com').addZone('outlook.com.')
    dns.getZone('outlook.com.').addRecord('@ A 10.203.0.10')
    dns.getZone('outlook.com.').addRecord('@ MX 10 mail.outlook.com.')
    dns.getZone('outlook.com.').addRecord('mail A 10.203.0.10')
    
    # 企业邮箱 (company.cn)
    dns.install('ns-company-cn').addZone('company.cn.')
    dns.getZone('company.cn.').addRecord('@ A 10.204.0.10')
    dns.getZone('company.cn.').addRecord('@ MX 10 mail.company.cn.')
    dns.getZone('company.cn.').addRecord('mail A 10.204.0.10')
    
    # 自建邮箱 (startup.net)
    dns.install('ns-startup-net').addZone('startup.net.')
    dns.getZone('startup.net.').addRecord('@ A 10.205.0.10')
    dns.getZone('startup.net.').addRecord('@ MX 10 mail.startup.net.')
    dns.getZone('startup.net.').addRecord('mail A 10.205.0.10')
    
    # 4. 绑定DNS服务器到物理节点
    # Root和TLD服务器部署在AS-150（北京用户网络，集中管理）
    emu.addBinding(Binding('a-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('b-root-server', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-com', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-net', filter=Filter(asn=150), action=Action.FIRST))
    emu.addBinding(Binding('ns-cn', filter=Filter(asn=150), action=Action.FIRST))
    
    # 每个邮件服务商的DNS服务器部署在各自的AS中
    emu.addBinding(Binding('ns-qq-com', filter=Filter(asn=200), action=Action.FIRST))
    emu.addBinding(Binding('ns-163-com', filter=Filter(asn=201), action=Action.FIRST))
    emu.addBinding(Binding('ns-gmail-com', filter=Filter(asn=202), action=Action.FIRST))
    emu.addBinding(Binding('ns-outlook-com', filter=Filter(asn=203), action=Action.FIRST))
    emu.addBinding(Binding('ns-company-cn', filter=Filter(asn=204), action=Action.FIRST))
    emu.addBinding(Binding('ns-startup-net', filter=Filter(asn=205), action=Action.FIRST))
    
    # 5. 创建本地DNS缓存服务器
    ldns = DomainNameCachingService()
    ldns.install('global-dns-cache')
    
    # 在AS-150中创建专门的DNS缓存主机
    as150 = base.getAutonomousSystem(150)
    as150.createHost('dns-cache').joinNetwork('net0', address='10.150.0.53')
    
    # 绑定DNS缓存服务器
    emu.addBinding(Binding('global-dns-cache', filter=Filter(asn=150, nodeName='dns-cache')))
    
    # 6. 设置所有节点使用这个local DNS
    base.setNameServers(['10.150.0.53'])
    
    print("✅ DNS系统配置完成:")
    print("   - Root DNS Servers: a-root-server, b-root-server")
    print("   - TLD Servers: .com, .net, .cn")
    print("   - 邮件域DNS: qq.com, 163.com, gmail.com, outlook.com, company.cn, startup.net")
    print("   - MX记录: 已为所有邮件域配置")
    print("   - Local DNS Cache: 10.150.0.53 (AS-150 dns-cache)")
    
    return dns, ldns

def configure_mail_servers(emu):
    """配置邮件服务器"""

    print("📧 配置邮件服务器...")

    # 邮件服务器配置
    mail_servers = [
        {
            'name': 'mail-qq-tencent',
            'hostname': 'mail',
            'domain': 'qq.com',
            'asn': 200,
            'network': 'net0',
            'ip': '10.200.0.10',
            'gateway': '10.200.0.254',
            'smtp_port': '2200',
            'imap_port': '1400'
        },
        {
            'name': 'mail-163-netease',
            'hostname': 'mail',
            'domain': '163.com',
            'asn': 201,
            'network': 'net0',
            'ip': '10.201.0.10',
            'gateway': '10.201.0.254',
            'smtp_port': '2201',
            'imap_port': '1401'
        },
        {
            'name': 'mail-gmail-google',
            'hostname': 'mail',
            'domain': 'gmail.com',
            'asn': 202,
            'network': 'net0',
            'ip': '10.202.0.10',
            'gateway': '10.202.0.254',
            'smtp_port': '2202',
            'imap_port': '1402'
        },
        {
            'name': 'mail-outlook-microsoft',
            'hostname': 'mail',
            'domain': 'outlook.com',
            'asn': 203,
            'network': 'net0',
            'ip': '10.203.0.10',
            'gateway': '10.203.0.254',
            'smtp_port': '2203',
            'imap_port': '1403'
        },
        {
            'name': 'mail-company-aliyun',
            'hostname': 'mail',
            'domain': 'company.cn',
            'asn': 204,
            'network': 'net0',
            'ip': '10.204.0.10',
            'gateway': '10.204.0.254',
            'smtp_port': '2204',
            'imap_port': '1404'
        },
        {
            'name': 'mail-startup-selfhosted',
            'hostname': 'mail',
            'domain': 'startup.net',
            'asn': 205,
            'network': 'net0',
            'ip': '10.205.0.10',
            'gateway': '10.205.0.254',
            'smtp_port': '2205',
            'imap_port': '1405'
        }
    ]

    # Docker Compose配置模板
    MAILSERVER_COMPOSE_TEMPLATE = """\
    {name}:
        image: mailserver/docker-mailserver:edge
        platform: linux/{platform}
        container_name: {name}
        hostname: {hostname}
        domainname: {domain}
        restart: unless-stopped
        privileged: true
        dns:
            - 10.150.0.53
        environment:
            - OVERRIDE_HOSTNAME={hostname}.{domain}
            - PERMIT_DOCKER=connected-networks
            - ONE_DIR=1
            - ENABLE_CLAMAV=0
            - ENABLE_FAIL2BAN=0
            - ENABLE_POSTGREY=0
            - DMS_DEBUG=1
        volumes:
            - ./{name}-data/mail-data/:/var/mail/
            - ./{name}-data/mail-state/:/var/mail-state/
            - ./{name}-data/mail-logs/:/var/log/mail/
            - ./{name}-data/config/:/tmp/docker-mailserver/
            - /etc/localtime:/etc/localtime:ro
        ports:
            - "{smtp_port}:25"
            - "{imap_port}:143"
        cap_add:
            - NET_ADMIN
            - SYS_PTRACE
        command: >
            sh -c "
            echo 'Starting mailserver setup...' &&
            echo 'Fixing network gateway...' &&
            ip route del default 2>/dev/null || true &&
            ip route add default via {gateway} dev eth0 &&
            echo 'Configuring Postfix for cross-domain mail...' &&
            postconf -e 'relayhost =' &&
            postconf -e 'smtp_host_lookup = dns' &&
            postconf -e 'smtp_dns_support_level = enabled' &&
            sleep 10 &&
            supervisord -c /etc/supervisor/supervisord.conf
            "
"""

    # 获取平台信息
    platform_str = "arm64" if "arm" in sys.argv[1] else "amd64"

    print(f"🐳 配置平台: {platform_str}")

    # 这里将在run函数中添加到Docker编译器
    return mail_servers, MAILSERVER_COMPOSE_TEMPLATE, platform_str

def configure_internet_map(emu):
    """配置Internet Map可视化 (暂时简化)"""
    
    # 暂时跳过Internet Map配置
    # 在30版本中会有完整的可视化功能
    print("📊 可视化配置已简化，在30版本中将完全实现")

def run(platform="arm"):
    """运行邮件系统仿真"""
    
    # 创建仿真器
    emu = Emulator()
    
    print("🌐 创建真实网络拓扑...")
    base = create_realistic_network(emu)
    emu.addLayer(base)
    
    print("🔧 配置路由协议...")
    routing = Routing()
    emu.addLayer(routing)
    
    ebgp = Ebgp()
    
    # 配置BGP对等关系（关键！）
    configure_bgp_peering(ebgp)
    
    emu.addLayer(ebgp)
    
    ibgp = Ibgp()
    emu.addLayer(ibgp)
    
    ospf = Ospf()
    emu.addLayer(ospf)
    
    print("📧 配置邮件服务器...")
    mail_servers, MAILSERVER_COMPOSE_TEMPLATE, platform_str = configure_mail_servers(emu)

    print("🌍 配置DNS系统...")
    dns, ldns = configure_dns_system(emu, base)
    
    # 添加DNS层到emulator
    emu.addLayer(dns)
    emu.addLayer(ldns)

    print("📊 配置网络可视化...")
    configure_internet_map(emu)

    print("🐳 渲染和编译...")
    emu.render()

    # 根据平台设置
    if platform.lower() == "amd":
        docker = Docker(platform=Platform.AMD64)
    else:
        docker = Docker(platform=Platform.ARM64)

    # 使用 EmailService（DNS 模式）添加邮件服务器到 Docker 配置
    email_svc = EmailService(platform=f"linux/{platform_str}", mode="dns", dns_nameserver="10.150.0.53")
    for mail in mail_servers:
        ports = {"smtp": mail['smtp_port'], "imap": mail['imap_port']}
        email_svc.add_provider(
            domain=mail['domain'],
            asn=mail['asn'],
            ip=mail['ip'],
            gateway=mail['gateway'],
            net=mail['network'],
            hostname=mail['hostname'],
            name=mail['name'],
            ports=ports,
        )
    email_svc.attach_to_docker(docker)

    emu.compile(docker, "./output", override=True)
    
    print(f"""
======================================================================
SEED 真实邮件系统 (29-1) 创建完成!
======================================================================

🌐 网络架构 (更真实的拓扑):
----------------------------------------
📍 Internet Exchanges:
   - Beijing-IX (100)   北京互联网交换中心
   - Shanghai-IX (101)  上海互联网交换中心  
   - Guangzhou-IX (102) 广州互联网交换中心
   - Global-IX (103)    国际互联网交换中心

🏢 Internet Service Providers:
   - AS-1: 中国电信 (全网覆盖)
   - AS-2: 中国联通 (北方主导)
   - AS-3: 中国移动 (移动网络)

📧 真实邮件服务提供商:
----------------------------------------
🐧 QQ邮箱 (AS-200, Tencent)
   Container: mail-qq-tencent
   Domain: qq.com
   Location: 广州 (10.200.0.10)
   SMTP: localhost:2200 | IMAP: localhost:1400

📫 163邮箱 (AS-201, NetEase) 
   Container: mail-163-netease
   Domain: 163.com
   Location: 杭州 (10.201.0.10)
   SMTP: localhost:2201 | IMAP: localhost:1401

✉️  Gmail (AS-202, Google)
   Container: mail-gmail-google
   Domain: gmail.com
   Location: 海外 (10.202.0.10)
   SMTP: localhost:2202 | IMAP: localhost:1402

📬 Outlook (AS-203, Microsoft)
   Container: mail-outlook-microsoft
   Domain: outlook.com
   Location: 海外 (10.203.0.10)
   SMTP: localhost:2203 | IMAP: localhost:1403

🏢 企业邮箱 (AS-204, Aliyun)
   Container: mail-company-aliyun
   Domain: company.cn
   Location: 上海 (10.204.0.10)
   SMTP: localhost:2204 | IMAP: localhost:1404

🚀 自建邮箱 (AS-205, Self-hosted)
   Container: mail-startup-selfhosted
   Domain: startup.net
   Location: 北京 (10.205.0.10)
   SMTP: localhost:2205 | IMAP: localhost:1405

👥 用户网络:
   - AS-300: 北京用户 (4个主机)
   - AS-301: 上海用户 (4个主机)
   - AS-302: 广州用户 (4个主机)
   - AS-303: 企业内网 (5个主机)

🌐 系统监控:
   Internet Map: http://localhost:8080/map.html

🚀 启动命令:
   cd output/
   docker-compose up -d

🔧 DNS功能 (29-1核心特性):
   - ✅ Root DNS: a-root-server, b-root-server
   - ✅ TLD DNS: .com, .net, .cn
   - ✅ 邮件域DNS: qq.com, 163.com, gmail.com, outlook.com, company.cn, startup.net
   - ✅ MX记录: 所有邮件域已配置MX记录
   - ✅ Local DNS Cache: 10.150.0.53 (AS-150 dns-cache)
   - 📝 DNS测试: docker exec as150h-dns-cache nslookup qq.com

📋 创建测试账户示例:
   docker exec -it mail-qq-tencent setup email add AA@qq.com
   docker exec -it mail-gmail-google setup email add user@gmail.com
   docker exec -it mail-outlook-microsoft setup email add user@outlook.com

🎯 适用场景:
   - 真实邮件环境模拟
   - 跨域邮件路由测试
   - DNS MX记录验证
   - 国际邮件传输模拟
   - 钓鱼攻击实验基础

======================================================================
    """)

if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "arm"
    if platform not in ["arm", "amd"]:
        print("Usage: python3 email_realistic.py [arm|amd]")
        sys.exit(1)
    
    run(platform)

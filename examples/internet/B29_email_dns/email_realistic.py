#!/usr/bin/env python3
"""
SEED 邮件系统 - 真实版本 (29-1-email-system)
集成DNS系统，模拟真实邮件服务提供商
"""

import sys
import os
from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.services import DomainNameService, DomainNameCachingService
from seedemu.services.EmailService import EmailService
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
    """Configure BGP peerings"""
    
    print("🔗 Configuring BGP peerings...")
    
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
    ebgp.addPrivatePeerings(101, [2], [204], PeerRelationship.Provider)  # 企业 - 电信 (改为电信以确保与AS-205互通)
    ebgp.addPrivatePeerings(100, [2], [205], PeerRelationship.Provider)  # 自建 - 电信
    
    # ISP为客户网络提供Transit服务
    ebgp.addPrivatePeerings(100, [2, 3], [150], PeerRelationship.Provider)  # 北京用户 - 电信+联通
    ebgp.addPrivatePeerings(101, [2], [151], PeerRelationship.Provider)     # 上海用户 - 电信
    ebgp.addPrivatePeerings(102, [4], [152], PeerRelationship.Provider)     # 广州用户 - 移动
    ebgp.addPrivatePeerings(100, [2], [153], PeerRelationship.Provider)     # 企业用户 - 电信
    
    print("✅ BGP peering configuration complete")
    print("   - ISP interconnect: AS-2, AS-3, AS-4 via route servers")
    print("   - Mail providers: 6 AS connected via ISPs")
    print("   - Customer networks: 4 AS connected via ISPs")

def configure_dns_system(emu, base):
    """Configure full DNS system (authoritative + caches)"""
    
    print("🌍 Configuring DNS system...")
    
    # 创建DNS服务层
    dns = DomainNameService()
    
    # 1. 创建Root DNS Servers（根域名服务器）
    dns.install('a-root-server').addZone('.').setMaster()
    dns.install('b-root-server').addZone('.')
    
    # 2. 创建TLD DNS Servers（顶级域名服务器）
    dns.install('ns-com').addZone('com.').setMaster()      # .com TLD
    dns.install('ns-net').addZone('net.').setMaster()      # .net TLD
    dns.install('ns-cn').addZone('cn.').setMaster()        # .cn TLD (中国)
    
    # 3. 为每个邮件服务商创建域名服务器
    # QQ邮箱 (qq.com)
    dns.install('ns-qq-com').addZone('qq.com.').setMaster()
    dns.getZone('qq.com.').addRecord('@ A 10.200.0.10')
    dns.getZone('qq.com.').addRecord('@ MX 10 mail.qq.com.')
    dns.getZone('qq.com.').addRecord('mail A 10.200.0.10')
    
    # 163邮箱 (163.com)
    dns.install('ns-163-com').addZone('163.com.').setMaster()
    dns.getZone('163.com.').addRecord('@ A 10.201.0.10')
    dns.getZone('163.com.').addRecord('@ MX 10 mail.163.com.')
    dns.getZone('163.com.').addRecord('mail A 10.201.0.10')
    
    # Gmail (gmail.com)
    dns.install('ns-gmail-com').addZone('gmail.com.').setMaster()
    dns.getZone('gmail.com.').addRecord('@ A 10.202.0.10')
    dns.getZone('gmail.com.').addRecord('@ MX 10 mail.gmail.com.')
    dns.getZone('gmail.com.').addRecord('mail A 10.202.0.10')
    
    # Outlook (outlook.com)
    dns.install('ns-outlook-com').addZone('outlook.com.').setMaster()
    dns.getZone('outlook.com.').addRecord('@ A 10.203.0.10')
    dns.getZone('outlook.com.').addRecord('@ MX 10 mail.outlook.com.')
    dns.getZone('outlook.com.').addRecord('mail A 10.203.0.10')
    
    # 企业邮箱 (company.cn)
    dns.install('ns-company-cn').addZone('company.cn.').setMaster()
    dns.getZone('company.cn.').addRecord('@ A 10.204.0.10')
    dns.getZone('company.cn.').addRecord('@ MX 10 mail.company.cn.')
    dns.getZone('company.cn.').addRecord('mail A 10.204.0.10')
    
    # 自建邮箱 (startup.net)
    dns.install('ns-startup-net').addZone('startup.net.').setMaster()
    dns.getZone('startup.net.').addRecord('@ A 10.205.0.10')
    dns.getZone('startup.net.').addRecord('@ MX 10 mail.startup.net.')
    dns.getZone('startup.net.').addRecord('mail A 10.205.0.10')
    
    # 4. 为权威DNS创建专用新主机（Action.NEW），确保 bind9 安装与启动
    # AS-150: root 与 TLD 使用独立专用主机
    emu.addBinding(Binding('^a-root-server$', action=Action.NEW, filter=Filter(asn=150, nodeName='dns-auth-root-a')))
    emu.addBinding(Binding('^b-root-server$', action=Action.NEW, filter=Filter(asn=150, nodeName='dns-auth-root-b')))
    emu.addBinding(Binding('^ns-com$',        action=Action.NEW, filter=Filter(asn=150, nodeName='dns-auth-com')))
    emu.addBinding(Binding('^ns-net$',        action=Action.NEW, filter=Filter(asn=150, nodeName='dns-auth-net')))
    emu.addBinding(Binding('^ns-cn$',         action=Action.NEW, filter=Filter(asn=150, nodeName='dns-auth-cn')))

    # 各提供商 AS: 为各自域创建专用权威主机
    emu.addBinding(Binding('^ns-qq-com$',      action=Action.NEW, filter=Filter(asn=200, nodeName='dns-auth-qq')))
    emu.addBinding(Binding('^ns-163-com$',     action=Action.NEW, filter=Filter(asn=201, nodeName='dns-auth-163')))
    emu.addBinding(Binding('^ns-gmail-com$',   action=Action.NEW, filter=Filter(asn=202, nodeName='dns-auth-gmail')))
    emu.addBinding(Binding('^ns-outlook-com$', action=Action.NEW, filter=Filter(asn=203, nodeName='dns-auth-outlook')))
    emu.addBinding(Binding('^ns-company-cn$',  action=Action.NEW, filter=Filter(asn=204, nodeName='dns-auth-company')))
    emu.addBinding(Binding('^ns-startup-net$', action=Action.NEW, filter=Filter(asn=205, nodeName='dns-auth-startup')))
    
    # 5. 创建本地DNS缓存服务器
    ldns = DomainNameCachingService()
    cache = ldns.install('global-dns-cache')
    cache.addForwardZone('com.', 'ns-com')
    cache.addForwardZone('net.', 'ns-net')
    cache.addForwardZone('cn.', 'ns-cn')
    # 直接将邮件域转发到其权威NS，避免依赖根与TLD可用性
    cache.addForwardZone('qq.com.', 'ns-qq-com')
    cache.addForwardZone('163.com.', 'ns-163-com')
    cache.addForwardZone('gmail.com.', 'ns-gmail-com')
    cache.addForwardZone('outlook.com.', 'ns-outlook-com')
    cache.addForwardZone('company.cn.', 'ns-company-cn')
    cache.addForwardZone('startup.net.', 'ns-startup-net')
    
    # 在AS-150中创建专门的DNS缓存主机
    base.getAutonomousSystem(150).createHost('dns-cache').joinNetwork('net0', address='10.150.0.53')
    
    # 绑定DNS缓存服务器
    emu.addBinding(Binding('global-dns-cache', filter=Filter(asn=150, nodeName='dns-cache')))

    # 为每个邮件服务商所在AS创建本地DNS缓存，避免跨AS访问10.150.0.53
    # 仅转发六个邮件域到其权威NS，减少依赖
    domain_forwarders = [
        ('qq.com.', 'ns-qq-com'),
        ('163.com.', 'ns-163-com'),
        ('gmail.com.', 'ns-gmail-com'),
        ('outlook.com.', 'ns-outlook-com'),
        ('company.cn.', 'ns-company-cn'),
        ('startup.net.', 'ns-startup-net'),
    ]
    for asn in [200, 201, 202, 203, 204, 205]:
        vname = f'dns-cache-{asn}'
        c = ldns.install(vname)
        for z, nsname in domain_forwarders:
            c.addForwardZone(z, nsname)
        asx = base.getAutonomousSystem(asn)
        asx.createHost('dns-cache').joinNetwork('net0', address=f'10.{asn}.0.53')
        emu.addBinding(Binding(vname, filter=Filter(asn=asn, nodeName='dns-cache')))
    
    # 6. 设置所有节点使用这个local DNS
    base.setNameServers(['10.150.0.53'])
    
    print("✅ DNS configuration complete:")
    print("   - Root DNS: a-root-server, b-root-server")
    print("   - TLD: .com, .net, .cn")
    print("   - Mail zones: qq.com, 163.com, gmail.com, outlook.com, company.cn, startup.net")
    print("   - MX records: configured for all mail zones")
    print("   - Local DNS Cache: 10.150.0.53 (AS-150 dns-cache)")
    
    return dns, ldns

def configure_mail_servers(emu):
    """Configure mail servers"""

    print("📧 Configuring mail servers...")

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

    # Auto-detect platform from uname
    arch = os.uname().machine if hasattr(os, 'uname') else ''
    platform_str = 'arm64' if arch in ('aarch64', 'arm64') else 'amd64'

    print(f"🐳 Using platform: {platform_str}")

    # Return to be used by run()
    return mail_servers, MAILSERVER_COMPOSE_TEMPLATE, platform_str

def configure_internet_map(emu):
    """Configure Internet Map visualization (simplified)"""
    
    # Visualization simplified for now; full support in v30
    print("📊 Visualization setup is simplified; full support planned in v30")

def run(platform="auto"):
    """Run the email system emulation"""
    
    # Create emulator
    emu = Emulator()
    
    print("🌐 Building realistic network topology...")
    base = create_realistic_network(emu)
    emu.addLayer(base)
    
    print("🔧 Configuring routing protocols...")
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
    
    print("📧 Configuring mail servers...")
    mail_servers, MAILSERVER_COMPOSE_TEMPLATE, platform_str = configure_mail_servers(emu)

    print("🌍 Configuring DNS system...")
    dns, ldns = configure_dns_system(emu, base)
    
    # 添加DNS层到emulator
    emu.addLayer(dns)
    emu.addLayer(ldns)

    print("📊 Configuring visualization...")
    configure_internet_map(emu)

    print("🐳 Rendering and compiling...")
    emu.render()

    # Select Docker platform
    arch = os.uname().machine if hasattr(os, 'uname') else ''
    auto_plat = Platform.ARM64 if arch in ('aarch64', 'arm64') else Platform.AMD64
    p = (platform or 'auto').lower()
    if p in ("amd", "amd64", "x86_64"):
        docker = Docker(platform=Platform.AMD64)
    elif p in ("arm", "arm64", "aarch64"):
        docker = Docker(platform=Platform.ARM64)
    else:
        docker = Docker(platform=auto_plat)

    # 使用 EmailService（transport 模式）添加邮件服务器到 Docker 配置（绕过DNS，确保跨域稳定）
    email_svc = EmailService(platform=f"linux/{platform_str}", mode="transport", dns_nameserver="10.150.0.53")
    for mail in mail_servers:
        # 为每个提供商分配唯一的 submission/imaps 端口，避免 587/993 端口冲突
        offset = int(mail['asn']) - 200  # 200..205 -> 0..5
        submission_port = str(5870 + offset)
        imaps_port = str(9930 + offset)
        ports = {
            "smtp": mail['smtp_port'],
            "submission": submission_port,
            "imap": mail['imap_port'],
            "imaps": imaps_port,
        }
        email_svc.add_provider(
            domain=mail['domain'],
            asn=mail['asn'],
            ip=mail['ip'],
            gateway=mail['gateway'],
            net=mail['network'],
            hostname=mail['hostname'],
            name=mail['name'],
            ports=ports,
            dns=f"10.{mail['asn']}.0.53",
        )
    email_svc.attach_to_docker(docker)

    emu.compile(docker, "./output", override=True)
    emu.updateOutputDirectory(docker, email_svc.get_output_callbacks())
    
    print(f"""
======================================================================
SEED Realistic Email System (29-1) created!
======================================================================

🌐 Topology:
----------------------------------------
📍 Internet Exchanges:
   - Beijing-IX (100)
   - Shanghai-IX (101)
   - Guangzhou-IX (102)
   - Global-IX (103)

🏢 Internet Service Providers:
   - AS-2, AS-3, AS-4

📧 Mail Providers:
----------------------------------------
🐧 QQ Mail (AS-200, Tencent)
   Container: mail-qq-tencent
   Domain: qq.com
   IP: 10.200.0.10
   SMTP: localhost:2200 | IMAP: localhost:1400

📫 163 Mail (AS-201, NetEase)
   Container: mail-163-netease
   Domain: 163.com
   IP: 10.201.0.10
   SMTP: localhost:2201 | IMAP: localhost:1401

✉️  Gmail (AS-202, Google)
   Container: mail-gmail-google
   Domain: gmail.com
   IP: 10.202.0.10
   SMTP: localhost:2202 | IMAP: localhost:1402

📬 Outlook (AS-203, Microsoft)
   Container: mail-outlook-microsoft
   Domain: outlook.com
   IP: 10.203.0.10
   SMTP: localhost:2203 | IMAP: localhost:1403

🏢 Company (AS-204, Aliyun)
   Container: mail-company-aliyun
   Domain: company.cn
   IP: 10.204.0.10
   SMTP: localhost:2204 | IMAP: localhost:1404

🚀 Startup (AS-205, Self-hosted)
   Container: mail-startup-selfhosted
   Domain: startup.net
   IP: 10.205.0.10
   SMTP: localhost:2205 | IMAP: localhost:1405

🌐 Monitoring:
   Internet Map: http://localhost:8080/map.html

======================================================================
    """)

if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if platform not in ["arm", "amd", "auto", "arm64", "amd64", "x86_64", "aarch64"]:
        print("Usage: python3 email_realistic.py [arm|amd|auto]")
        sys.exit(1)
    run(platform)

# SEED Emulator 邮件服务系统设计文档

## 📋 目录

1. [概述](#概述)
2. [核心设计理念](#核心设计理念)
3. [架构说明](#架构说明)
4. [EmailComprehensiveService 详细设计](#emailcomprehensiveservice-详细设计)
5. [WebmailService 详细设计](#webmailservice-详细设计)
6. [使用示例](#使用示例)
7. [技术细节与注意事项](#技术细节与注意事项)
8. [测试验证](#测试验证)

---

## 概述

本文档详细说明了 SEED Emulator 项目中新设计的邮件服务系统，包括 `EmailComprehensiveService` 和 `WebmailService` 两个核心组件。

### 设计目标

- ✅ **符合 SEED Emulator 架构规范**：使用标准的 Service/Server 模式
- ✅ **职责分离**：服务层不直接操作容器，仅配置节点
- ✅ **灵活可扩展**：支持多种邮件路由模式和 DNS 集成
- ✅ **教学友好**：面向课堂演示，配置简单明了
- ✅ **真实模拟**：基于 Postfix + Dovecot 实现标准 SMTP/IMAP 协议

---

## 核心设计理念

### SEED Emulator 的 Service 层设计原则

在 SEED Emulator 中，Service 和 Server 的职责划分非常明确：

```
┌─────────────────────────────────────────────────────────────┐
│                    Emulator 层                               │
│  - 管理全局拓扑                                               │
│  - 协调各层渲染                                               │
│  - 生成最终输出                                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Service 层                                │
│  - 管理多个 Server 实例                                       │
│  - 处理 vnode → pnode 绑定                                   │
│  - 协调跨节点依赖（如 DNS 解析）                              │
│  - ✅ 只能调用 node 级别的 API                                │
│  - ❌ 不能直接操作 docker-compose                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Server 层                                 │
│  - 代表单个服务实例（如一个邮件服务器）                        │
│  - 配置具体节点：                                             │
│    • node.addSoftware()     - 安装软件包                      │
│    • node.setFile()         - 写入配置文件                    │
│    • node.appendStartCommand() - 添加启动命令                 │
│  - ✅ 只配置，不执行                                          │
│  - ❌ 不能假设容器环境                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Node 层                                   │
│  - 代表一个物理/虚拟节点                                      │
│  - 存储软件、文件、命令列表                                    │
│  - 最终由 Compiler 转换为容器配置                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Compiler 层                                 │
│  - 将 Node 配置转换为 docker-compose.yml                      │
│  - 生成 Dockerfile 和启动脚本                                 │
│  - 处理网络、卷、端口映射                                     │
└─────────────────────────────────────────────────────────────┘
```

### ❌ 常见错误示例：越权操作

```python
# ❌ 错误：Service 层直接操作 docker-compose
class BadEmailService(Service):
    def configure(self, emulator):
        docker = emulator.getCompiler()
        docker.addContainer(...)  # 越权！
```

### ✅ 正确示例：通过 Node API

```python
# ✅ 正确：通过 Node API 配置
class GoodEmailService(Service):
    def configure(self, emulator):
        for (vnode, server) in self.getPendingTargets().items():
            pnode = emulator.getBindingFor(vnode)
            server.install(pnode)  # 调用 Server.install()

class GoodEmailServer(Server):
    def install(self, node: Node):
        node.addSoftware('postfix dovecot-imapd')
        node.appendStartCommand('service postfix start')
```

---

## 架构说明

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                  Example Script                              │
│  (email_simple_v2.py)                                        │
│                                                              │
│  1. 创建 AS 和网络拓扑                                        │
│  2. 安装邮件服务：                                           │
│     email.install('mail-qq')                                 │
│         .setDomain('qq.com')                                 │
│         .addAccount('user', 'password123')                   │
│  3. 安装 Webmail：                                           │
│     webmail.install('webmail-qq')                            │
│         .setImapTarget('mail-qq')                            │
│  4. 绑定到物理节点：                                         │
│     emu.addBinding(Binding('mail-qq', ...))                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│          EmailComprehensiveService                           │
│                                                              │
│  • 管理多个 EmailServer 实例                                 │
│  • 支持两种路由模式：                                        │
│    - DNS-first: 通过 MX 记录查询                             │
│    - Transport: 静态路由表                                   │
│  • 可选集成 DomainNameService                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              EmailServer                                     │
│                                                              │
│  配置内容：                                                   │
│  1. 安装软件：postfix, dovecot-imapd, rsyslog               │
│  2. 配置 Postfix：                                           │
│     - myhostname, mydomain                                   │
│     - smtp_host_lookup = dns (DNS模式)                       │
│     - transport_maps (Transport模式)                         │
│  3. 配置 Dovecot：                                           │
│     - mail_location = maildir:~/Maildir                      │
│     - disable_plaintext_auth = no (课堂演示)                 │
│  4. 创建系统用户和邮箱目录                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              WebmailService                                  │
│                                                              │
│  • 管理多个 WebmailServer 实例                               │
│  • 提供 Web 界面访问邮箱                                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              WebmailServer                                   │
│                                                              │
│  配置内容：                                                   │
│  1. 安装软件：apache2, php, roundcube, sqlite3              │
│  2. 配置 Apache：创建 /roundcube 别名                        │
│  3. 配置 Roundcube：                                         │
│     - 数据库：SQLite                                         │
│     - IMAP/SMTP 服务器地址                                   │
│  4. 初始化数据库                                             │
└─────────────────────────────────────────────────────────────┘
```

### 关键技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| **SMTP Server** | Postfix | 业界标准 MTA，配置灵活 |
| **IMAP Server** | Dovecot | 轻量高效，支持 Maildir |
| **Webmail** | Roundcube | 现代化 Web 邮件客户端 |
| **Web Server** | Apache2 + PHP | Roundcube 依赖 |
| **Database** | SQLite | 单机部署，无需额外服务 |
| **邮箱格式** | Maildir | 每封邮件独立文件，适合演示 |

---

## EmailComprehensiveService 详细设计

### 类结构

```python
EmailComprehensiveService (Service)
    └── EmailServer (Server)
            ├── 配置属性
            ├── Fluent API 设置方法
            ├── _prepare() - 预处理阶段
            └── install() - 安装配置
```

### EmailServer 核心属性

```python
class EmailServer(Server):
    # 域名配置
    __domain: str = ''              # 邮件域名，如 'qq.com'
    __hostname: str = 'mail'        # 主机名，如 'mail'
    
    # 路由模式
    __mode: str = 'dns'             # 'dns' 或 'transport'
    __transport: Dict[str, str]     # 跨域路由映射
    __resolved_transport: Dict      # 解析后的 IP 地址
    
    # 用户账户
    __accounts: List[Tuple[str, str]]  # [(localpart, password), ...]
    
    # DNS 集成
    __auto_publish_mx: bool = False  # 自动发布 MX 记录
    
    # 可选端口
    __enable_submission: bool = False  # 启用 587 端口
    __enable_imaps: bool = False       # 启用 993 端口
```

### Fluent API 设计

采用链式调用风格，提高代码可读性：

```python
# ✅ 清晰的配置流程
email.install('mail-qq') \
     .setDomain('qq.com') \
     .setHostname('mail') \
     .setModeDnsFirst() \
     .enableAutoPublishMx(True) \
     .addAccount('alice', 'pass123') \
     .addAccount('bob', 'pass456')
```

### 关键方法详解

#### 1. setModeDnsFirst() - DNS 优先模式

```python
def setModeDnsFirst(self) -> "EmailServer":
    """使用 DNS MX 记录进行邮件路由
    
    工作原理：
    1. Postfix 接收到发往 user@example.com 的邮件
    2. 查询 example.com 的 MX 记录
    3. 获取邮件服务器地址（如 mail.example.com）
    4. 解析 A 记录获取 IP
    5. 建立 SMTP 连接投递邮件
    
    Postfix 配置：
        smtp_host_lookup = dns
        smtp_dns_support_level = enabled
    """
    self.__mode = 'dns'
    return self
```

**配置示例**：

```python
# 在 install() 中生成的 Postfix 配置
postconf -e "smtp_host_lookup = dns"
postconf -e "smtp_dns_support_level = enabled"
postconf -e "relayhost = "  # 不使用固定中继
```

#### 2. setModeTransport() - 静态路由模式

```python
def setModeTransport(self) -> "EmailServer":
    """使用静态路由表进行邮件路由
    
    工作原理：
    1. 配置 /etc/postfix/transport 文件：
       gmail.com    smtp:[10.202.0.10]:25
       qq.com       smtp:[10.200.0.10]:25
    2. Postfix 根据目标域名查表
    3. 直接连接指定 IP 投递邮件
    
    优点：
    - 绕过 DNS 查询，确保可达性
    - 适合复杂网络拓扑
    - 调试方便
    
    Postfix 配置：
        transport_maps = hash:/etc/postfix/transport
    """
    self.__mode = 'transport'
    return self
```

**配置示例**：

```python
# 设置路由
server.setTransportRoute('gmail.com', 'mail-gmail')  # vnode 名
server.setTransportRoute('outlook.com', '10.203.0.10')  # 或直接 IP

# 生成的 transport 文件内容：
# gmail.com smtp:[10.202.0.10]:25
# mail.gmail.com smtp:[10.202.0.10]:25
# outlook.com smtp:[10.203.0.10]:25
# mail.outlook.com smtp:[10.203.0.10]:25
```

#### 3. _prepare() - 预处理阶段

```python
def _prepare(self, node: Node, emulator: Emulator, dns_layer: Optional[DomainNameService]):
    """在 Service.configure() 阶段调用
    
    任务1: 解析 Transport 路由的 next-hop IP
    -----------------------------------------------
    transport 表中可能包含 vnode 名，需要解析为 IP：
    
    输入：
        self.__transport = {
            'gmail.com': 'mail-gmail',  # vnode 名
            'qq.com': '10.200.0.10'      # 已经是 IP
        }
    
    处理：
        for dom, hop in self.__transport.items():
            if hop 包含字母:  # 认为是 vnode 名
                pnode = emulator.getBindingFor(hop)
                ip = pnode.getInterfaces()[0].getAddress()
            else:
                ip = hop  # 已经是 IP
            self.__resolved_transport[dom] = ip
    
    输出：
        self.__resolved_transport = {
            'gmail.com': '10.202.0.10',
            'qq.com': '10.200.0.10'
        }
    
    任务2: 可选发布 MX 和 A 记录到 DNS
    -----------------------------------------------
    如果 enableAutoPublishMx(True)：
    
    1. 获取 DNS Zone 对象：
       zone = dns_layer.getZone('qq.com.')
    
    2. 添加 mail 主机 A 记录：
       zone.resolveTo('mail', node)
       # 生成：mail.qq.com. IN A 10.200.0.10
    
    3. 添加 MX 记录：
       zone.addRecord('@ MX 10 mail.qq.com.')
       # 生成：qq.com. IN MX 10 mail.qq.com.
    """
    # 实现见源码...
```

#### 4. install() - 安装配置

```python
def install(self, node: Node):
    """在节点上安装并配置邮件服务
    
    步骤1: 安装软件包
    -----------------------------------------------
    """
    node.addSoftware('postfix dovecot-imapd rsyslog')
    node.appendClassName('EmailComprehensiveService')
    
    """
    步骤2: 配置 Postfix 基础参数
    -----------------------------------------------
    使用 postconf 命令追加配置，不覆盖默认 main.cf
    """
    domain = self.__domain
    hostname = self.__hostname
    fqdn = f"{hostname}.{domain}" if domain else hostname
    
    # 基础网络配置
    node.appendStartCommand(f'postconf -e "inet_interfaces = all"')
    node.appendStartCommand(f'postconf -e "myhostname = {fqdn}"')
    node.appendStartCommand(f'postconf -e "mydomain = {domain}"')
    
    # 本地投递配置
    node.appendStartCommand(
        'postconf -e "mydestination = $myhostname, $mydomain, '
        'localhost.$mydomain, localhost"'
    )
    
    # 网络信任（课堂演示，生产环境需限制）
    node.appendStartCommand('postconf -e "mynetworks = 0.0.0.0/0"')
    
    # Maildir 格式
    node.appendStartCommand('postconf -e "home_mailbox = Maildir/"')
    
    """
    步骤3: 配置路由模式
    -----------------------------------------------
    """
    if self.__mode == 'dns':
        # DNS 模式：查询 MX 记录
        node.appendStartCommand('postconf -e "relayhost = "')
        node.appendStartCommand('postconf -e "smtp_host_lookup = dns"')
        node.appendStartCommand('postconf -e "smtp_dns_support_level = enabled"')
    else:
        # Transport 模式：静态路由表
        content_lines = []
        for dom, ip in self.__resolved_transport.items():
            content_lines.append(f"{dom} smtp:[{ip}]:25")
            content_lines.append(f"mail.{dom} smtp:[{ip}]:25")
        
        # 写入 transport 文件
        node.setFile('/etc/postfix/transport', 
                     '\n'.join(content_lines) + '\n')
        
        # 配置使用 transport 映射
        node.appendStartCommand(
            'postconf -e "transport_maps = hash:/etc/postfix/transport"'
        )
        
        # 编译 transport.db
        node.appendStartCommand(
            'test -f /etc/postfix/transport && postmap /etc/postfix/transport || true'
        )
    
    """
    步骤4: 配置 Dovecot IMAP 服务
    -----------------------------------------------
    """
    # Maildir 位置
    node.appendStartCommand(
        "sed -i 's/^#\?mail_location.*/mail_location = maildir:\\~\\/Maildir/' "
        "/etc/dovecot/conf.d/10-mail.conf || true"
    )
    
    # 允许明文认证（课堂演示，生产环境禁止）
    node.appendStartCommand(
        "sed -i 's/^#\?disable_plaintext_auth.*/disable_plaintext_auth = no/' "
        "/etc/dovecot/conf.d/10-auth.conf || true"
    )
    
    # 认证机制
    node.appendStartCommand(
        "sed -i 's/^#\?auth_mechanisms.*/auth_mechanisms = plain login/' "
        "/etc/dovecot/conf.d/10-auth.conf || true"
    )
    
    """
    步骤5: 创建系统用户和邮箱目录
    -----------------------------------------------
    """
    for (user, pwd) in self.__accounts:
        # 创建系统用户（如果不存在）
        node.appendStartCommand(
            f"id -u {user} >/dev/null 2>&1 || "
            f"useradd -m -s /usr/sbin/nologin {user}"
        )
        
        # 设置密码
        node.appendStartCommand(f"echo '{user}:{pwd}' | chpasswd")
        
        # 初始化 Maildir 结构
        node.appendStartCommand(
            f"runuser -l {user} -c 'mkdir -p ~/Maildir/{{cur,new,tmp}}' || true"
        )
    
    """
    步骤6: 启动服务
    -----------------------------------------------
    """
    node.appendStartCommand('service rsyslog start')
    node.appendStartCommand('service postfix restart || service postfix start')
    node.appendStartCommand('service dovecot restart || service dovecot start')
```

### EmailComprehensiveService 实现

```python
class EmailComprehensiveService(Service):
    """邮件服务层：创建并管理多个 EmailServer 实例
    
    职责：
    1. 创建 EmailServer 实例（通过 _createServer）
    2. 管理 vnode → pnode 绑定
    3. 在 configure 阶段协调所有 server 的预处理
    4. 声明对 Base 层的依赖
    """
    
    def __init__(self):
        super().__init__()
        # 仅依赖 Base 层
        # DNS 依赖是可选的，通过弱耦合方式集成
        self.addDependency('Base', False, False)
    
    def _createServer(self) -> Server:
        """工厂方法：创建新的 EmailServer 实例"""
        return EmailServer()
    
    def getName(self) -> str:
        """服务唯一标识"""
        return 'EmailComprehensiveService'
    
    def configure(self, emulator: Emulator):
        """配置阶段：协调所有 server 实例
        
        执行流程：
        1. 尝试获取 DomainNameService 层（可选）
        2. 遍历所有待处理的 server 实例
        3. 调用每个 server 的 _prepare() 进行预处理
        4. 调用父类 configure() 触发标准配置流程
        """
        # 可选：获取 DNS 层
        dns_layer = None
        if DomainNameService is not None:
            try:
                dns_layer = emulator.getRegistry().get(
                    'seedemu', 'layer', 'DomainNameService'
                )
            except Exception:
                dns_layer = None
        
        # 预处理所有 server
        for (vnode, server) in self.getPendingTargets().items():
            pnode = emulator.getBindingFor(vnode)
            if isinstance(server, EmailServer):
                server._prepare(pnode, emulator, dns_layer)
        
        # 触发标准配置流程（install 等）
        super().configure(emulator)
```

---

## WebmailService 详细设计

### 类结构

```python
WebmailService (Service)
    └── WebmailServer (Server)
            ├── 配置属性
            ├── Fluent API 设置方法
            ├── _prepare() - 预处理阶段
            └── install() - 安装配置
```

### WebmailServer 核心属性

```python
class WebmailServer(Server):
    # IMAP/SMTP 目标配置
    __imap_target: str = "127.0.0.1"  # IMAP 服务器（vnode 或 IP）
    __smtp_target: str = "127.0.0.1"  # SMTP 服务器（vnode 或 IP）
    __smtp_port: int = 25              # SMTP 端口
    
    # 解析后的地址
    __resolved_imap: Optional[str] = None
    __resolved_smtp: Optional[str] = None
    
    # Web 路径配置
    __alias_path: str = "/roundcube"   # 访问路径
```

### 关键方法详解

#### 1. setImapTarget() / setSmtpTarget()

```python
def setImapTarget(self, target: str) -> "WebmailServer":
    """设置 IMAP 服务器目标
    
    参数可以是：
    1. vnode 名称：'mail-qq'
       - 在 _prepare() 阶段解析为 IP
    2. 主机名：'mail.qq.com'
       - 依赖 DNS 解析（需确保 DNS 配置正确）
    3. IP 地址：'10.200.0.10'
       - 直接使用
    
    推荐：使用 vnode 名称，可靠性最高
    """
    self.__imap_target = target
    return self

def setSmtpTarget(self, target: str) -> "WebmailServer":
    """设置 SMTP 服务器目标（同上）"""
    self.__smtp_target = target
    return self
```

**使用示例**：

```python
# 方式1: 使用 vnode 名（推荐）
webmail.install('webmail-qq') \
       .setImapTarget('mail-qq') \
       .setSmtpTarget('mail-qq')

# 方式2: 使用 IP 地址
webmail.install('webmail-qq') \
       .setImapTarget('10.200.0.10') \
       .setSmtpTarget('10.200.0.10')

# 方式3: 使用主机名（需要 DNS）
webmail.install('webmail-qq') \
       .setImapTarget('mail.qq.com') \
       .setSmtpTarget('mail.qq.com')
```

#### 2. _prepare() - 解析目标地址

```python
def _prepare(self, emulator: Emulator):
    """将 vnode 名解析为 IP 地址
    
    判断逻辑：
    - 如果 target 包含 '.' 或 ':'，认为是主机名或 IP，不解析
    - 否则，认为是 vnode 名，尝试解析
    
    示例：
        输入：'mail-qq'
        查询：emulator.getBindingFor('mail-qq')
        获取：pnode.getInterfaces()[0].getAddress()
        输出：'10.200.0.10'
    """
    def resolve_target(t: str) -> str:
        if ('.' in t) or (':' in t):
            return t  # 已经是主机名或 IP
        try:
            pnode = emulator.getBindingFor(t)
            ifaces = pnode.getInterfaces()
            if len(ifaces) > 0:
                return ifaces[0].getAddress()
        except Exception:
            pass
        return t
    
    self.__resolved_imap = resolve_target(self.__imap_target)
    self.__resolved_smtp = resolve_target(self.__smtp_target)
```

#### 3. install() - 安装配置

```python
def install(self, node: Node):
    """在节点上安装并配置 Roundcube Webmail
    
    步骤1: 安装软件包
    -----------------------------------------------
    """
    node.addSoftware(
        'apache2 php php-imap php-sqlite3 php-mbstring '
        'php-xml php-json php-intl php-gd php-curl '
        'roundcube sqlite3'
    )
    node.appendClassName('WebmailService')
    
    """
    步骤2: 配置 Apache Alias
    -----------------------------------------------
    Debian 打包的 Roundcube 位于 /usr/share/roundcube
    需要创建 Apache 配置文件将其暴露为 Web 路径
    """
    alias = self.__alias_path
    apache_conf = f'''Alias {alias} /usr/share/roundcube
<Directory /usr/share/roundcube/>
    Options FollowSymLinks
    AllowOverride All
    Require all granted
</Directory>
'''
    node.setFile('/etc/apache2/conf-available/roundcube.conf', apache_conf)
    
    # 启用配置
    node.appendStartCommand('a2enconf roundcube || true')
    node.appendStartCommand('a2enmod rewrite || true')
    
    """
    步骤3: 配置 Roundcube
    -----------------------------------------------
    使用 SQLite 数据库，配置 IMAP/SMTP 连接
    """
    imap_host = self.__resolved_imap or self.__imap_target
    smtp_host = self.__resolved_smtp or self.__smtp_target
    smtp_port = self.__smtp_port
    
    config_inc = f'''<?php
$config['db_dsnw'] = 'sqlite:////var/lib/roundcube/db/sqlite.db?mode=0646';
$config['default_host'] = '{imap_host}';
$config['smtp_server'] = '{smtp_host}';
$config['smtp_port'] = {smtp_port};

// 禁用 SSL 证书验证（课堂演示）
$config['imap_conn_options'] = array(
    'ssl' => array(
        'verify_peer' => false,
        'allow_self_signed' => true
    )
);

// 禁用 SMTP 认证（使用 Postfix open relay）
$config['smtp_user'] = null;
$config['smtp_pass'] = null;
$config['smtp_auth_type'] = '';

$config['support_url'] = '';
$config['des_key'] = 'seedseedseedseed';  // 加密密钥
$config['plugins'] = array();
?>
'''
    node.setFile('/etc/roundcube/config.inc.php', config_inc)
    
    """
    步骤4: 初始化数据库
    -----------------------------------------------
    """
    # 创建目录
    node.appendStartCommand(
        'mkdir -p /var/lib/roundcube/db '
        '/var/lib/roundcube/logs '
        '/var/lib/roundcube/temp'
    )
    
    # 初始化 SQLite 数据库（如果不存在）
    node.appendStartCommand(
        'if [ -f /usr/share/roundcube/SQL/sqlite.initial.sql ] && '
        '[ ! -f /var/lib/roundcube/db/sqlite.db ]; then '
        'sqlite3 /var/lib/roundcube/db/sqlite.db < '
        '/usr/share/roundcube/SQL/sqlite.initial.sql; fi'
    )
    
    # 设置权限
    node.appendStartCommand(
        'chown -R www-data:www-data /var/lib/roundcube'
    )
    
    """
    步骤5: 启动 Apache
    -----------------------------------------------
    """
    node.appendStartCommand(
        'service apache2 restart || service apache2 start'
    )
```

---

## 使用示例

### 示例 1: 简单双域邮件系统（email_simple_v2.py）

这是最基础的测试场景，展示核心功能。

```python
#!/usr/bin/env python3
from seedemu.layers import Base, Routing, Ebgp
from seedemu.services import (
    EmailComprehensiveService,
    WebmailService,
    DomainNameService,
    DomainNameCachingService,
)
from seedemu.compiler import Docker
from seedemu.core import Emulator, Binding, Filter

def run():
    emu = Emulator()
    base = Base()
    routing = Routing()
    ebgp = Ebgp()
    
    # 创建服务层实例
    dns_auth = DomainNameService()
    dns_ldns = DomainNameCachingService(autoRoot=True)
    email = EmailComprehensiveService()
    webmail = WebmailService()
    
    # =========================================================================
    # AS-200: qq.com 邮件域
    # =========================================================================
    
    # 1. 创建网络拓扑
    base.createInternetExchange(100)
    as200 = base.createAutonomousSystem(200)
    as200.createNetwork('net0')
    as200.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    
    # 2. 创建主机节点
    as200.createHost('mail').joinNetwork('net0')
    as200.createHost('webmail').joinNetwork('net0').addPort(18080, 80)
    as200.createHost('ns').joinNetwork('net0')
    as200.createHost('dns').joinNetwork('net0')
    
    # 3. 安装邮件服务
    email.install('mail-qq') \
         .setDomain('qq.com') \
         .setHostname('mail') \
         .setModeDnsFirst() \
         .enableAutoPublishMx(True) \
         .addAccount('alice', 'password123') \
         .addAccount('bob', 'password456')
    
    # 4. 安装 Webmail
    webmail.install('webmail-qq') \
           .setImapTarget('mail-qq') \
           .setSmtpTarget('mail-qq') \
           .setSmtpPort(25)
    
    # 5. 配置 DNS
    dns_auth.install('ns-qq').addZone('qq.com.').setMaster()
    dns_ldns.install('dns-qq') \
            .setConfigureResolvconf(True) \
            .addForwardZone('qq.com.', 'ns-qq') \
            .addForwardZone('gmail.com.', 'ns-gmail')
    
    # 6. 绑定虚拟节点到物理节点
    emu.addBinding(Binding('mail-qq', filter=Filter(nodeName='mail', asn=200)))
    emu.addBinding(Binding('webmail-qq', filter=Filter(nodeName='webmail', asn=200)))
    emu.addBinding(Binding('ns-qq', filter=Filter(nodeName='ns', asn=200)))
    emu.addBinding(Binding('dns-qq', filter=Filter(nodeName='dns', asn=200)))
    
    # =========================================================================
    # AS-201: gmail.com 邮件域（类似配置）
    # =========================================================================
    
    as201 = base.createAutonomousSystem(201)
    as201.createNetwork('net0')
    as201.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as201.createHost('mail').joinNetwork('net0')
    as201.createHost('webmail').joinNetwork('net0').addPort(18081, 80)
    as201.createHost('ns').joinNetwork('net0')
    as201.createHost('dns').joinNetwork('net0')
    
    email.install('mail-gmail') \
         .setDomain('gmail.com') \
         .enableAutoPublishMx(True) \
         .addAccount('user', 'password123')
    
    webmail.install('webmail-gmail') \
           .setImapTarget('mail-gmail') \
           .setSmtpTarget('mail-gmail') \
           .setSmtpPort(25)
    
    dns_auth.install('ns-gmail').addZone('gmail.com.').setMaster()
    dns_ldns.install('dns-gmail') \
            .setConfigureResolvconf(True) \
            .addForwardZone('qq.com.', 'ns-qq') \
            .addForwardZone('gmail.com.', 'ns-gmail')
    
    emu.addBinding(Binding('mail-gmail', filter=Filter(nodeName='mail', asn=201)))
    emu.addBinding(Binding('webmail-gmail', filter=Filter(nodeName='webmail', asn=201)))
    emu.addBinding(Binding('ns-gmail', filter=Filter(nodeName='ns', asn=201)))
    emu.addBinding(Binding('dns-gmail', filter=Filter(nodeName='dns', asn=201)))
    
    # =========================================================================
    # BGP 对等
    # =========================================================================
    
    ebgp.addRsPeer(100, 200)
    ebgp.addRsPeer(100, 201)
    
    # =========================================================================
    # 渲染和编译
    # =========================================================================
    
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(dns_auth)
    emu.addLayer(dns_ldns)
    emu.addLayer(email)
    emu.addLayer(webmail)
    
    emu.render()
    emu.compile(Docker(), './output_v2', override=True)

if __name__ == '__main__':
    run()
```

### 示例 2: Transport 模式跨域路由

当网络拓扑复杂、DNS 不可靠时，使用静态路由表：

```python
# 创建三个邮件域
email = EmailComprehensiveService()

# 配置 qq.com
email.install('mail-qq') \
     .setDomain('qq.com') \
     .setModeTransport() \
     .setTransportRoute('gmail.com', 'mail-gmail') \
     .setTransportRoute('163.com', 'mail-163') \
     .addAccount('user', 'pass123')

# 配置 gmail.com
email.install('mail-gmail') \
     .setDomain('gmail.com') \
     .setModeTransport() \
     .setTransportRoute('qq.com', 'mail-qq') \
     .setTransportRoute('163.com', 'mail-163') \
     .addAccount('user', 'pass123')

# 配置 163.com
email.install('mail-163') \
     .setDomain('163.com') \
     .setModeTransport() \
     .setTransportRoute('qq.com', 'mail-qq') \
     .setTransportRoute('gmail.com', 'mail-gmail') \
     .addAccount('user', 'pass123')
```

生成的 `/etc/postfix/transport` 文件（mail-qq 节点）：

```
gmail.com smtp:[10.202.0.10]:25
mail.gmail.com smtp:[10.202.0.10]:25
163.com smtp:[10.201.0.10]:25
mail.163.com smtp:[10.201.0.10]:25
```

---

## 技术细节与注意事项

### 1. Postfix 配置要点

#### mynetworks = 0.0.0.0/0

```bash
# ⚠️ 安全警告：允许任何 IP 中继邮件
postconf -e "mynetworks = 0.0.0.0/0"
```

**说明**：
- **课堂演示**：简化配置，无需认证
- **生产环境**：必须限制为可信网络！

```bash
# 生产环境推荐配置
postconf -e "mynetworks = 127.0.0.0/8, 10.200.0.0/24"
```

#### Maildir vs mbox

```bash
# ✅ 使用 Maildir（推荐）
postconf -e "home_mailbox = Maildir/"

# ❌ 不推荐 mbox
# postconf -e "home_mailbox = mail/"
```

**Maildir 优势**：
- 每封邮件独立文件，不易损坏
- 并发访问安全
- 便于调试（可直接查看文件）

**目录结构**：
```
/home/alice/Maildir/
├── cur/   # 已读邮件
├── new/   # 新邮件
└── tmp/   # 临时文件
```

### 2. Dovecot 配置要点

#### 明文认证

```bash
# ⚠️ 课堂演示：允许明文密码
sed -i 's/^#\?disable_plaintext_auth.*/disable_plaintext_auth = no/' \
    /etc/dovecot/conf.d/10-auth.conf
```

**生产环境**：
- 必须启用 TLS/SSL
- 禁止明文认证
- 使用证书（Let's Encrypt）

#### 认证机制

```bash
# 支持 PLAIN 和 LOGIN
sed -i 's/^#\?auth_mechanisms.*/auth_mechanisms = plain login/' \
    /etc/dovecot/conf.d/10-auth.conf
```

**机制说明**：
- `plain`：Base64 编码用户名/密码
- `login`：分步传输用户名和密码
- 生产环境可考虑 `cram-md5` 等更安全机制

### 3. DNS 集成机制

#### 自动发布 MX 记录

```python
# 在 EmailServer._prepare() 中
if self.__auto_publish_mx and self.__domain:
    zone = dns_layer.getZone(f"{self.__domain}.")
    zone.resolveTo('mail', node)  # mail.qq.com → 10.200.0.10
    zone.addRecord(f"@ MX 10 mail.{self.__domain}.")
```

**生成的 DNS 记录**：
```
qq.com.         IN  MX  10 mail.qq.com.
mail.qq.com.    IN  A   10.200.0.10
```

#### DNS 查询流程

```
发件人: alice@qq.com → bob@gmail.com

1. Postfix 提取目标域名: gmail.com
2. 查询 MX 记录: gmail.com. IN MX 10 mail.gmail.com.
3. 查询 A 记录: mail.gmail.com. IN A 10.202.0.10
4. 连接 10.202.0.10:25
5. SMTP 会话: HELO, MAIL FROM, RCPT TO, DATA
```

### 4. Roundcube 配置要点

#### SQLite 数据库

```php
$config['db_dsnw'] = 'sqlite:////var/lib/roundcube/db/sqlite.db?mode=0646';
```

**优点**：
- 无需额外数据库服务
- 配置简单

**生产环境**：
- 建议使用 MySQL/PostgreSQL
- 支持多用户并发

#### SMTP 认证

```php
// 课堂演示：禁用 SMTP 认证
$config['smtp_user'] = null;
$config['smtp_pass'] = null;
$config['smtp_auth_type'] = '';
```

**说明**：
- Postfix 配置了 open relay (mynetworks = 0.0.0.0/0)
- Roundcube 无需认证即可发送
- 生产环境必须启用 SMTP AUTH

### 5. 系统用户管理

#### 创建邮箱用户

```bash
# 检查用户是否存在
id -u alice >/dev/null 2>&1 || useradd -m -s /usr/sbin/nologin alice

# 设置密码
echo 'alice:password123' | chpasswd

# 初始化 Maildir
runuser -l alice -c 'mkdir -p ~/Maildir/{cur,new,tmp}'
```

**安全考虑**：
- 使用 `/usr/sbin/nologin` 禁止 SSH 登录
- 生产环境应使用虚拟用户（不创建系统用户）

#### 虚拟用户方案

生产环境推荐使用 Postfix + Dovecot 虚拟用户：

```bash
# Postfix: 使用 MySQL/LDAP 查询用户
postconf -e "virtual_mailbox_domains = mysql:/etc/postfix/mysql-domains.cf"
postconf -e "virtual_mailbox_maps = mysql:/etc/postfix/mysql-mailboxes.cf"

# Dovecot: 连接同一数据库
# auth-sql.conf.ext
```

### 6. 调试技巧

#### 查看邮件日志

```bash
# 在容器中
docker exec -it hnode_200_mail tail -f /var/log/mail.log

# 常见日志条目
# - SMTP 连接: postfix/smtpd[1234]: connect from unknown[10.201.0.10]
# - 邮件接收: postfix/cleanup[1234]: message-id=<...>
# - 投递成功: postfix/local[1234]: to=<alice@qq.com>, status=sent
```

#### 查看邮箱内容

```bash
# 进入容器
docker exec -it hnode_200_mail bash

# 查看用户邮箱
ls -la /home/alice/Maildir/new/
cat /home/alice/Maildir/new/1234567890.Vfd00I1M123456.mail
```

#### 手动测试 SMTP

```bash
# 连接到 SMTP 服务器
telnet 10.200.0.10 25

# SMTP 会话
HELO test.com
MAIL FROM:<alice@qq.com>
RCPT TO:<bob@gmail.com>
DATA
Subject: Test
From: alice@qq.com
To: bob@gmail.com

This is a test message.
.
QUIT
```

#### 手动测试 IMAP

```bash
# 连接到 IMAP 服务器
telnet 10.200.0.10 143

# IMAP 会话
. LOGIN alice password123
. LIST "" "*"
. SELECT INBOX
. FETCH 1 BODY[]
. LOGOUT
```

---

## 测试验证

### 测试场景 1: 域内邮件投递

**目标**：验证同域用户间邮件收发

```bash
# 1. 启动环境
cd output_v2
docker-compose up -d

# 2. 发送邮件（使用 sendmail 命令）
docker exec -it hnode_200_mail bash
echo "Test message" | mail -s "Test" alice@qq.com

# 3. 检查邮箱
ls /home/alice/Maildir/new/

# 4. 使用 Roundcube 查看
# 浏览器访问: http://localhost:18080/roundcube
# 登录: alice@qq.com / password123
```

### 测试场景 2: 跨域邮件投递

**目标**：验证不同域之间邮件路由

```bash
# 从 qq.com 发送到 gmail.com
docker exec -it hnode_200_mail bash
echo "Cross-domain test" | mail -s "Test" user@gmail.com

# 检查 gmail.com 邮箱
docker exec -it hnode_201_mail ls /home/user/Maildir/new/

# 查看路由日志
docker exec -it hnode_200_mail tail -f /var/log/mail.log | grep gmail.com
```

### 测试场景 3: DNS 解析验证

**目标**：验证 MX 记录和 DNS 解析

```bash
# 在任意节点查询 MX 记录
docker exec -it hnode_200_mail dig qq.com MX

# 预期输出:
# qq.com.  IN  MX  10 mail.qq.com.

# 查询 A 记录
docker exec -it hnode_200_mail dig mail.qq.com A

# 预期输出:
# mail.qq.com.  IN  A  10.200.0.10
```

### 测试场景 4: Webmail 功能测试

**目标**：验证 Web 界面收发邮件

```bash
# 1. 访问 Roundcube
# http://localhost:18080/roundcube

# 2. 登录
# 用户名: alice@qq.com
# 密码: password123

# 3. 发送邮件
# 收件人: bob@qq.com
# 主题: Test from Roundcube
# 内容: This is a test.

# 4. 切换用户登录查看
# 用户名: bob@qq.com
# 密码: password456
```

### 测试场景 5: Transport 模式验证

**目标**：验证静态路由表

```bash
# 查看 transport 文件
docker exec -it hnode_200_mail cat /etc/postfix/transport

# 预期内容:
# gmail.com smtp:[10.202.0.10]:25
# mail.gmail.com smtp:[10.202.0.10]:25

# 查看编译后的数据库
docker exec -it hnode_200_mail postmap -q gmail.com hash:/etc/postfix/transport

# 预期输出:
# smtp:[10.202.0.10]:25
```

### 常见问题排查

#### 问题 1: 邮件发送失败

```bash
# 检查日志
docker exec -it hnode_200_mail tail -100 /var/log/mail.log

# 常见原因:
# - DNS 解析失败 → 检查 resolv.conf
# - 网络不通 → 检查路由表
# - Transport 映射错误 → 检查 transport 文件
```

#### 问题 2: Roundcube 无法登录

```bash
# 检查 IMAP 连接
docker exec -it hnode_200_webmail telnet 10.200.0.10 143

# 检查配置
docker exec -it hnode_200_webmail cat /etc/roundcube/config.inc.php

# 检查 Apache 日志
docker exec -it hnode_200_webmail tail -f /var/log/apache2/error.log
```

#### 问题 3: DNS 记录未生效

```bash
# 检查 DNS 服务器
docker exec -it hnode_200_ns service bind9 status

# 检查 Zone 文件
docker exec -it hnode_200_ns cat /etc/bind/zones/qq.com.zone

# 强制重载
docker exec -it hnode_200_ns rndc reload
```

---

## 总结

### 设计优势

✅ **符合架构规范**
   - 严格遵循 Service/Server 模式
   - 通过 Node API 配置，不越权操作容器
   - 职责清晰，易于维护

✅ **灵活可扩展**
   - 支持 DNS-first 和 Transport 两种路由模式
   - 可选集成 DomainNameService
   - Fluent API 提高可读性

✅ **真实模拟**
   - 基于 Postfix + Dovecot 标准组件
   - 支持标准 SMTP/IMAP 协议
   - 可与真实邮件客户端交互

✅ **教学友好**
   - 配置简化，易于理解
   - 详细日志，便于调试
   - 提供 Web 界面，直观展示

### 后续改进方向

🔧 **安全性增强**
   - 支持 TLS/SSL 加密
   - 实现 SMTP AUTH
   - 限制 mynetworks 范围

🔧 **功能扩展**
   - 支持邮件过滤规则
   - 实现垃圾邮件检测
   - 添加邮件别名支持

🔧 **性能优化**
   - 支持虚拟用户（无需系统用户）
   - 集成 MySQL/PostgreSQL 数据库
   - 实现邮件队列管理

🔧 **监控和可观测性**
   - 集成 Prometheus 指标
   - 提供管理面板
   - 邮件统计报表

---

## 参考资源

### 官方文档

- [Postfix Documentation](http://www.postfix.org/documentation.html)
- [Dovecot Wiki](https://wiki.dovecot.org/)
- [Roundcube Documentation](https://github.com/roundcube/roundcubemail/wiki)

### SEED Emulator

- [SEED Emulator GitHub](https://github.com/seed-labs/seed-emulator)
- [SEED Project](https://seedsecuritylabs.org/)

### 相关 RFC

- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
- [RFC 3501 - IMAP](https://tools.ietf.org/html/rfc3501)
- [RFC 1035 - DNS](https://tools.ietf.org/html/rfc1035)
- [RFC 5322 - Internet Message Format](https://tools.ietf.org/html/rfc5322)

---

**文档版本**: 1.0  
**最后更新**: 2024-11-14  
**作者**: SEED Emulator Email Service Team  
**许可证**: MIT License
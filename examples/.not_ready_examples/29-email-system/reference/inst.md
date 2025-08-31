###  **自建邮件服务器 (Docker-Mailserver) 部署操作手册**

本文档旨在指导您在个人服务器上，通过 Docker 快速部署一套功能完整的邮件服务，并配置 Webmail 客户端。（在seed-emu环境下则需要考虑清楚，因为服务提供商是我们自己，qq邮箱还是所谓个人邮箱在我们看来可能是一样的）

**最终实现功能:**

1. 基于 `mail.zzw4257.cn` 域名的邮件收发。

2. 通过 `acme.sh` 自动申请与续签 SSL 证书。

3. 解决云服务商封禁25端口问题，通过 QQ 邮箱作为 SMTP 中继对外发信。(目前被封了)

4. 通过 Roundcube 提供 Webmail 服务，并解决备案限制问题。（这个忘记立案了）

---

### **第一部分：环境准备**

在开始之前，请确保您的服务器环境满足以下条件。

**1. 系统与软件**

* **操作系统**: Ubuntu 24.04 (或其他主流 Linux 发行版)。

* **硬件建议**: 至少 2核 CPU, 2GB RAM, 20GB 磁盘空间。

* **软件安装**: 确保 `curl`, `wget`, `netstat` 等基础工具已安装。

**2. 安装 Docker 和 Docker Compose**

```plaintext
# 更新软件包列表
sudo apt update
​
# 安装 Docker
sudo apt install -y docker.io
​
# 启动并设置 Docker 开机自启
sudo systemctl start docker
sudo systemctl enable docker
```

**3. 配置 Docker 镜像加速源** 为了提高镜像拉取速度，我们配置国内加速源。

```plaintext
# 创建或修改 Docker 配置文件
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://xuanyuan.cloud"
  ]
}
EOF
​
# 重启 Docker 服务以应用配置
sudo systemctl restart docker
```

**4. 端口检查**

* **确认邮件端口未被占用**:

  ```plaintext
  netstat -unltp | grep -E -w '25|143|465|587|993|110|995'
  # 预期：无任何输出
  ```

* **防火墙放行**: 确保服务器的安全组或防火墙已放行上述所有 TCP/UDP 端口。

---

### **第二部分：核心邮件服务部署 (docker-mailserver)**

**1. 创建工作目录并下载配置文件**

```plaintext
# 创建并进入工作目录
mkdir -p ~/mail-test/mailserver && cd ~/mail-test/mailserver
​
# 下载官方配置文件
DMS_GITHUB_URL='https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master'
wget "${DMS_GITHUB_URL}/docker-compose.yml"
wget "${DMS_GITHUB_URL}/mailserver.env"
wget "${DMS_GITHUB_URL}/setup.sh"
chmod a+x ./setup.sh
```

**2. 编写自定义配置文件** 创建 `docker-compose.override.yml` 来管理我们的自定义设置，并集成 `acme.sh` 用于自动申请证书。

```plaintext
# 创建并编辑 docker-compose.override.yml
tee docker-compose.override.yml <<-'EOF'
services:
  mailserver:
    hostname: mail
    domainname: zzw4257.cn
    ports:
      - "110:110"  # POP3
      - "995:995"  # POP3 (with TLS)
    volumes:
      - ./docker-data/dms/mail-data/:/var/mail/
      - ./docker-data/dms/mail-state/:/var/mail-state/
      - ./docker-data/dms/mail-logs/:/var/log/mail/
      - ./docker-data/dms/config/:/tmp/docker-mailserver/
      - /etc/localtime:/etc/localtime:ro
      - mailserver_ssl:/etc/letsencrypt # 将证书卷命名为 mailserver_ssl
    environment:
      - OVERRIDE_HOSTNAME=mail.zzw4257.cn
      - ENABLE_POP3=1
      - SSL_TYPE=letsencrypt # 改为 letsencrypt 以便 acme.sh 接管
    labels:
      - sh.acme.autoload.domain=mail.zzw4257.cn
​
  acme.sh:
    image: neilpang/acme.sh
    container_name: acme.sh_mail
    command: daemon
    volumes:
      - ./acme.sh:/acme.sh
      - /var/run/docker.sock:/var/run/docker.sock
      - mailserver_ssl:/etc/letsencrypt # 共享同一个证书卷
    environment:
      - DEPLOY_DOCKER_CONTAINER_LABEL=sh.acme.autoload.domain=mail.zzw4257.cn
      - DEPLOY_DOCKER_CONTAINER_KEY_FILE=/etc/letsencrypt/live/mail.zzw4257.cn/privkey.pem
      - DEPLOY_DOCKER_CONTAINER_CERT_FILE="/etc/letsencrypt/live/mail.zzw4257.cn/cert.pem"
      - DEPLOY_DOCKER_CONTAINER_CA_FILE="/etc/letsencrypt/live/mail.zzw4257.cn/chain.pem"
      - DEPLOY_DOCKER_CONTAINER_FULLCHAIN_FILE="/etc/letsencrypt/live/mail.zzw4257.cn/fullchain.pem"
      - DEPLOY_DOCKER_CONTAINER_RELOAD_CMD="supervisorctl restart postfix"
​
volumes:
  mailserver_ssl:
EOF
```

**3. 启动容器并创建邮件账户**

```plaintext
# 以后台模式启动容器
docker compose up -d
​
# 添加第一个邮件账户 (按提示输入密码)
./setup.sh email add admin@zzw4257.cn
```

**4. 申请 SSL 证书 (acme.sh & Cloudflare)** a. **获取 Cloudflare API Token**     \*   登录 Cloudflare -> 我的个人资料 -> API 令牌 -> 创建令牌。     \*   使用“自定义令牌”模板，添加以下权限：         \*   `区域` - `DNS` - `编辑`         \*   `区域` - `区域` - `读取`     \*   区域资源选择 `zzw4257.cn`。     \*   创建并保存好生成的 Token。

b. **进入 acme.sh 容器并申请证书**     \`\`\`bash     # 进入容器     docker exec -it acme.sh_mail sh

````plaintext
# (在容器内) 注册账户
acme.sh --register-account -m zzw4257@gmail.com
​
# (在容器内) 设置 Cloudflare API Token
export CF_Token="粘贴你刚刚获取的API_Token"
​
# (在容器内) 申请证书
acme.sh --issue --dns dns_cf -d mail.zzw4257.cn
​
# (在容器内) 退出容器
exit
```
````

c. **重启 mailserver 容器以加载证书**     `bash     docker compose restart mailserver`

**5. 生成 DKIM 密钥**

```plaintext
# 生成 2048 位的 DKIM 密钥对
./setup.sh config dkim keysize 2048
​
# 查看需要配置到 DNS 的公钥记录 (复制引号内的内容)
cat ./docker-data/dms/config/opendkim/keys/zzw4257.cn/mail.txt
```

---

### **第三部分：DNS 记录配置 (Cloudflare)**

登录您的 Cloudflare 控制台，为 `zzw4257.cn` 添加以下 DNS 记录：

| **类型** | **名称 (Host)**     | **内容 (Value)**                                             |
| -------- | ------------------- | ------------------------------------------------------------ |
|          |                     |                                                              |
|          |                     |                                                              |
| **A**    | `mail`              | `你的服务器公网IP地址`                                       |
| **MX**   | `@` (或 zzw4257.cn) | `mail.zzw4257.cn` (优先级: 10)                               |
| **TXT**  | `@` (或 zzw4257.cn) | `v=spf1 mx ~all`                                             |
| **TXT**  | `mail._domainkey`   | `v=DKIM1; h=sha256; k=rsa; p=...` (粘贴上一步从 `mail.txt` 文件中复制的内容) |
| **TXT**  | `_dmarc`            | `v=DMARC1; p=none; rua=mailto:zzw4257@gmail.com; ruf=mailto:zzw4257@gmail.com; sp=none; ri=86400` |

---

### **第四部分：配置 SMTP 中继 (解决25端口封禁)**

由于云服务商封禁 TCP 25 端口，我们需要配置邮件服务器通过 QQ 邮箱的 465 端口对外发信。

**1. 修改 Postfix 主配置**

```
# 编辑 postfix-main.cf 文件，在末尾追加中继设置
tee -a ./docker-data/dms/config/postfix-main.cf <<-'EOF'

# SMTP Relay Settings for QQ Mail
smtp_sender_dependent_authentication = yes
sender_dependent_relayhost_maps = hash:/tmp/docker-mailserver/postfix-sender-relay.cf
smtp_sasl_auth_enable = yes
smtp_sasl_password_maps = hash:/tmp/docker-mailserver/postfix-sasl.cf
smtp_sasl_security_options = noanonymous
smtp_tls_security_level = may
smtp_tls_wrappermode = yes
sender_canonical_maps = regexp:/tmp/docker-mailserver/postfix-sender-canonical.cf
EOF
```

**2. 创建 SASL 认证文件** 此文件包含您的 QQ 邮箱账户和授权码。

```plaintext
# 创建 postfix-sasl.cf 文件
tee ./docker-data/dms/config/postfix-sasl.cf <<-'EOF'
[smtp.qq.com]:465 809050685@qq.com:xutqpejdkpfcbbhi
EOF
```

**3. 创建发件人重写规则** QQ 邮箱要求发件人地址必须与认证账户一致，此规则将所有外发邮件的发件人重写为您的 QQ 邮箱。

```plaintext
# 创建 postfix-sender-canonical.cf 文件
tee ./docker-data/dms/config/postfix-sender-canonical.cf <<-'EOF'
/.+@zzw4257\.cn/ 809050685@qq.com
EOF
```

**4. 创建中继主机映射** 此文件定义了使用哪个中继服务器。

```plaintext
# 创建 postfix-sender-relay.cf 文件
tee ./docker-data/dms/config/postfix-sender-relay.cf <<-'EOF'
@zzw4257.cn [smtp.qq.com]:465
EOF
```

**5. 重启服务使配置生效**

````plaintext
docker compose restart mailserver```

---

### **第五部分：部署 Webmail (Roundcube)**

**1. 创建 Webmail 工作目录**```bash
# 在 mail-test 目录下创建 webmail 目录并进入
mkdir -p ~/mail-test/webmail && cd ~/mail-test/webmail
````

**2. 编写 Webmail 的** `docker-compose.yml` 此配置包含 Roundcube 服务和一个 Nginx 反向代理。

```plaintext
tee docker-compose.yml <<-'EOF'
version: '3.3'
services:
  roundcube:
    image: roundcube/roundcubemail:latest
    container_name: roundcube
    restart: always
    volumes:
      - ./www:/var/www/html
    environment:
      - ROUNDCUBEMAIL_DEFAULT_HOST=mail.zzw4257.cn
      - ROUNDCUBEMAIL_SMTP_SERVER=mail.zzw4257.cn
    networks:
      - mailserver_default

  nginx:
    image: nginx:alpine
    container_name: roundcube-nginx
    restart: always
    ports:
      - "8888:80" # 使用 8888 端口绕过备案检查
    volumes:
      - ./nginx/roundcube.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - roundcube
    networks:
      - mailserver_default

networks:
  mailserver_default:
    external: true
    name: mailserver_default
EOF
```

**3. 创建 Nginx 配置文件**

```plaintext
# 创建 Nginx 配置目录和文件
mkdir -p nginx
tee nginx/roundcube.conf <<-'EOF'
server {
    listen 80;
    server_name mail.zzw4257.cn;

    location / {
        proxy_pass http://roundcube;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF
```

**4. 启动 Webmail 服务**

```plaintext
docker compose up -d
```

---

### **第六部分：验证与使用**

**1. 检查所有容器状态**

```plaintext
# 切换到 mailserver 目录
cd ~/mail-test/mailserver
docker compose ps

# 切换到 webmail 目录
cd ~/mail-test/webmail
docker compose ps
# 预期：所有容器的状态应为 running 或 healthy
```

**2. 如何访问和使用**

* **Webmail 访问**:

  * 在浏览器中打开：`http://你的服务器IP:8888`

  * 用户名：`admin@zzw4257.cn`

  * 密码：(您之前设置的密码)

* **邮件客户端配置 (如 Outlook, Foxmail, Thunderbird)**:

  * **接收邮件 (IMAP)**:

    * 服务器: `mail.zzw4257.cn`

    * 端口: `993`

    * 加密: `SSL/TLS`

  * **发送邮件 (SMTP)**:

    * 服务器: `mail.zzw4257.cn`

    * 端口: `465` 或 `587`

    * 加密: `SSL/TLS` (465) 或 `STARTTLS` (587)

  * **用户名**: `admin@zzw4257.cn`

  * **密码**: (您的密码)

**3. 添加更多邮箱用户**

```plaintext
# 在 mailserver 目录下执行
cd ~/mail-test/mailserver
./setup.sh email add newuser@zzw4257.cn
```

至此，您的个人邮件服务器已完全部署并配置成功。
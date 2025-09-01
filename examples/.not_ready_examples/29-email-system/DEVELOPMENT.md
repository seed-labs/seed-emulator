# Email System 开发日志

## 项目开发记录

### 2024年 - 项目启动

#### 开发目标
基于SEED Emulator框架构建邮件系统仿真环境，为邮件安全实验（特别是钓鱼攻击实验）奠定基础。

#### 技术栈选择
- **仿真框架**: SEED Emulator (seedemu)
- **邮件服务器**: docker-mailserver
- **平台支持**: ARM64/AMD64
- **容器化**: Docker + docker-compose

## 开发阶段

### 阶段1: 需求分析和架构设计

#### 参考项目分析
1. **B00_mini_internet**: 学习基础网络拓扑构建
2. **B25_pki**: 理解服务集成和DNS配置模式
3. **A11_add_containers_new/method_1**: 掌握自定义容器添加方法

#### 关键设计决策

**网络拓扑设计**:
```
选择简单的星型拓扑而非复杂的多层结构
原因: MVP版本优先保证功能完整性，避免网络复杂度带来的调试困难
```

**邮件服务器选择**:
```
选择docker-mailserver而非自建postfix/dovecot
原因: 
1. docker-mailserver是成熟的邮件服务器解决方案
2. 配置简单，适合教学环境
3. 支持完整的SMTP/IMAP/POP3协议栈
```

**平台兼容性**:
```
同时支持ARM64和AMD64
原因: 考虑到Mac M系列和Intel/AMD处理器的广泛使用
```

### 阶段2: MVP实现

#### 实现策略
采用递增式开发，先实现最小可行产品(MVP)，再逐步增加功能。

#### 第一版实现 (`email_simple.py`)

**完成功能**:
- ✅ 基础网络拓扑 (3个邮件服务器AS + 2个客户端AS)
- ✅ docker-mailserver容器集成
- ✅ 多域名支持 (seedemail.net, corporate.local, smallbiz.org)
- ✅ ARM64/AMD64平台自动检测
- ✅ 端口映射和网络配置
- ✅ 可视化支持 (Internet Map)

**技术实现要点**:

1. **平台检测逻辑**:
```python
if sys.argv[1].lower() == 'arm':
    platform = Platform.ARM64
    platform_str = "linux/arm64"
elif sys.argv[1].lower() == 'amd':
    platform = Platform.AMD64  
    platform_str = "linux/amd64"
```

2. **容器配置模板**:
```python
MAILSERVER_COMPOSE_TEMPLATE = """
    {name}:
        image: mailserver/docker-mailserver:edge
        platform: {platform}
        # ... 其他配置
"""
```

3. **网络绑定**:
```python
docker.attachCustomContainer(
    compose_entry=compose_entry,
    asn=mail['asn'],
    net=mail['network'],
    ip_address=mail['ip'],
    node_name=mail['name'],
    show_on_map=True
)
```

### 阶段3: 问题解决记录

#### 问题1: 函数参数传递错误
**问题描述**: 在`create_base_network()`函数中使用了未定义的`emu`变量

**解决方案**:
```python
# 修改前
def create_base_network():
    # ... 
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 2)  # emu未定义

# 修改后  
def create_base_network(emu):
    # ...
    Makers.makeStubAsWithHosts(emu, base, 150, 100, 2)  # 通过参数传递
```

**教训**: 函数设计时要明确参数依赖，避免隐式的全局变量依赖

#### 问题2: docker-mailserver容器启动复杂性
**问题描述**: docker-mailserver需要特定的环境变量和卷挂载配置

**解决方案**:
```python
environment:
    - OVERRIDE_HOSTNAME={hostname}.{domain}
    - PERMIT_DOCKER=connected-networks
    - ONE_DIR=1
    - ENABLE_CLAMAV=0           # 禁用ClamAV以减少资源消耗
    - ENABLE_FAIL2BAN=0         # 禁用Fail2ban简化配置
    - SSL_TYPE=self-signed      # 使用自签名证书简化SSL配置
```

**考虑因素**:
- 禁用非必要服务以降低资源消耗
- 使用自签名证书避免证书配置复杂性
- 设置合适的权限以确保容器正常运行

#### 问题3: ARM64平台镜像兼容性
**问题描述**: docker-mailserver在ARM64平台需要明确指定平台标签

**解决方案**:
```bash
# 手动拉取命令
docker pull --platform linux/arm64 mailserver/docker-mailserver:edge

# 在compose文件中指定平台
platform: linux/arm64
```

**扩展考虑**: 在脚本中自动检测平台并设置正确的镜像标签

### 阶段4: 测试和验证

#### 测试环境
- **硬件**: Apple M1 Pro (ARM64)
- **操作系统**: Ubuntu 24.04 (通过Parallels)
- **Docker版本**: 24.x
- **Python版本**: 3.9+

#### 测试流程
1. **环境准备测试**:
```bash
source development.env
conda activate seed-emulator
python -c "from seedemu.core import Emulator; print('OK')"
```

2. **脚本执行测试**:
```bash
python3 email_simple.py arm
cd output/
docker-compose config  # 验证配置文件语法
```

3. **容器启动测试**:
```bash
docker-compose up -d
docker-compose ps
```

4. **功能验证测试**:
```bash
# 网络连通性测试
docker exec -it as150h-host_0 ping 10.151.0.10

# 邮件服务器端口测试
telnet localhost 25150
```

## 已知问题和限制

### 当前限制
1. **DNS配置缺失**: MVP版本暂未包含完整的DNS服务器配置
2. **邮件路由**: 跨域邮件路由需要手动配置主机名解析
3. **安全配置**: 使用自签名证书，生产环境需要正式证书
4. **性能优化**: 未针对大规模部署进行优化

### 计划改进
1. **完整DNS系统**: 在`email_system.py`中实现完整的DNS配置
2. **自动化配置**: 添加邮件账户的自动创建脚本
3. **监控功能**: 集成邮件服务器状态监控
4. **安全特性**: 添加DKIM、SPF、DMARC支持

## 最佳实践总结

### 开发原则
1. **渐进式开发**: 先实现MVP，再逐步添加功能
2. **模块化设计**: 将功能拆分为独立的函数模块
3. **平台兼容**: 考虑不同硬件平台的兼容性
4. **文档驱动**: 详细记录每个决策和解决方案

### 代码规范
1. **函数命名**: 使用清晰的动词+名词命名模式
2. **注释风格**: 使用docstring描述函数功能和参数
3. **错误处理**: 提供清晰的错误信息和使用说明
4. **配置管理**: 使用模板和配置字典管理复杂配置

### 测试策略
1. **分层测试**: 环境->脚本->容器->功能逐层验证
2. **跨平台测试**: 在ARM64和AMD64平台都进行验证
3. **场景测试**: 测试典型的邮件发送接收场景
4. **压力测试**: 验证多用户并发场景

## 下一阶段规划

### 短期目标 (1-2周)
- [ ] 完成DNS系统集成 (`email_system.py`)
- [ ] 添加邮件账户自动创建脚本
- [ ] 完善测试用例和验证脚本

### 中期目标 (1个月)
- [ ] 实现跨域邮件路由测试
- [ ] 添加Web邮件客户端集成
- [ ] 性能优化和资源使用分析

### 长期目标 (2-3个月)  
- [ ] 扩展为钓鱼攻击实验平台 (`30-phishing`)
- [ ] 集成邮件安全检测工具
- [ ] 建立完整的教学实验指南

## 技术债务记录

### 代码质量
- [ ] 添加类型注解提高代码可读性
- [ ] 重构配置管理使用配置文件而非硬编码
- [ ] 添加单元测试覆盖核心功能

### 架构改进
- [ ] 考虑使用工厂模式管理不同类型的邮件服务器
- [ ] 抽象网络拓扑配置为独立模块
- [ ] 设计插件系统支持功能扩展

---

**维护人员**: SEED Lab  
**最后更新**: 2024年  
**版本**: 1.0 (MVP)

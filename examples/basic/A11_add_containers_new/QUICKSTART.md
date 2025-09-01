# 🚀 DeSci Platform 快速启动指南

## 📋 目录

- [快速开始](#快速开始)
- [详细启动方式](#详细启动方式)
- [环境配置](#环境配置)
- [服务检查](#服务检查)
- [故障排除](#故障排除)

## ⚡ 快速开始

### 最简单的启动方式（推荐）

```bash
# 1. 进入项目目录
cd demo

# 2. 安装依赖
npm install

# 3. 一键启动所有服务
npm run unified
```

**启动成功后访问：**
- 🌐 Vue.js前端：http://localhost:3001
- 🌐 HTML前端：http://localhost:3000
- 🔗 API文档：http://localhost:3000/api/version

### 基础演示模式

```bash
# 只启动HTML前端演示
npm run demo
```
访问：http://localhost:3000

---

## 🎯 详细启动方式

### 方式一：完整开发环境

```bash
# 安装主项目依赖
npm install

# 安装Vue.js前端依赖
cd BS && npm install

# 返回主目录并启动所有服务
cd .. && npm run unified
```

### 方式二：单独启动服务

#### 仅Vue.js前端
```bash
npm run unified:vue
```
访问：http://localhost:3001

#### 仅HTML前端
```bash
npm run demo
```
访问：http://localhost:3000

#### 仅后端API
```bash
npm run backend
```
访问：http://localhost:3000/api

### 方式三：开发调试模式

**终端1：**
```bash
npm run backend
```

**终端2：**
```bash
cd BS && npm run dev
```

**终端3：**
```bash
npm run demo
```

### 方式四：区块链集成模式

**步骤1：启动区块链网络**
```bash
npm run node
```

**步骤2：部署合约**
```bash
npm run deploy
```

**步骤3：启动应用**
```bash
npm run unified
```

---

## ⚙️ 环境配置

### 环境变量

创建 `.env` 文件：

```bash
# 调试模式
DEBUG=true
NODE_ENV=development

# 端口配置
PORT=3000
VUE_PORT=3001
API_PORT=3000

# 区块链配置
BLOCKCHAIN_ENABLED=true
RPC_URL=http://127.0.0.1:8545

# CORS配置
CORS_ORIGIN=http://localhost:3001,http://localhost:3000
```

### 自定义启动

```bash
# 指定端口
PORT=8080 npm run demo

# 启用调试
DEBUG=true npm run unified

# 禁用区块链
BLOCKCHAIN_ENABLED=false npm run unified
```

---

## 🔍 服务检查

### 检查服务状态

```bash
# 检查HTML前端
curl http://localhost:3000

# 检查Vue.js前端
curl http://localhost:3001

# 检查API健康状态
curl http://localhost:3000/health

# 检查区块链网络
curl http://localhost:8545
```

### 查看运行进程

```bash
# 查看所有Node.js进程
ps aux | grep node

# 查看端口占用
netstat -tulpn | grep :300

# 查看具体端口
lsof -i :3000
lsof -i :3001
```

---

## 🐛 故障排除

### 常见问题

#### 1. 端口被占用

```bash
# 检查端口占用
lsof -i :3000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
PORT=3002 npm run demo
```

#### 2. Vue.js启动失败

```bash
# 清理并重新安装
cd BS
rm -rf node_modules package-lock.json
npm install

# 检查版本
node --version
npm --version
```

#### 3. 依赖安装失败

```bash
# 清理缓存
npm cache clean --force

# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 重新安装
npm install
```

#### 4. 内存不足

```bash
# 增加内存限制
NODE_OPTIONS="--max-old-space-size=4096" npm run unified
```

### 区块链相关问题

#### 连接失败

```bash
# 检查Hardhat网络
curl http://localhost:8545

# 重新启动网络
npm run node

# 等待10秒后部署
sleep 10 && npm run deploy
```

#### 合约部署失败

```bash
# 编译合约
npx hardhat compile

# 检查网络状态
npx hardhat run scripts/check-network.js
```

---

## 📊 服务端口一览

| 服务类型 | 默认端口 | 说明 | 访问地址 |
|---------|---------|------|----------|
| HTML前端 | 3000 | 原生HTML演示 | http://localhost:3000 |
| Vue.js前端 | 3001 | 现代化Vue应用 | http://localhost:3001 |
| 后端API | 3000 | RESTful API服务 | http://localhost:3000/api |
| Hardhat网络 | 8545 | 本地区块链 | http://localhost:8545 |

---

## 🎉 启动成功标志

当所有服务正常启动时，您应该看到：

### HTML前端 (端口3000)
```
🚀 ============================================
🚀         DeSci平台演示已启动
🚀 ============================================
🚀 服务器地址: http://localhost:3000
```

### Vue.js前端 (端口3001)
```
VITE v4.5.14  ready in 338 ms
➜  Local:   http://localhost:3001/
➜  press h to show help
```

### 后端API (端口3000)
```
🚀 ============================================
🚀         DeSci Platform API Server
🚀 ============================================
🚀 服务器地址: http://localhost:3000
🚀 调试模式: ✅ 启用
🚀 区块链集成: ✅ 启用
```

---

## 📞 获取帮助

如果遇到问题，请：

1. 检查[详细文档](./README.md)
2. 查看[故障排除指南](./TROUBLESHOOTING.md)
3. 检查[API文档](./UNIFIED_SYSTEM_README.md)
4. 查看控制台错误信息

---

## 🎯 下一步

启动成功后，您可以：

1. **浏览应用**：访问前端界面探索功能
2. **查看API**：访问 `/api/version` 查看API状态
3. **测试功能**：尝试各项功能的完整流程
4. **深入开发**：参考详细文档进行二次开发

祝您使用愉快！ 🎉

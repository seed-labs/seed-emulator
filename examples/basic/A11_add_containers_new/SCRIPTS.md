# 📜 NPM Scripts 使用指南

## 📋 目录

- [快速开始](#快速开始)
- [演示脚本](#演示脚本)
- [开发脚本](#开发脚本)
- [区块链脚本](#区块链脚本)
- [构建和部署](#构建和部署)
- [测试脚本](#测试脚本)
- [工具脚本](#工具脚本)

## ⚡ 快速开始

```bash
# 一键安装所有依赖
npm run setup

# 一键启动完整系统
npm run unified

# 检查系统状态
npm run status
```

---

## 🎬 演示脚本

### 基础演示

```bash
# 启动HTML前端演示
npm run demo

# 启动完整系统演示
npm run unified

# 启动Vue.js前端演示
npm run unified:vue

# 启动HTML前端演示
npm run unified:html
```

### 自定义配置演示

```bash
# 指定端口启动
npm run demo:port

# 调试模式启动
npm run demo:debug

# 生产模式启动
npm run demo:prod
```

### 区块链集成演示

```bash
# 启用区块链功能
npm run unified:blockchain

# 仅使用模拟数据
npm run unified:mock
```

---

## 🛠️ 开发脚本

### 服务启动

```bash
# 启动后端API
npm run backend

# 启动Vue.js前端开发服务器
npm run vue

# 启动所有服务（开发模式）
npm run unified:debug
```

### 环境配置

```bash
# 开发环境启动
npm run dev:debug

# 生产环境启动
npm run unified:prod

# 后端生产模式
npm run backend:prod
```

### 依赖管理

```bash
# 安装所有依赖
npm run setup

# 仅安装主项目依赖
npm install

# 安装Vue.js前端依赖
npm run vue:install

# 完整安装（包含编译）
npm run setup:full
```

---

## ⛓️ 区块链脚本

### 网络管理

```bash
# 启动本地Hardhat网络
npm run node

# 启动本地网络的别名
npm run local
```

### 合约操作

```bash
# 编译智能合约
npm run compile

# 部署到本地网络
npm run deploy

# 部署到Sepolia测试网
npm run deploy:sepolia

# 部署到主网
npm run deploy:mainnet

# 本地部署别名
npm run deploy:local
```

### 合约验证

```bash
# 验证已部署合约
npm run verify

# 清理编译产物
npm run clean
```

---

## 🏗️ 构建和部署

### 构建

```bash
# 构建Vue.js前端
npm run vue:build

# 完整构建流程
npm run compile && npm run vue:build
```

### 一键部署流程

```bash
# 完整演示流程（编译+部署+启动）
npm run full-demo
```

---

## 🧪 测试脚本

### 单元测试

```bash
# 运行所有测试
npm run test

# 运行所有测试套件
npm run test:all
```

### 组件测试

```bash
# 测试用户档案合约
npm run test:userprofile

# 测试零知识证明合约
npm run test:zkproof

# 测试数据集合约
npm run test:dataset

# 测试NFT合约
npm run test:descinft

# 测试平台合约
npm run test:platform
```

### 覆盖率测试

```bash
# 生成测试覆盖率报告
npm run coverage
```

---

## 🔧 工具脚本

### 状态检查

```bash
# 检查系统状态
npm run status

# 检查服务健康状态
npm run health

# 状态检查别名
npm run check
```

### 代码质量

```bash
# 代码检查
npm run lint
```

---

## 📊 脚本分类总结

### 🚀 快速启动

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `npm run setup` | 安装所有依赖 | 初次使用 |
| `npm run unified` | 启动完整系统 | 完整体验 |
| `npm run demo` | 启动HTML演示 | 快速预览 |
| `npm run status` | 检查系统状态 | 故障排查 |

### 🛠️ 开发环境

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `npm run backend` | 启动API服务 | 后端开发 |
| `npm run vue` | 启动Vue.js开发服务器 | 前端开发 |
| `npm run unified:debug` | 调试模式启动 | 开发调试 |
| `npm run dev:debug` | 开发调试模式 | 快速开发 |

### ⛓️ 区块链操作

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `npm run node` | 启动本地网络 | 本地测试 |
| `npm run compile` | 编译合约 | 合约开发 |
| `npm run deploy` | 部署合约 | 合约部署 |
| `npm run verify` | 验证合约 | 部署确认 |

### 🧪 测试和质量

| 命令 | 说明 | 适用场景 |
|------|------|----------|
| `npm run test` | 运行测试 | 质量保证 |
| `npm run test:all` | 运行所有测试 | 完整测试 |
| `npm run coverage` | 覆盖率测试 | 测试报告 |
| `npm run lint` | 代码检查 | 代码质量 |

---

## 🎯 使用建议

### 新用户推荐流程

```bash
# 1. 初次使用：安装依赖
npm run setup

# 2. 快速预览：启动演示
npm run demo

# 3. 完整体验：启动全系统
npm run unified

# 4. 开发调试：启用调试模式
npm run unified:debug
```

### 开发者工作流

```bash
# 1. 启动开发环境
npm run unified:debug

# 2. 开发过程中检查状态
npm run status

# 3. 运行测试确保质量
npm run test

# 4. 部署到测试网络
npm run deploy:sepolia
```

### 生产部署流程

```bash
# 1. 完整测试
npm run test:all

# 2. 构建生产版本
npm run vue:build

# 3. 生产模式启动
npm run unified:prod

# 4. 监控系统状态
npm run health
```

---

## 🔧 自定义脚本

### 添加新脚本

在 `package.json` 的 `scripts` 部分添加：

```json
{
  "scripts": {
    "custom:start": "node custom-script.js",
    "custom:build": "npm run compile && npm run vue:build",
    "custom:deploy": "npm run deploy && npm run custom:start"
  }
}
```

### 环境变量使用

```bash
# 使用环境变量
DEBUG=true npm run demo

# 组合使用
DEBUG=true PORT=8080 npm run unified

# 区块链配置
BLOCKCHAIN_ENABLED=false npm run unified
```

---

## 📞 获取帮助

### 脚本帮助

```bash
# 查看所有可用脚本
npm run

# 查看特定脚本
npm run --help
```

### 故障排除

- **脚本执行失败**：检查 Node.js 版本和依赖
- **端口冲突**：使用自定义端口启动
- **依赖问题**：运行 `npm run setup` 重新安装
- **网络问题**：检查防火墙和代理设置

---

## 🎉 最佳实践

1. **使用语义化脚本名**：如 `npm run dev` 而不是 `npm run demo`
2. **保持脚本简洁**：复杂操作拆分为多个简单脚本
3. **添加脚本描述**：在脚本名中使用 `:` 分隔描述
4. **使用环境变量**：灵活配置不同环境的参数
5. **定期更新脚本**：根据项目发展调整脚本

---

*最后更新：2024年8月30日*

# 智能体上下文文件包指南

> **目标**：为没有前情知识的智能体提供完整的项目理解所需的关键文件清单

## 📋 必需文件列表

### 1. 项目概览与架构
```
docs/ARCHITECTURE.md              # 系统架构设计文档
docs/MIGRATION_FROM_42.md         # 从42实验迁移的历史脉络
README.md                         # 项目总体介绍（如存在）
```

### 2. 核心实现代码
```
web_interface.py                  # Flask 主应用与路由定义
templates/showcase.html           # 教学展示页面模板
templates/base.html               # 基础模板布局
integration_monitor.py            # 服务监控与外部工具集成类
```

### 3. 配置与数据
```
config/integration_config.json   # 外部工具配置（Gophish、OpenBAS等）
config/seed_network_overlay.yaml # 网络拓扑覆盖配置
config/credentials.example.env   # 凭据配置示例
requirements.txt                 # Python 依赖列表
```

### 4. 脚本与自动化
```
scripts/prepare_external_tools.sh     # 外部工具准备脚本
scripts/run_demo_57.sh                # 演示启动脚本
scripts/cleanup_seed_env.sh           # 环境清理脚本
```

## 🎯 根据调研方向的重点文件

### 教学设计深化（Pedagogy Enhancement）
**重点文件**：
- `web_interface.py` → `/showcase` 路由的 `pedagogy_blueprint`、`assessment_rubric`
- `templates/showcase.html` → 教学设计、案例对标、评估指标区块
- `docs/MIGRATION_FROM_42.md` → 实验脉络演化历史

**智能体提示词模板**：
```
基于提供的 Flask 路由代码和教学展示模板，分析当前的教学设计结构，并提出以下维度的改进建议：
1. 课堂节奏优化（引入→探究→总结的时间分配）
2. 多学科整合点（与传播学、心理学的结合）
3. 评估 Rubric 的 Bloom 分类法映射
4. 学生作业与教师评价要点的样本设计
```

### 动态数据集成（Real-time Integration）
**重点文件**：
- `integration_monitor.py` → `IntegrationMonitor` 类的API调用逻辑
- `config/integration_config.json` → 外部工具连接配置
- `web_interface.py` → `monitor.list_services()` 的使用方式

**智能体提示词模板**：
```
分析 IntegrationMonitor 的设计模式，并基于以下需求设计实时数据融合方案：
1. 将 Gophish Campaign 指标嵌入教学展示页面
2. OpenBAS 演练得分与进度的实时显示
3. PentestAgent 任务状态的可视化集成
4. 异常服务的告警与自动恢复建议
请提供具体的代码修改建议和前端展示组件设计。
```

### 攻防场景扩展（Attack Scenarios）
**重点文件**：
- `web_interface.py` → `case_studies`、`toolchain`、`future_tracks`
- `config/seed_network_overlay.yaml` → 网络拓扑结构
- `docs/ARCHITECTURE.md` → 攻防工具链架构

**智能体提示词模板**：
```
基于 MITRE ATT&CK 框架和现有工具链配置，设计新的攻防演练场景：
1. 鱼叉邮件 → 横向渗透 → 情报狩猎的完整链路
2. AI 对抗样本生成与检测模型鲁棒性验证
3. 多云环境下的邮件合规与威胁情报联动
请为每个场景提供技术实现路径、教学要点和评估指标。
```

### 可视化与交互优化（Visualization Enhancement）
**重点文件**：
- `templates/showcase.html` → 前端样式与交互组件
- `templates/base.html` → Bootstrap 基础样式
- `web_interface.py` → 数据结构与模板渲染

**智能体提示词模板**：
```
基于现有的 Bootstrap 5 + 自定义CSS 设计，提升教学展示页面的交互体验：
1. 引入 Chart.js 展示点击率、检测率时序图
2. 设计手风琴式组件呈现未来拓展方向
3. 添加"导出课堂报告"功能的前后端实现
4. 优化移动端适配与深色主题一致性
请提供具体的代码片段和设计建议。
```

## 🔧 使用方式

### 步骤1：准备上下文包
```bash
# 创建临时目录
mkdir /tmp/ai_context_package

# 复制必需文件
cp web_interface.py /tmp/ai_context_package/
cp templates/showcase.html /tmp/ai_context_package/
cp config/integration_config.json /tmp/ai_context_package/
cp docs/ARCHITECTURE.md /tmp/ai_context_package/
# ... 根据具体调研方向选择其他文件

# 打包
tar -czf ai_context_package.tar.gz -C /tmp ai_context_package/
```

### 步骤2：智能体对话开场
```
我正在开发一个基于 Flask 的邮件安全教学展示系统，需要你帮助深化以下方面：
[选择具体方向：教学设计深化 / 动态数据集成 / 攻防场景扩展 / 可视化优化]

项目背景：这是一个整合了 Gophish、OpenBAS、PentestAgent 等真实攻防工具的综合安全评估实验(57号实验)，用于高校邮件安全课程的实践教学。

请首先阅读提供的代码文件，理解当前架构，然后基于我的具体需求提出改进方案。
```

### 步骤3：迭代优化
根据智能体的初步建议，可进一步提供：
- 测试用例文件 (`tests/test_*.py`)
- 相关脚本输出日志
- 具体的报错信息或性能瓶颈描述

## ⚠️ 注意事项

1. **敏感信息过滤**：不要包含 `credentials.example.env` 中的真实密钥
2. **文件大小控制**：单个文件超过1000行时，可提供关键函数/类的摘要
3. **版本一致性**：确保提供的文件是同一时间点的快照，避免版本冲突
4. **依赖说明**：在对话中明确 Python 版本、主要依赖库版本

## 📚 扩展阅读建议

为智能体提供额外的领域知识参考：
- MITRE ATT&CK Framework 官方文档链接
- Gophish 官方教程与最佳实践
- Bootstrap 5 组件库文档
- Flask-SQLAlchemy 集成模式（如需数据持久化）

这样配置后，智能体就能基于完整的项目上下文，针对具体的调研方向提供有价值的建议和代码实现。
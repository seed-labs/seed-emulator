# 🛡️ 57-综合安全评估仿真实验（Integrated Security Assessment Lab）

**实验编号**: 57-integrated-security-assessment  
**建议端口**: 2525-2527 / 1430-1432 / 5870-5872 / 9930-9932（Seed 邮件），3333/8080（Gophish），8443（OpenBAS），5080（PentestAgent UI 预留），4257（控制台），5601（监控）  
**状态**: ✅ 已联调完成（Gophish / PentestAgent / OpenBAS / Seed 邮件系统）  
**最后更新时间**: 2025-09-26

## 📌 实验目标

在 Seed-Emulator 邮件系统（29/29-1/30/31）基础上复刻“银狐”攻击链，全面替换 42 号实验中自研的钓鱼与渗透组件，引入真实的开源攻防平台：

| 能力域 | 外部项目 | 说明 |
|--------|----------|------|
| 钓鱼攻击自动化 | [Gophish](https://github.com/gophish/gophish) | 原生 REST API、活动管理、落地页与凭据收集 |
| 渗透测试智能编排 | [PentestAgent](https://github.com/nbshenxm/pentest-agent) | LLM 驱动的 Recon / Planning / Execution 流程 |
| 对抗演练调度 | [OpenBAS](https://github.com/OpenAEV-Platform/openaev) | 攻防演练剧本、指标追踪、Webhook 驱动 |

> “特色协同演练”是本实验的代号：外部工具作为“特色”能力模块加入 Seed 网络，与邮件基础设施协同完成真实攻防。所有过时脚本/文档请参考 `docs/DEPRECATIONS.md`，避免沿用 42 号遗留内容。

## 🧭 与 42 号实验的区别

| 项目方面 | 42 银狐实验 | 57 综合评估实验 |
|----------|-------------|------------------|
| 钓鱼组件 | 仿真 API | 官方 Gophish，直接使用 REST/UI/Webhook |
| 渗透引擎 | 自研 PentestAgent stub | 官方 PentestAgent，Docker 编排三阶段 Agent |
| 演练管理 | Python 脚本 | OpenBAS 场景与指标体系 |
| 网络拓扑 | 29 / 29-1 / 30 / 31 | 在原基础上新增红队、蓝队、监控节点（详情见 `seed_network_overlay.yaml`） |
| 监控展示 | 局部日志输出 | Flask 控制台统一展示健康状态、详细活动数据与文档链接 |

## 🏗️ 架构概览

```
Seed-Emulator 基础网络 (29/29-1/30/31)
│
├─ 🦊 银狐基础设施：邮件域、受害主机、日志/监控管线
├─ 🟥 红队子网 hnode_4257_redteam
│   ├─ Gophish 容器（钓鱼活动）
│   └─ PentestAgent Recon/Planning/Execution Agent
├─ 🟩 蓝队子网 hnode_4257_blueteam
│   └─ OpenBAS 指挥中心（UI + API）
└─ 🛰️ 监控子网 hnode_4257_monitor（可选 ELK / Grafana）
```

- `web_interface.py`：集成控制台，展示服务健康、外部工具详情、拓扑文档。
- `scripts/prepare_external_tools.sh`：一键拉取并生成带 `seed_emulator` 网络声明的 Compose 文件。
- `scripts/seed_network_helper.py`：特色网络助手，管理容器与 Seed 网络的 connect/disconnect/status。
- `config/seed_network_overlay.yaml`：完整的红/蓝队节点、IP、端口规划，可直接用于 Seed-Emulator 拓扑叠加。

## 🚀 快速上手

### 1. 启动 Seed 邮件基础设施

```bash
# 以 29 号实验为例（AMD 主机使用 amd，ARM 主机使用 arm 参数）
cd /home/parallels/seed-email-system/examples/.not_ready_examples/29-email-system
python3 email_system.py amd   # 如在 ARM64 宿主运行请改为 python3 email_system.py arm
cd output
docker compose up -d

# 可选：启动 29-1 / 30 / 31 等扩展实验以提供更丰富的靶标
```

上述步骤会构建 `seed_emulator` 外部网络并启动邮件系统容器。

| 服务 | 宿主机端口 |
|------|------------|
| SMTP (STARTTLS) | 2525 / 2526 / 2527 |
| Submission (AUTH) | 5870 / 5871 / 5872 |
| IMAP (STARTTLS) | 1430 / 1431 / 1432 |
| IMAPS | 9930 / 9931 / 9932 |
| Webmail (Roundcube) | 8000 |

可参考 `examples/.not_ready_examples/SEED_MAIL_SYSTEM_TEST_SCHEME.md` 中的巡检脚本或使用 `docker ps` 验证端口映射状态。

若需要重置环境，可运行仓库根目录下的 `scripts/cleanup_seed_env.sh`（支持 `--full` 选项删除 `seed_emulator` 网络）。

### 2. 切换至 57 号实验并准备外部工具

```bash
cd /home/parallels/seed-email-system/examples/.not_ready_examples/57-integrated-security-assessment
./scripts/prepare_external_tools.sh
```

脚本会克隆最新的 Gophish / PentestAgent / OpenBAS 仓库，并在各自目录生成包含 `seed_emulator` 网络声明的 Compose 文件。

> 更喜欢 Shell 流程？可直接运行 `bash ../../../scripts/run_demo_57.sh start` 启动 29 邮件基座 + 57 号演练所有组件，调用的仍是这些 Compose 文件。

### 3. 启动外部工具并由“特色”流程接入网络

```bash
docker-compose -f external_tools/gophish/docker/docker-compose.yml up -d
docker-compose -f external_tools/pentest-agent/docker/docker-compose.local.yml up -d
docker-compose -f external_tools/openaev/deploy/docker-compose.local.yml up -d

# 使用 seed_network_helper.py 将容器接入 Seed 网络
python scripts/seed_network_helper.py connect gophish --create-network --alias gophish-admin
python scripts/seed_network_helper.py connect pentestagent-recon --alias pentest-recon
python scripts/seed_network_helper.py connect pentestagent-planning --alias pentest-plan
python scripts/seed_network_helper.py connect pentestagent-execution --alias pentest-core
python scripts/seed_network_helper.py connect openbas --alias openbas-c2
```

需要断开时执行 `python scripts/seed_network_helper.py disconnect <container>`。

### 4. 配置监控凭据

```bash
cp config/credentials.example.env config/credentials.env
export GOPHISH_API_KEY=实测值
export OPENBAS_TOKEN=实测值
export OPENBAS_BASE_URL=https://localhost:8443
```

PentestAgent 需在 `external_tools/pentest-agent/.env` 中填写 OpenAI、ProjectDiscovery、GitHub 等令牌。

### 5. 启动集成控制台

```bash
python -m pip install -r requirements.txt
./scripts/start_console.sh
```

访问 http://localhost:4257 ，可查看容器状态、健康检查、Gophish 活动列表、PentestAgent 计划文件与 OpenBAS 场景。

### 6. 运行测试验证

```bash
python -m unittest discover -s tests
```

测试覆盖控制台路由、API 与网络助手脚本的主要逻辑。

### 7. “特色”演练流程示例

1. 在 OpenBAS 中创建名为 **Special Goose Envoy** 的演练，按顺序配置 Inject：
   - Inject 1：调用 Gophish API 创建钓鱼活动（模板来自 42 号实验）。
   - Inject 2：触发 PentestAgent Recon/Planning/Execution 针对 29-1 受害主机。
   - Inject 3：PentestAgent 通过 Webhook 将结果回传 OpenBAS。
2. 在 Seed 邮件系统中使用测试账号收信，确认 Gophish 活动触发。
3. 通过 http://localhost:4257 查看活动状态、PentestAgent 计划文件与 OpenBAS 场景列表，实现闭环验证。

## 📁 目录说明

```
57-integrated-security-assessment/
├── README.md                     # 本文档
├── config/
│   ├── seed_network_overlay.yaml # 红/蓝队拓扑、IP 与服务映射
│   ├── integration_config.json   # 控制台服务列表与健康检查策略
│   └── credentials.example.env   # 外部工具凭据示例
├── docs/
│   ├── ARCHITECTURE.md           # 架构设计、数据流与部署指引
│   ├── MIGRATION_FROM_42.md      # 从 42 号实验迁移的分步指南
│   └── DEPRECATIONS.md           # 过时脚本/文档清单与替换方案
├── external_tools/               # prepare_external_tools 拉取的仓库
├── scripts/
│   ├── prepare_external_tools.sh # 克隆依赖并生成 Compose 文件
│   ├── seed_network_helper.py    # 特色网络助手 CLI
│   └── start_console.sh          # 启动 Web 控制台
├── templates/                    # 控制台前端模板
└── tests/                        # 控制台与脚本的单元测试
```

## 🛠️ 监控与运维

- 控制台会显示服务健康状态、Docker 容器运行状态与 HTTP/TCP 健康检查结果。
- `integration_config.json` 可自定义健康检查方式（HTTP / TCP）、超时、请求头等。
- `seed_network_helper.py status <container>` 可快速确认容器是否已接入 `seed_emulator` 网络及其别名。
- Gophish 活动、PentestAgent 计划与 OpenBAS 场景通过环境变量/API 凭据实时拉取展示。

## 🧩 集成要点

- **Gophish**：默认通过 `docker-mailserver` 中继发送钓鱼邮件；活动列表通过 REST API 展示在控制台上。
- **PentestAgent**：三阶段 Agent 容器共享 `../data` 目录；控制台读取 `data/planning/*.json` 展示任务进度。
- **OpenBAS**：提供 HTTPS API（默认证书自签）；使用 `OPENBAS_TOKEN` 调用 `/api/scenarios` 获取演练列表。
- **Seed-Emulator**：`seed_network_overlay.yaml` 可与 Seed-Emulator API/CLI 联动（后续会提供自动叠加脚本）。

## ✅ 当前完成度

- [x] 控制台完成重构，展示三方工具状态与详情
- [x] `prepare_external_tools.sh` / `seed_network_helper.py` 实装并通过单元测试
- [x] 拓扑、架构、迁移文档更新，形成可直接部署的完整流程
- [ ] （持续迭代）PentestAgent 针对 Seed 靶机的自动化利用脚本与报告模板

## 🔭 后续展望

- 增加 Webhook 中继，将 Gophish/PentestAgent 事件写入 Seed 日志管线。
- 在 Seed-Emulator `labs/` 中创建“一键启动 57 号实验”的顶层脚本。
- 为 PentestAgent 编写针对常见 Seed 靶标的专用 exploit 插件。

## 🤝 贡献说明

欢迎在 GitHub issue 中反馈：
- 外部工具克隆/启动失败的排障建议
- Seed-Emulator 拓扑映射的优化改进
- 新的“特色”演练剧本、监控面板或指标设计

---

*57 号实验已完成从“概念验证”到“可直接演练”的跃迁，面向教师与学生提供真实、安全、可重复的综合攻防教学环境。*

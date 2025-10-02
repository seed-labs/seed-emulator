# 🎯 SEED 邮件系统与特色协同演练平台

[![SEED Lab](https://img.shields.io/badge/SEED-Lab-blue.svg)](https://seedsecuritylabs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-24.0+-blue.svg)](https://www.docker.com/)

本仓库聚合了 **SEED Emulator 邮件基座（29 / 29-1 / 30 / 31）** 与 **57 号“特色协同演练”** 实验，覆盖从多域邮件系统到真实攻防联调的完整教学路径。

## � 实验矩阵总览

| 类别 | 目录 | 目标 | 当前状态 |
|------|------|------|----------|
| 基础邮件 | `examples/.not_ready_examples/29-email-system/` | 三域邮件系统 + Webmail | ✅ 编译脚本/文档完成，端口统一为 2525-2527 / 1430-1432 / 5870-5872 / 9930-9932 |
| 拓展网络 | `examples/.not_ready_examples/29-1-email-system/` | 多 AS 邮件链路与 BGP/DNS | ✅ 可与 29 号联动运行 |
| AI 钓鱼 | `examples/.not_ready_examples/30-phishing-ai-system/` | AI 辅助钓鱼演练 | ⚠️ 研发中，需手动校准依赖 |
| 高级钓鱼 | `examples/.not_ready_examples/31-advanced-phishing-system/` | 定制化钓鱼流程 | ⚠️ 研发中 |
| 特色协同演练 | `examples/.not_ready_examples/57-integrated-security-assessment/` | Gophish + PentestAgent + OpenBAS 联调 | ✅ 邮件基座 + 外部工具联动完成 |

更多草稿/调研内容位于 `examples/.not_ready_examples/` 目录，可按需探索。

## 🔑 核心端口速查

| 场景 | 端口 | 描述 |
|------|------|------|
| Seed 邮件系统 | 2525 / 2526 / 2527 | 各域 SMTP (STARTTLS) |
| Seed 邮件系统 | 5870 / 5871 / 5872 | Submission (AUTH 端口) |
| Seed 邮件系统 | 1430 / 1431 / 1432 | IMAP (STARTTLS) |
| Seed 邮件系统 | 9930 / 9931 / 9932 | IMAPS |
| Seed Webmail | 8000 | Roundcube Webmail |
| 特色控制台 | 4257 | 57 号实验仪表盘 |
| 特色工具 | 3333 / 8080 | Gophish Admin / Landing |
| 特色工具 | 8443 | OpenBAS 控制台 |
| 特色工具 | 5080 | PentestAgent UI 预留 |

## � 快速上手

1. **准备环境**
	- Linux (Ubuntu 22.04 / Debian 12) 推荐；需 Docker 24+ 与 Compose v2。
	- 安装 Python 3.10+ 并执行 `pip install -r requirements.txt` 以获得基础 CLI/脚本依赖。

2. **构建 29 号邮件系统**
	```bash
	cd examples/.not_ready_examples/29-email-system
	python email_system.py amd   # x86_64 主机改用 amd，ARM64 用 arm
	cd output
	docker compose up -d
	```
	命令会生成 `seed_emulator` 外部网络并启动 3 台 `mailserver`、3 台虚拟主机以及辅助容器。所有端口按照上表映射到宿主机。

3. **启动 57 号特色协同演练**
	```bash
	cd ../../57-integrated-security-assessment
	./scripts/prepare_external_tools.sh
	docker compose -f external_tools/gophish/docker/docker-compose.yml up -d
	docker compose -f external_tools/pentest-agent/docker/docker-compose.local.yml up -d
	docker compose -f external_tools/openaev/deploy/docker-compose.local.yml up -d
	```
	然后使用网络助手将容器加入 Seed 网络：
	```bash
	python scripts/seed_network_helper.py connect gophish --create-network --alias gophish-admin
	python scripts/seed_network_helper.py connect pentestagent-recon --alias pentest-recon
	python scripts/seed_network_helper.py connect openbas --alias openbas-c2
	```

4. **启动集成控制台**
	```bash
	python -m pip install -r examples/.not_ready_examples/57-integrated-security-assessment/requirements.txt
	cd examples/.not_ready_examples/57-integrated-security-assessment
	./scripts/start_console.sh
	```
	浏览器访问 http://localhost:4257 ，即可看到 Seed 邮件系统及外部工具的健康状态、最新活动与文档入口。

5. **运行验证**
	```bash
	cd examples/.not_ready_examples/57-integrated-security-assessment
	python -m unittest discover -s tests
	```
	推荐结合 `examples/.not_ready_examples/SEED_MAIL_SYSTEM_TEST_SCHEME.md` 完成端到端检查。

如需“一键式”体验，可使用仓库提供的脚本：

- `scripts/cleanup_seed_env.sh [--full]`：清除遗留容器/网络，避免端口及网段冲突。
- `scripts/run_demo_57.sh start|stop|status`：以 Shell 方式启动或停止 29 邮件基座 + 57 号外部工具栈。

## 📚 文档索引

| 路径 | 内容 |
|------|------|
| `examples/.not_ready_examples/29-email-system/DEPLOYMENT_GUIDE.md` | 29 号实验部署、端口、验证手册 |
| `examples/.not_ready_examples/29-email-system/SYSTEM_READY_GUIDE.md` | 课堂演示/巡检手册 |
| `examples/.not_ready_examples/SEED_MAIL_SYSTEM_TEST_SCHEME.md` | 邮件系统一站式测试方案 |
| `examples/.not_ready_examples/57-integrated-security-assessment/README.md` | 57 号实验总览与联调流程 |
| `examples/.not_ready_examples/57-integrated-security-assessment/docs/ARCHITECTURE.md` | 特色协同演练架构与数据流 |
| `examples/.not_ready_examples/57-integrated-security-assessment/docs/MIGRATION_FROM_42.md` | 42 → 57 迁移指引 |
| `examples/.not_ready_examples/57-integrated-security-assessment/docs/DEPRECATIONS.md` | 弃用资产清单 |

更多脚本、预设和历史总结请查看 `examples/.not_ready_examples/` 根目录下的辅助文档（如 `PROJECT_COMPLETION_SUMMARY.md`、`SYSTEM_OVERVIEW_README.md` 等）。

## 🧭 推荐演练路径

1. **快速巡检**：使用 `SEED_MAIL_SYSTEM_TEST_SCHEME.md` 中的脚本确认 SMTP/IMAP/Webmail 正常。
2. **钓鱼链路**：在 Gophish 创建活动，验证 Seed 邮件用户可收到邮件并访问落地页。
3. **PentestAgent 联动**：触发 Recon → Planning → Execution，观察日志输出与 OpenBAS 场景指标。
4. **控制台监控**：通过 http://localhost:4257 查看容器状态、活动、指标、文档链接。
5. **课堂演示**：结合 `SYSTEM_READY_GUIDE.md` 与 57 号控制台实现“特色协同演练”全过程展示。

## 🤝 贡献与支持

- 欢迎通过 Pull Request / Issue 提交改进建议。
- 若需课堂化部署支持，可在 Issue 中说明课程规模与目标。
- 所有实验仅限教学研究用途，请在隔离环境中运行并遵守法律法规。

---

*最后更新：2025-09（同步 29/57 实验最新端口与流程）*
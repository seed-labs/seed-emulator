# 从 42 号实验迁移至 57 号实验的实操指南

> 在开始前请先阅读 `docs/DEPRECATIONS.md`，确认哪些脚本与文档需要删除或归档，避免混用旧资料。

## 1. 目录差异

| 42 号实验资产 | 57 号实验对标组件 | 迁移动作 |
|----------------|--------------------|-----------|
| `simulation_framework/attack_orchestrator.py` | OpenBAS 场景（Inject） | 删除脚本，改由 OpenBAS 定义演练流程，使用 API/Webhook 触发 |
| `external_tools/gophish_integration.py` | 官方 Gophish API | 替换为真实 `/api/campaigns`、Webhook 监听逻辑，控制台直接调用 |
| `external_tools/pentest_agent_integration.py` | PentestAgent Docker Agents | 使用 `docker-compose.local.yml` 启动 recon/planning/execution 容器 |
| `payloads/` 目录 | Gophish 落地页资源 | 保留，直接上传至 Gophish 活动或引用 Seed 静态服务器 |
| `web_interface.py` | 本仓库 `web_interface.py` | 迁移 UI 结构，新增外部工具状态卡片、API、执行脚本入口 |
| `docker/*.yml` | Seed 邮件系统容器 | 原封保留，通过 `seed_network_helper.py` 将新容器加入 `seed_emulator` 网络 |
| `docs/legacy_workflow.md` 等历史文档 | `docs/ARCHITECTURE.md`、`docs/DEPRECATIONS.md` | 删除或迁移到 `legacy/` 目录，避免误导 |

## 2. 代码层面

1. **移除 Stub/Mock**：
   - 删除 `simulation_framework` 内所有虚构类，统一改用真实工具 API。

2. **事件流切换**：
   - 将原有“模拟 API”调用改为监听 Gophish/PentestAgent/OpenBAS Webhook。
   - 推荐编写一个轻量异步服务（Flask + asyncio）转发事件至 Seed 控制台或日志系统。

3. **配置重组**：
   - 使用 `config/integration_config.json` 维护服务端口、容器名、健康检查策略。
   - 原 `attack_chain_config.yaml` 中的阶段映射迁移到 OpenBAS 场景配置与 PentestAgent 计划文件。

4. **网络连通**：
   - 删除 42 号实验自定义的 Docker 网络脚本，统一调用 `scripts/seed_network_helper.py connect <container>` 加入 `seed_emulator`。
   - 统一 Seed 邮件端口映射：SMTP 2525/2526/2527，Submission 5870/5871/5872，IMAP 1430/1431/1432，IMAPS 9930/9931/9932，避免与旧版脚本的 25/143 等端口冲突。

## 3. 外部依赖准备

- **Gophish**：执行 `./scripts/prepare_external_tools.sh` 自动生成 `docker/docker-compose.yml`、`config/config.json`，并通过 `seed_network_helper.py connect gophish` 接入网络。
- **PentestAgent**：复制 `.env.example` 补齐 API Key，创建 `../data/indexes|planning|logs` 目录后启动 `docker-compose.local.yml`。
- **OpenBAS**：使用脚本生成的 `deploy/docker-compose.local.yml`，默认管理员账号 `admin@openaev.local`，密码 `ChangeMe!123`。
- **网络拓扑**：参考 `config/seed_network_overlay.yaml` 在 Seed-Emulator 中创建红/蓝队节点，确保新容器与邮件系统互通。

## 4. 验证建议

1. 使用 Seed 邮件系统测试账号触发 Gophish 活动，确认邮件投递与登录页面可访问。
2. PentestAgent Recon → Planning → Execution 任务针对 29-1 靶机执行一次，日志写入 `external_tools/pentest-agent/data/logs`。
3. 在 OpenBAS 创建 “Special Goose Envoy” 场景，将 Gophish 活动与 PentestAgent 任务串联，验证仪表盘与演练指标更新。
4. 控制台 http://localhost:4257 与单元测试 `python -m unittest discover -s tests` 用于最终回归。

## 5. TODO

- [ ] 编写 Webhook 中继服务，将外部工具事件转化为 Seed 控制台可消费的数据源。
- [ ] 制定标准化演练报告模板，整合 OpenBAS 指标、Gophish 活动表与 PentestAgent 日志。
- [ ] 在 Seed-Emulator `labs/` 中加入“一键启动 57 号实验”示例脚本。
- [ ] 定期更新 `docs/DEPRECATIONS.md`，保持课堂资料与脚本一致。

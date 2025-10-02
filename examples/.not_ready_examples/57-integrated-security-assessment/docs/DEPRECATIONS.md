# 过时脚本与文档清单

本文件列出 42 号实验中已经被 57 号“特色协同演练”替换或淘汰的资产，方便在对接 Seed-Labs 或课堂环境时统一清理。

## 已淘汰脚本

| 旧文件/目录 | 替代方案 | 说明 |
|-------------|----------|------|
| `simulation_framework/` 下所有 Python 模块 | OpenBAS 场景 + PentestAgent 任务 | 42 号的攻击编排和模拟逻辑全部移交给外部工具，建议删除整个目录。
| `external_tools/gophish_integration.py` | 官方 Gophish REST API 调用（见 `scripts/prepare_external_tools.sh`） | 旧脚本仿真返回值，不再维护。
| `external_tools/pentest_agent_integration.py` | 官方 PentestAgent Docker Compose (`external_tools/pentest-agent/docker/docker-compose.local.yml`) | 旧脚本只提供 stub，已废弃。
| `scripts/legacy_seed_network.sh`（如存在） | `scripts/seed_network_helper.py` | 任何手工 `docker network connect` 脚本请替换为新的 CLI。

## 已过时文档

| 旧文档 | 替代文档 | 处理建议 |
|--------|----------|----------|
| `docs/legacy_workflow.md`（若仍残留） | `docs/ARCHITECTURE.md` + `docs/MIGRATION_FROM_42.md` | 删除旧版流程文档，使用新文档同步教学内容。
| 42 号实验 README 中的“模拟接口说明”段落 | 本目录下 `README.md` | 复制迁移时请更新到新目录下的 README。

## 迁移清理步骤

1. 在 42 号实验目录执行备份：
   ```bash
   tar czf backup-42-framework.tar.gz simulation_framework
   ```
2. 删除旧的模拟脚本目录与重复的 `external_tools/` 子目录。
3. 将本实验的 `scripts/`、`config/`、`docs/`、`templates/` 替换/拷贝到目标仓库。
4. 根据 `docs/MIGRATION_FROM_42.md` 完成剩余对接工作。

## 备注

- 如课堂仍需展示旧流程，可将上述目录移入 `legacy/` 文件夹，并在 README 中显式标注「过时，仅供参考」。
- 本清单会随实验迭代更新，请在执行脚本 `./scripts/prepare_external_tools.sh` 后检查是否有新的弃用项目。
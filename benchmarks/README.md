<!-- README_SYNC_REQUIRED -->

# Benchmark workspace

本目录保存 benchmark 场景、拓扑、生成器、测试和运行证据。修改任一主要层级的接口、文件布局或工作流时，必须同步更新该层 `README.md`；修改跨层流程时还必须更新本文件。

## 主要目录

| 目录 | 作用 |
| --- | --- |
| `agents/` | benchmark 运行期诊断 Agent、观测和故障注入适配 |
| `docs/` | 场景开发、生成、晋级和验收规范 |
| `generator/` | 声明式拓扑、软件、故障、NL/MCP、bundle 与生命周期生成器 |
| `scenarios/` | 手工场景实现、注册表和已有故障示例 |
| `specs/` | suite 清单和晋级输入规范 |
| `tests/` | 单元、集成、真实 Docker 生命周期及文档覆盖测试 |
| `topologies/` | 可执行拓扑入口包装器 |
| `topology_specs/` | 声明式拓扑请求及其确定性编译计划 |
| `reports/` | 本地运行证据、NL 会话、缓存和发布记录 |
| `meeting_reports/` | 按时间归档的组会复现材料（本地保留） |

`generated/`、`logs/`、`backups/` 和 `__pycache__/` 是运行时或缓存目录，不属于需要 README 的长期维护层。

## 常用入口

```bash
cd /home/zvanadium/seed-emulator/benchmarks
python3 benchmark_cli.py --list
python3 -m generator.cli --help
python3 -m generator.nl.cli --help
python3 tests/test_benchmark_readmes.py
python3 tests/test_generator_readmes.py
```

执行真实场景前先阅读 `AGENTS.md` 和 `docs/NEW_SCENARIO_DEVELOPMENT_GUIDE.md`；正式 Agent 测试默认使用 blind 模式。

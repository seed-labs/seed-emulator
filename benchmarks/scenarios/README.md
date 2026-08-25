<!-- README_SYNC_REQUIRED -->

# Hand-authored benchmark scenarios

本目录保存可由统一 benchmark CLI 发现和运行的手工场景，也是故障行为、注入、修复与验证语义的重要参考实现。

## 结构

- `base.py` / `strict_base.py`：场景生命周期、严格安全和验证基类。
- `registry.py`：场景注册与 CLI 发现。
- 其余模块：DNS、路由、容器、资源、服务配置及组合故障场景。

每个场景应明确健康基线、故障注入、blind 观测、允许的修复命令、独立恢复验证和清理行为。新增故障类型时，应评估是否同时补充 `generator/` 的 FaultDriver 或 bundle 绑定，避免手工场景与生成场景能力分叉。

```bash
cd /home/zvanadium/seed-emulator/benchmarks
python3 benchmark_cli.py --list
```

场景接口或类别变化时同步更新本 README、注册表和相关测试。

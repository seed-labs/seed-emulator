<!-- README_SYNC_REQUIRED -->

# Benchmark tests

统一任意 benchmark 入口由 `test_unified_natural_language_generator.py` 覆盖；隔离策略、
响应硬化和旧 Unsafe 兼容性由 `test_unsafe_natural_language_generator.py` 覆盖。真实 Docker
验收必须检查完整 phase coverage、证据指纹、评分准备文件以及容器/网络/镜像零残留。

该目录覆盖 benchmark CLI、场景安全边界、生成器、自然语言桥接、bundle 和真实 Docker 生命周期。

## 测试层次

- 纯单元测试：schema、编译器、分配器、策略和确定性。
- 集成测试：TopologyRequest、BenchmarkRequest、FaultSpec、bundle 与证据链。
- 安全测试：命令白名单、资源预算、作用域隔离、prompt injection 和高风险审批。
- 生命周期测试：基线、注入、blind 测试、修复、恢复、清理与晋级。
- 文档覆盖：`test_benchmark_readmes.py` 和 `test_generator_readmes.py`。

常用检查：

```bash
cd /home/zvanadium/seed-emulator/benchmarks
python3 tests/test_benchmark_readmes.py
python3 tests/test_generator_readmes.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

涉及 Docker 或外部 provider 的测试应显式区分真实运行与离线测试，并保留可审计证据。新增测试工具或测试分层时同步更新本 README。

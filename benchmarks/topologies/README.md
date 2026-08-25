<!-- README_SYNC_REQUIRED -->

# Executable topology wrappers

本目录保存兼容既有 benchmark 工作流的拓扑入口包装器。它们把明确的构建参数交给生成器或 SEED Emulator，并将产物写入 `../generated/`，而不是在本目录保存运行结果。

当前入口覆盖大型规模和不同结构的拓扑构建示例。新增入口时应优先复用 `generator/topology/` 的声明式模型、资源预算、地址/ASN 分配、连通性检查和编译适配，避免再实现一套拓扑语义。

```bash
cd /home/zvanadium/seed-emulator/benchmarks
python3 topologies/<entry>.py --help
```

入口参数、默认资源或输出位置变化时同步更新本 README、对应 topology spec 和回归测试。

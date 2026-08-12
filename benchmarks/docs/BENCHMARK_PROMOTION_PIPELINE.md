# 生成 Benchmark 场景晋级机制

## 目标

生成场景默认进入 quarantine，只有经过真实、盲测、无 AI、可重复的生命周期验证后，才能成为主榜计分 benchmark。晋级失败时保持原 manifest 隔离状态；已晋级场景在每次加载时重新验证审计链。

## 证据链

一次晋级同时绑定以下内容：

1. 当前 benchmark contract SHA-256；contract 包括场景接口、CLI、盲测观测、生成模型、校验器和晋级策略本身。
2. 场景名称与语义 fingerprint。
3. 至少两份独立 lifecycle receipt；每份都必须来自 `rule + validate-only + blind`，且记录健康基线、故障生效、修复、标准清理和污染状态。
4. 当前注册拓扑 fingerprint 对应的 topology smoke 报告。
5. capability-driven 盲测观测，明确 `scenario_metadata_included=false`。
6. promotion record，绑定晋级后 manifest 以及上述全部证据文件的 SHA-256。

删除 promotion record、修改 manifest、修改任一 receipt、替换拓扑报告、替换盲测观测或改变 contract，都会使场景注册失败，而不是降级为无审计计分。

## 持续生产入口

拓扑已运行且 smoke/observation 证据已生成时：

```bash
cd benchmarks
python3 -m generator.agent qualify \
  --suite-id declarative_small_ring_pilot \
  --rounds 2 \
  --batch-size 5 \
  --reuse-running \
  --topology-evidence reports/TOPOLOGY_SMALL_RING_SMOKE.json \
  --observation-evidence reports/DECLARATIVE_SMALL_RING_BLIND_OBSERVATION.json
```

`qualify` 会按轮次调用正式 `benchmark_cli.py`，每批写入独立 receipt；所有场景达到两轮干净通过后才原子晋级。若生命周期由外部调度器完成，也可分别使用 `benchmark_cli.py --receipt ...` 和 `generator.agent promote --receipt ...`。

## 晋级轨道

当前审核策略为：

- `container_stopped`、`dns_nameserver` → `network_functional`
- `bird_wrong_asn`、`random_complex_transit_acl`、`random_complex_dual_bgp_acl` → `network_control_plane`

没有明确策略的模板会失败关闭，不能由 CLI 任意指定主榜轨道。

## 当前已晋级套件

`declarative_small_ring_pilot` 的 5 个场景已完成两轮真实无 AI 生命周期并进入主榜。证据位置：

- `specs/declarative_small_ring_pilot/promotion.json`
- `reports/PROMOTION_DECLARATIVE_SMALL_RING_PILOT_ROUND_01_BATCH_0000.json`
- `reports/PROMOTION_DECLARATIVE_SMALL_RING_PILOT_ROUND_02_BATCH_0000.json`
- `reports/TOPOLOGY_SMALL_RING_SMOKE.json`
- `reports/DECLARATIVE_SMALL_RING_BLIND_OBSERVATION.json`

## 运营建议

- 每次 contract 变化后，固定 seed 重生成 suite，重新运行 qualification；旧证据不能跨 contract 使用。
- 提交级 CI 运行全部静态/负向测试；定时环境运行真实 topology smoke 和两轮 qualification。
- 新故障模板必须先新增固定晋级轨道策略和负向测试，才允许进入持续生产。

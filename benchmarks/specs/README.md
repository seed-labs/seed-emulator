<!-- README_SYNC_REQUIRED -->

# Benchmark suite specifications

本目录保存可版本化的 suite 清单，用于定义哪些候选或 pilot 场景进入一组可重复执行、评分和晋级的 benchmark。

典型 suite 目录包含清单文件，描述场景集合、版本、运行策略和质量要求。清单必须引用稳定、可发现的场景或生成产物，不能依赖本地未记录状态。

修改 suite schema、字段含义或晋级条件时，同步更新本 README、`../docs/PROMOTION_PIPELINE.md`、解析代码和测试。运行时结果不写入此目录，应写入 `../reports/`。

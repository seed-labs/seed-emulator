# Generator Agent 工作要求

本文件适用于 `benchmarks/generator/` 及其所有子目录，并补充上级
`benchmarks/AGENTS.md`。进入本目录修改代码或声明文件的所有 Agent 都必须遵守以下规则。

## README 强制同步

`README_SYNC_REQUIRED`

1. 修改任意目录中的 `.py` 或声明式 `.json` 时，必须在同一个变更中更新该目录的
   `README.md`。即使代码行为看似未变，也必须记录本次改动对职责、接口或维护状态的影响。
2. 改变公共接口、CLI、schema、数据流、输出布局、安全边界或跨层依赖时，还必须同步更新
   所有受影响的上级 README；至少检查 `generator/README.md`。
3. 新增包含 Python 或声明式 JSON 的目录时，必须同时创建带
   `README_SYNC_REQUIRED` 标记的 `README.md`。
4. 删除或移动代码时，必须同步修正原目录、目标目录和上级 README 的文件索引与数据流。
5. README 中的命令必须真实存在并可从 `benchmarks/` 目录运行；不得记录尚未实现的接口为
   已完成能力。
6. 完成前必须运行：

   ```bash
   python3 tests/test_generator_readmes.py
   ```

7. CI 或提交区间审查必须指定比较基线：

   ```bash
   GENERATOR_README_DIFF_BASE=<base-commit> \
     python3 tests/test_generator_readmes.py
   ```

## 代码与文档完成定义

- 同目录 README 已在当前 diff 中更新；
- 受影响的上级 README 已更新；
- 新目录 README 覆盖检查通过；
- README 描述与代码、CLI `--help`、schema 和真实输出一致；
- 相关功能测试、`py_compile` 和 `git diff --check -- benchmarks` 通过；
- 未通过重新资格验证时，不得把计划结果描述为真实执行或正式晋级。

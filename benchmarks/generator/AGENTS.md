# Generator Agent 工作要求

本文件适用于 `benchmarks/generator/` 及其所有子目录，并补充上级
`benchmarks/AGENTS.md`。进入本目录修改代码或声明文件的所有 Agent 都必须遵守以下规则。

## README 强制同步

`README_SYNC_REQUIRED`

1. 修改任意目录中的 `.py` 或声明式 `.json` 时，必须在同一个变更中更新该目录的
   `README.md`，并逐级更新从该目录到 `generator/README.md` 的每一份上级 README。
   这是强制联级更新，不以“公共接口没有变化”为例外；README 至少应记录行为未变及验证结果。
2. 改变公共接口、CLI、schema、数据流、输出布局、安全边界或跨层依赖时，除上述祖先链外，
   还必须更新所有横向消费者目录的 README，例如 NL schema 影响 `mcp/`、`bundle/` 或
   `topology/` 时必须同步这些层。
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
8. `generator/README.md` 必须同时保留 Mermaid `flowchart` 和 `sequenceDiagram`。任何入口、
   分支、编译边界、生命周期、安全门禁、证据或晋级流程变化，都必须在同一变更中同步更新
   两张图；不得只修改正文，也不得把图降级为指向外部报告的链接。
9. Mermaid 框内标签必须保持简短；长名称使用 `<br/>` 主动换行，详细解释移到图下正文。
   修改后必须检查中文、英文标识和箭头标签没有被节点边框裁切。

## 代码与文档完成定义

- 同目录 README 及其到 `generator/README.md` 的完整祖先链均已在当前 diff 中更新；
- 横向消费者和受影响的接口 README 已更新；
- 新目录 README 覆盖检查通过；
- README 描述与代码、CLI `--help`、schema 和真实输出一致；
- 相关功能测试、`py_compile` 和 `git diff --check -- benchmarks` 通过；
- 未通过重新资格验证时，不得把计划结果描述为真实执行或正式晋级。

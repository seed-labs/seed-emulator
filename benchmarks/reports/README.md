<!-- README_SYNC_REQUIRED -->

# Runtime reports and evidence

本目录保存 generator 和 benchmark 运行产生的本地证据，不是源规范目录。除本 README 或明确选定的固定验证样本外，内容默认由 `.gitignore` 排除。

常见内容包括：

- `nl_sessions/`：Prompt、provider、能力快照、规范化 Intent、编译结果和审批记录。
- provider 缓存：外部模型结构化响应的可复现缓存。
- bundle/lifecycle 证据：健康基线、注入、blind 测试、修复、恢复、日志和指纹。
- pilot、晋级和发布记录。

报告可能包含命令输出、环境信息或模型响应。提交固定证据前必须检查密钥、token、私有地址和不必要的大文件；API 密钥不得写入报告。

报告目录结构或证据契约变化时同步更新本 README 和产生这些证据的代码层 README。

# 现场运行手册

## 总原则

现场一定同时准备三条路径：

1. 主路径：交互式 live operation
2. 备路径：非交互式 mission / task 执行
3. 兜底路径：直接展示已有证据，不把时间耗在不稳定链路上

核心目标不是“硬跑一个命令”，而是保证你在任何情况下都能把效果讲清楚。

## 汇报前先检查

在仓库根目录执行：

```bash
scripts/seed-codex up
scripts/seed-codex status
```

确认两个服务都在线：

- SeedOps MCP：`http://127.0.0.1:8000/mcp`
- SeedAgent MCP：`http://127.0.0.1:8100/mcp`

如果这里就不稳，不要直接开始 live 演示，先切到证据路径。

## 主路径：交互式 attached-runtime 演示

启动交互：

```bash
scripts/seed-codex ui
```

推荐现场输入 1：

```text
Attach to mcp-server/output_e2e_demo, refresh inventory, inspect BGP neighbors and critical services, repair anomalies if any, and leave evidence plus a concise change summary.
```

推荐现场输入 2：

```text
Attach to examples/internet/B29_email_dns/output, diagnose end-to-end mail reachability, explain the likely fault domain, verify recovery if intervention is needed, and summarize evidence.
```

## 现场口播建议

在它运行的时候，建议你同步讲这四句：

1. 现在不是在离线生成脚本，而是先 attach 到已经运行中的 SEED output。
2. 它会先感知运行时状态，再决定范围和动作。
3. 如果涉及高风险动作，它应该经过确认门。
4. 我们最终看的不只是结果，还要看 evidence、verification 和 change summary。

## 备路径 1：非交互式 planning

如果交互界面不稳，或者你不想把时间花在多轮交互上，直接跑：

```bash
scripts/seed-codex plan "Attach to mcp-server/output_e2e_demo and summarize BGP health"
```

这条路径适合快速证明：

- agent 能 attach 到真实运行环境
- agent 能理解目标
- agent 能生成运行计划

## 备路径 2：任务化执行

如果你想展示“有确认门的真实动作”，直接跑：

```bash
examples/agent-missions/run_task_demo.sh \
  --task RS_B29_FAULT_IMPACT_ABLATION \
  --objective "Run controlled packet loss ablation with rollback" \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

这条路径适合展示：

- 不是只读智能体
- 高风险动作不是直接放开
- 可以看到 action、rollback、verify 的完整闭环

## 证据优先兜底路径

如果现场模型慢、网络不稳、交互卡顿，立刻切到这三份材料：

- `evidence/review_report.md`
- `evidence/review_summary.json`
- `evidence/RUN_EVIDENCE.md`

你可以直接这样说：

1. 我们已经在真实运行输出上完成了六类场景 review pack。
2. 这里给的是完整证据，不是临时截图。
3. 我可以继续展示 live 入口和命令，但不会把现场时间浪费在不稳定外部链路上。

## 推荐现场顺序

建议按这个顺序来：

1. 一句话结论
2. 六类结果卡片
3. live interactive 或者 live plan
4. 如果时间允许，再演示一次有确认门的 task
5. 展示架构图
6. 最后讲方法论意义和下一步

## 如果现场又出现 `template_fallback`

不要慌，直接按下面这套说法：

1. `template_fallback` 是受控回退，不是系统崩了。
2. 它过去主要由 token 不一致、上游瞬时失败、GPT-5 兼容性、以及 playbook schema 不匹配引起。
3. 即便进入 fallback，review pack 里的闭环执行和 verification 仍然是完成的。
4. 如果现场需要，我可以马上切换到已经验证好的 mission 路径。

## 最后提醒

现场不要死守一种方式。你的目标是：

- 先证明效果
- 再证明它是真实操作
- 最后证明它可监督、可回放、可扩展

只要这三点讲清楚，现场就稳。

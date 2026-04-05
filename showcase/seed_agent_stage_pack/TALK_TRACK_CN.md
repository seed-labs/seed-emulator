# 汇报稿

## 0. 开场一句话

我们这次做的不是给仿真器外面套一个聊天接口，而是把 SEED Emulator 变成一个可以被智能体真实操作、又能被监督和回放的闭环实验平台。

## 1. 先讲结果，不先讲架构

先看结果。现在我们的基线不是离线生成脚本，而是对已经运行起来的 SEED 网络做 attached-runtime operation，也就是先 attach 到真实 output，再做 inspect、decide、operate、verify、summarize。

我们已经用六类场景做了基线验证：

1. Diagnosis / Maintenance
2. Disturbance Recovery
3. Routing Security
4. Service Reachability
5. Security Offense-Defense
6. Research Experiments

这一轮 review pack 的结果是六类全部通过。attach 成功 6/6，verification 成功 6/6，rollback verified 2 次，真实 risky actions 一共 7 个。重点不是它会不会说，而是它已经能在运行中的实验系统上留下真实执行轨迹和证据。

## 2. 我们解决的核心问题是什么

老师最关心的是第二层，也就是交互式操作。不是固定模板跑通一次，而是智能体面对运行中的网络，能不能先感知环境，再选择合理范围，再执行，再验证。

所以我们把主路径明确成：

`attach -> inspect -> decide -> operate -> verify -> summarize`

对应到系统里，核心不是大模型本身，而是三层闭环：

1. SEED Emulator 作为真实运行的实验基底
2. SeedOps 作为运行时控制与证据平面
3. SeedAgent 作为有策略约束和确认门的编排层

这三层闭合之后，智能体的行为就不是“调几个工具”，而是一个可监督的实验轨迹。

## 3. 为什么这不是玩具

第一，它面对的是已经运行中的 SEED 网络，不是空白画布。

第二，它不是只读。对于受控场景，它能做 fault injection、routing drill、service diagnosis、rollback 和 verify。

第三，它不是黑盒执行。每一步都可以落成 evidence、artifact、status 和 summary。

第四，它不是只能跑一个任务包。我们现在至少已经把六类任务做成了可复核的 baseline taxonomy，后面每个新 skill、每个新任务、每个失败点，都可以挂到这个 taxonomy 上继续推进。

## 4. 现场演示怎么讲

现场我建议不要全讲满，而是走三段式。

第一段，30 秒说明目标：
我们现在让 agent 接到一个自然语言目标后，先 attach 到运行中的 SEED output，再根据真实状态决定怎么检查和操作。

第二段，直接跑：
优先展示 interactive path。让它 attach 到一个已经跑起来的 output，做 BGP health 或 service reachability 检查。如果现场条件允许，再展示一个需要确认门的高风险任务，比如 fault impact ablation。

第三段，再解释为什么可信：
展示 evidence、rollback、verification，不强调“它会调用很多工具”，强调“它留下了完整的行为轨迹”。

## 5. 关于 template_fallback 怎么说

之前的 template_fallback 不是一个“功能设计目标”，而是一个退路，主要由四类问题引起：

1. SeedOps 和 SeedAgent token 不一致
2. 上游网关瞬时失败
3. GPT-5 温度参数兼容性
4. LLM 生成的 playbook schema 和 SeedOps 执行面不完全对齐

现在这些基础问题已经处理了很大一部分，尤其是 provider retry、诊断信息、schema normalization 这条链路已经补上，所以主链路稳定性已经明显提升。

## 6. 边界也要主动讲

我们不说已经通吃所有实验。现在更准确的说法是：

1. 六类 baseline 已经建立
2. 任务化/回放化路径已经很强
3. 交互式自由规划已经可用，但仍然需要继续做 planner stability 和场景分层增强

这不是短板，这是我们下一阶段工作的清晰边界。

## 7. 收束一句

我们真正交付的，不只是一个能调工具的大模型，而是一个面向 SEED Emulator 真实实验场景的、可监督、可回放、可扩展的智能体运行闭环。

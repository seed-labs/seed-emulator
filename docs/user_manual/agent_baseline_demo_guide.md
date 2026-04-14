# SEED Agent Baseline 演示手册

Last updated: 2026-04-09

这份文档是给人现场演示、自己切 baseline、自己跟智能体对话时用的。

它不回答“怎么实现”。
它回答的是：

- 现在仓库里到底有哪些 baseline 值得讲
- 每个 baseline 在哪
- 每个 baseline 的网络意义是什么
- 推荐让智能体做什么
- 你该怎么跟智能体说
- 你人应该看什么现象来判断它做得好不好

---

## 0. 演示时先记住这几条

- 现场主入口是 `scripts/seed-codex ui`。
- `mission` 是测试/回放/审计入口，不是老师面前的主交互面。
- 一次只留一个 baseline 在线。
- 先起网络，再让智能体接管。
- 先做 read-only 环境理解，再做更具体的诊断或实验。
- 默认规则就是只根据运行态做判断，不依赖源码、拓扑定义或 build-time 结构。
- 现在能稳定演示的是“接管当前唯一在线的运行网络”，不是“完全不知道 output 在哪的全黑箱发现”。

推荐统一开场提示词：

```text
接管当前唯一在线的运行网络。
先根据运行态推断关键节点、关系和第一步。
优先用已有高层工具，只有高层工具不够时才做定点容器检查。
明确区分哪些结论来自证据，哪些只是推断。
```

---

## 1. 总表

| Bundle | 源 baseline | 位置 | 主要意义 | 最适合的展示主题 | 当前推荐度 |
| --- | --- | --- | --- | --- | --- |
| `Z00` | `B00_mini_internet` | `examples/internet/B00_mini_internet/output` | 通用 routing 运维基本盘 | BGP flap、路径维护、拓扑关系推断、受控 hijack drill | 高 |
| `Z29` | `B29_email_dns` | `examples/internet/B29_email_dns/output` | 最强 service-ops 主线 | mail/DNS reachability、日志 triage、受控恢复 | 很高 |
| `Z14` | `A14_bgp_event_looking_glass` | `examples/basic/A14_bgp_event_looking_glass/output` | BGP 可观察性双视角 | route-state vs event-stream | 很高 |
| `Z12` | `A12_bgp_mixed_backend` | `examples/basic/A12_bgp_mixed_backend/output` | FRR 迁移与 live drill 主线 | mixed BIRD/FRR、announce/withdraw/rollback | 很高 |
| `Z13` | `A13_exabgp_control_plane` | `examples/basic/A13_exabgp_control_plane/output` | ExaBGP 工具节点 | tool node、peer、dashboard、event evidence | 高 |
| `Z02` | `A02_transit_as_mpls` | `examples/basic/A02_transit_as_mpls/output` | FRR/MPLS 控制面检查 | backend 判断、FRR/MPLS 证据位点 | 中高 |
| `Z28` | `B28_traffic_generator` | `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output` | 非 BGP 泛化样本 | generator/receiver 运行态识别 | 中高 |
| `Z01` | `Y01_bgp_prefix_hijacking` | `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output` | 安全 drill 候选 | hijack 观察与演练设计 | 中 |

推荐现场顺序：

1. `B29`
2. `B00`
3. `A14`
4. `A12`
5. `A13`
6. `A02`
7. `B28`
8. `Y01`

---

## 2. B00: 通用 routing 运维主线

### 2.1 位置

- bundle: `Z00`
- 源 baseline: `B00_mini_internet`
- output: `examples/internet/B00_mini_internet/output`

### 2.2 这个网络是干什么的

这是最适合做“接管一个已经运行的互联网风格网络”的基本盘。

它不是服务故事。
它更像一个通用 routing 运维场：

- BGP 异常排查
- 路径维护
- 路由关系推断
- 收敛对比
- 带回滚的 prefix hijack drill

如果你要证明“这个智能体不是只会跟着说明书修一个写死的小 bug”，`B00` 很重要。

### 2.3 最推荐让智能体干什么

- 根据运行态推断谁像 border router / route server / host
- 推断谁和谁像 peer
- 判断哪些路径本来应该通，哪些不一定应该直通
- 定位 BGP flap 或 path degradation
- 设计一次带 rollback 的 routing drill

### 2.4 推荐提示词

#### A. 只做运行态接管

```text
接管当前唯一在线的运行网络。
请只根据运行态告诉我：
1. 哪些节点像 border router / route server / host
2. 哪些 AS 之间像是直接 peer
3. 你判断的依据是什么
```

#### B. 做路径/路由排障

```text
接管当前运行网络，只做 read-only。
帮我定位当前最可能的 BGP flap 或路径异常断点。
先告诉我最有价值的第一步，不要直接做变更。
```

#### C. 做推理题

```text
请只根据运行态信息推断：
哪些路径应该可达，哪些不一定应该直达，
并明确区分高置信结论和推断结论。
```

#### D. 做受控实验前的设计

```text
接管当前运行网络。
请设计一次最小范围、可回滚的 prefix hijack drill。
先不要执行，只把作用范围、风险、回滚点和验证点说清楚。
```

#### E. 老师指定的 FRR 迁移实验

```text
接管当前运行网络。
在 mini-internet 里选几个最合适的 BGP 路由器，
把它们的 BIRD 运行时替换成 FRRouting，并补齐相应配置，
目标是尽量不破坏现有对等关系与可达性。
先不要直接大范围改动。
请先告诉我：
1. 你建议选哪些路由器，为什么
2. 这些节点当前的 BGP 邻居和风险点是什么
3. 你准备怎么把 BIRD 改成 FRR
4. 你怎么验证替换成功且网络仍然正常
5. 你怎么回滚
```

如果你想让它直接进入“先做方案，再执行”的节奏，可以继续说：

```text
按你刚才选的那几个路由器，先做最小变更方案。
方案确认后，再逐台替换，并在每台替换后做邻居状态、路由可见性和基本连通性验证。
```

如果你想压它不要只说不做，可以再补一句：

```text
不要只给我迁移想法。
请先做只读基线核对，再给我一个可执行的逐步替换与验证计划。
```

### 2.5 老师指定实验：把 BIRD 换成 FRR

这是 `B00` 里一个很重要的增强实验。

它测的不是普通排障，而是：

- 智能体能不能从当前运行态里挑出**最合适**的几个 BGP 路由器
- 它能不能判断替换成 FRR 后哪些邻居/配置最容易出问题
- 它能不能把“替换、验证、回滚”这三件事连起来

这个实验最适合讲的点是：

- 它不是只会修一个已经发生的问题
- 它可以主动做一个控制面迁移实验
- 而且这个实验不是拍脑袋改配置，必须带验证和回滚

### 2.6 这个实验里，什么叫“合理”

理想情况下，它应该先做这几步：

1. 先选节点，而不是一上来全换
2. 先说明为什么选这些节点
3. 先拉当前 BGP 邻居和路由基线
4. 再设计 BIRD -> FRR 的最小迁移步骤
5. 每换一台就验证：
   - 邻居是否还在
   - 路由是否还可见
   - 基本连通性是否还正常
6. 保留回滚方法

你希望它优先说清楚的，不是“FRR 很 popular”，而是：

- 哪些节点最适合先换
- 为什么这些节点风险最低/代表性最高
- 怎么证明换完以后网络没坏

### 2.7 你人该看什么

这个实验里你重点盯：

- 它选的 router 合不合理
- 它会不会一下子贪心选太多点
- 它是不是先做 baseline，再改
- 它有没有把验证写清楚，而不是只说“应该能 work”
- 它会不会主动保留 rollback

如果它一上来就想“把所有 BIRD 都换成 FRR”，那通常是不成熟的。

### 2.8 这个实验最适合的演示口径

你可以对老师直说：

- 这不是起网络
- 这不是修一个现成 bug
- 这是让智能体在一个已经运行的 mini-internet 上，自己挑选合适的 BGP 路由器，尝试把 BIRD 迁移成 FRR，并证明迁移后控制面仍然正常

### 2.9 你可以怎么追问它

如果第一轮回答太空，你可以继续压它：

```text
不要先给我大而全的迁移想法。
先只选 1 到 3 台最值得先换的 BGP 路由器，
并告诉我每一台替换前后你准备用什么证据判断成功或失败。
```

或者：

```text
如果只能先换一台，选哪一台最合理？
请给我最小风险答案。
```

### 2.10 你可以故意搞什么问题

- 做 path degradation，再让它排障
- 做 latency fault，再让它比较前后差异
- 做 prefix hijack drill，再让它说明 before/during/after
- 不直接给它“谁有问题”，只说“网络似乎不稳定”，看它会不会自己缩 scope
- 明确要求它做 BIRD -> FRR 迁移，看它会不会先做基线核对和最小风险选点

### 2.11 你人该看什么

- 它是不是先走 `routing_protocol_summary`、`routing_looking_glass`、`traceroute`
- 它会不会一上来就满世界 `ops_exec`
- 它能不能把“peer 关系”和“可达性关系”分开讲
- 它会不会承认不确定性，而不是乱编 topology
- 做 FRR 迁移实验时，它会不会把“选点、验证、回滚”说完整

### 2.12 map.html 里看什么

- AS 分布
- border router 的位置
- 你怀疑有问题的 router 周围连接是不是合理
- 智能体说的“谁像 peer”在图上是否说得通
- 如果它建议先替换某些 router，你看这些 router 在图上是不是确实是合理的最小风险位置

### 2.13 相关任务/旧 showcase

相关任务：

- `TS_B00_BGP_FLAP_ROOTCAUSE`
- `RS_B00_CONVERGENCE_COMPARISON`
- `TS_B00_PREFIX_HIJACK_LIVE`

旧 showcase：

- `examples/agent-base/S02_b00_path_maintenance`
- `examples/agent-base/S03_b00_latency_experiment`

### 2.14 当前建议

这是最适合讲“泛化 routing 运维能力”的 baseline。

如果老师问：
“它不看拓扑，怎么知道谁跟谁有关系？”

你就拿 `B00` 回答。

---

## 3. B29: 网络 + 服务联合排障主线

### 3.1 位置

- bundle: `Z29`
- 源 baseline: `B29_email_dns`
- output: `examples/internet/B29_email_dns/output`

### 3.2 这个网络是干什么的

这是当前仓库里最强的 end-to-end runtime ops 主线。

它不只是“网络通不通”。
它强调：

- mail reachability
- DNS 和 mail logs
- disturbance recovery
- bounded security triage

这很适合现场讲“智能体能不能在已经起好的网络上，像一个运维助手一样做事”。

### 3.3 最推荐让智能体干什么

- 从 source client 到 mail/dns 目标节点做 reachability diagnosis
- 联合看 routing 和 service logs
- 判断是服务异常、DNS 异常，还是路径异常
- 做 bounded disturbance 实验并验证 recovery
- 做可疑 domain/sender 的 triage

### 3.4 推荐提示词

#### A. 最稳 read-only 入口

```text
接管当前唯一在线的运行网络。
只做 read-only。
帮我理解当前 mail 和 DNS 环境里有哪些关键节点、它们大概分别负责什么。
先告诉我最有价值的第一步。
```

#### B. mail reachability debug

```text
接管当前运行网络，只做 read-only。
帮我诊断某个 source 到某个 mail 或 DNS 节点为什么不通。
优先看 routing 和 service logs，不要直接做变更。
```

#### C. abuse triage

```text
接管当前运行网络。
围绕某个可疑 sender 或 domain 做 mail 和 DNS triage。
先判断异常证据，再告诉我最安全的 containment 建议。
```

#### D. disturbance recovery

```text
接管当前运行网络。
如果我想做一次受控 packet loss 或 service disturbance 实验，
你先帮我设计 before/during/after 的观测点和 rollback 点。
```

### 3.5 你可以故意搞什么问题

- packet loss
- mail reachability 异常
- DNS/mail abuse 事件
- 只给一个很模糊的症状，让它自己找 routing 还是 service 根因

### 3.6 你人该看什么

- 它是不是把 service 层和 routing 层一起看
- 它是不是先缩到相关 host/router，再去看 logs
- 它会不会只说“容器都在，所以正常”
- 它能不能给出 bounded next action，而不是一句空话

### 3.7 map.html 里看什么

- client、mail、dns 这些关键 host 的位置
- 智能体锁定的目标节点是不是合理
- 如果它说“问题更像路径不是服务”，图上是否说得通

### 3.8 相关任务/旧 showcase

相关任务：

- `TS_B29_MAIL_REACHABILITY_DEBUG`
- `RS_B29_FAULT_IMPACT_ABLATION`
- `SEC_B29_DNS_MAIL_ABUSE_RESPONSE`
- `SEC_B29_SOCIAL_ENGINEERING_TRIAGE`

旧 showcase：

- `examples/agent-base/S01_b29_health_maintenance`
- `examples/agent-base/S04_b29_packetloss_experiment`

### 3.9 当前建议

如果你只能先选一个 baseline 给老师看，优先 `B29`。

因为它最容易让人理解“这个智能体不是在玩具网络里瞎跑，而是在一个真有服务语义的运行网络里帮你干活”。

---

## 4. Y01: 安全 drill 候选

### 4.1 位置

- bundle: `Z01`
- 源 baseline: `Y01_bgp_prefix_hijacking`
- output: `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output`

### 4.2 这个网络是干什么的

这是 routing-security 的强故事样本。

但它不是首秀路径。
更适合作为：

- 安全观察方案设计
- prefix hijack before/during/after 证据设计
- live drill 前的 scope reasoning

### 4.3 推荐提示词

```text
接管当前唯一在线的运行网络。
不要执行任何 live 动作。
请告诉我如果当前网络里发生 prefix hijack，最该看哪些证据面，
并把 before / during / after 分开说。
```

或者：

```text
请只根据运行态，设计一套 prefix hijack 观察方案，
说明哪些结论你能直接确认，哪些只能推断。
```

### 4.4 你人该看什么

- 它会不会先做 read-only 环境理解
- 它会不会把“观察方案”和“直接攻击动作”分开
- 它会不会乱跳到高风险动作

### 4.5 当前建议

把它当成安全候选，不要当第一场主秀。

---

## 5. A02: FRR/MPLS 控制面检查

### 5.1 位置

- bundle: `Z02`
- 源 baseline: `A02_transit_as_mpls`
- output: `examples/basic/A02_transit_as_mpls/output`

### 5.2 这个网络是干什么的

它更偏控制面，不偏服务故事。

重点是：

- mixed backend 判断
- MPLS/FRR 证据位点识别
- 高层 routing 工具是不是能先给出正确方向

### 5.3 推荐提示词

```text
接管当前唯一在线的运行网络，只做 read-only。
先总结当前 routing backend 的行为，
再告诉我哪些节点和哪些证据位点必须用 FRR/MPLS 显式检查。
```

或者：

```text
优先用高层 routing 工具。
只有当高层证据不够时，再告诉我为什么需要 vtysh。
```

### 5.4 你人该看什么

- 它是不是先用 `routing_protocol_summary(auto)`
- 它会不会一上来就 `ops_exec vtysh`
- 它能不能把“FRR negative signal”也识别成证据

### 5.5 当前建议

这个适合讲“控制面工具链很懂协议”，
不适合当“最容易理解的第一场 demo”。

---

## 6. A12: FRR 迁移与 live drill 主线

### 6.1 位置

- bundle: `Z12`
- 源 baseline: `A12_bgp_mixed_backend`
- output: `examples/basic/A12_bgp_mixed_backend/output`

### 6.2 这个网络是干什么的

这是现在 FRR 主线的核心 baseline。

它的意义不是“起一个网络”。
它的意义是：

- 区分 BIRD 和 FRR
- 看 mixed backend 是否能互通
- 在不破坏全网的前提下做 FRR prefix announce/withdraw/rollback

### 6.3 最推荐让智能体干什么

- 识别哪些 router 跑的是 BIRD，哪些是 FRR
- 说明 mixed backend 的边界
- 设计并执行最小范围 FRR live drill
- 做 rollback 和 post-check

### 6.4 推荐提示词

#### A. read-only 审计版

```text
接管当前唯一在线的运行网络，只做 read-only。
帮我区分哪些 router 跑的是 BIRD，哪些跑的是 FRR，
并判断现在最安全的 FRR 迁移下一步是什么。
```

#### B. FRR drill 设计版

```text
接管当前运行网络。
我想做一次可回滚的 FRR prefix announce/withdraw drill。
先不要执行，先给我最小范围、回滚点、post-check 和风险说明。
```

#### C. FRR drill 执行版

```text
接管当前运行网络。
在最小范围内执行一次 FRR prefix announce/withdraw drill，
先做基线，再变更，再回滚，再复验，
不要扩大作用范围。
```

### 6.5 你可以故意搞什么问题

- 让它先判断哪里是 FRR，哪里不是
- 让它做 controlled announce / withdraw
- 看它 rollback 后会不会补 post-check
- 看它会不会把非 FRR 节点也拿去做无意义 `vtysh`

### 6.6 你人该看什么

- 它是不是先 baseline，再 announce，再 rollback，再复验
- 它是不是优先用 routing 工具，再用少量定点 `ops_exec`
- 它会不会乱对 BIRD 节点打 `vtysh`
- 它会不会只报“成功”而不给强证据

### 6.7 map.html 里看什么

- FRR customer router
- route server
- 下游 border router
- 这些位置关系和它的叙述是不是一致

### 6.8 本轮真实情况

这轮要分开讲。

#### A12 read-only audit

- `TS_A12_FRR_BACKEND_AUDIT`
- 这轮不够好
- planner 还是退到了 fallback
- 这说明“backend 审计”这条 read-only 主线还要继续加强

#### A12 live drill

- `RS_A12_FRR_ROUTE_INJECTION_LIVE`
- 这轮是真的跑通了
- 结果是：`llm_primary`、`fallback_used=false`、`rollback_status=verified`
- 说明它已经能做受控 FRR drill，不只是会聊天

但要诚实讲：

- 现在“announce 后 prefix 可见性”的强证据还不够硬
- 所以它已经能做，但证据闭环还在继续打磨

### 6.9 当前建议

如果你要讲 FRR，这就是主 baseline。

但现场说法要准确：

- “它已经能做 FRR 动态 drill 并回滚”
- 不要说成“所有 FRR 验证都已经完全完美”

---

## 7. A13: ExaBGP 工具节点

### 7.1 位置

- bundle: `Z13`
- 源 baseline: `A13_exabgp_control_plane`
- output: `examples/basic/A13_exabgp_control_plane/output`

### 7.2 这个网络是干什么的

它不是“普通业务网络”。
它的核心是把 ExaBGP 作为可复用的 control-plane tool node 放进来。

所以它最适合回答的问题是：

- 当前网络里哪个节点更像 control-plane tool
- 它和谁 peer
- 它有哪些 announcement / event / dashboard 面
- 后续实验怎么复用它

### 7.3 推荐提示词

```text
接管当前唯一在线的运行网络，只做 read-only。
找到最像 control-plane tool 的节点，
判断它是不是 ExaBGP，
并说明它和谁 peer、有哪些 dashboard/event/config 证据面。
```

或者：

```text
请把当前网络里可复用的 BGP 工具节点找出来，
并解释后续可以拿它做什么实验。
```

### 7.4 你人该看什么

- 它是不是先锁定 host，再看 logs / config / process
- 它会不会把 ExaBGP 当成普通 router
- 它会不会说明这个节点后续实验里的“工具角色”

### 7.5 map.html 里看什么

- ExaBGP host 所在 AS
- 它和 peer router 的位置关系

### 7.6 当前建议

这是讲“ExaBGP 作为嵌入式 control-plane tool”的最佳 baseline。

---

## 8. A14: looking glass / event dashboard 双视角

### 8.1 位置

- bundle: `Z14`
- 源 baseline: `A14_bgp_event_looking_glass`
- output: `examples/basic/A14_bgp_event_looking_glass/output`

### 8.2 这个网络是干什么的

它的核心不是“修 bug”。
而是“解释可观察性”。

同一个网络里有两种观察面：

- route-table looking glass
- ExaBGP event dashboard

老师一看就容易懂。

### 8.3 最推荐让智能体干什么

- 找到 classic LG
- 找到 ExaBGP event dashboard
- 解释哪个看状态，哪个看事件
- 解释为什么这两个页面不能混为一谈

### 8.4 推荐提示词

```text
接管当前唯一在线的运行网络，只做 read-only。
找到 route-table looking glass 和 event dashboard，
解释这两个页面分别说明什么，回答的问题有什么不同。
```

或者：

```text
请把当前网络里的 BGP 可观察性界面都找出来，
并区分哪个看 route state，哪个看 event stream。
```

### 8.5 你人该看什么

- 它是不是先走 routing，再走日志，再落到页面解释
- 它会不会把 route-table view 和 event view 说成一回事
- 它会不会乱用 shell，而不是先用已有工具

### 8.6 map.html 和页面里看什么

- map 里看 as2 的 looking-glass host、as151 的 event-viewer host
- classic LG 页面真实入口一般会跳 `/summary/router0`
- event dashboard 看的是 ExaBGP 事件流，不是静态路由表

### 8.7 本轮真实情况

这轮 live 跑过，而且是目前最适合讲的一个。

你可以把它当“解释能力 + 页面能力 + 运行态证据能力”的主 showcase。

---

## 9. B28: 非 BGP 运行态角色识别

### 9.1 位置

- bundle: `Z28`
- 源 baseline: `B28_traffic_generator`
- output: `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output`

### 9.2 这个网络是干什么的

它是最好的非 BGP 泛化样本。

重点不是控制面，而是：

- 只看运行态，判断谁是 generator
- 判断谁是 receiver
- 再提出实验设计

### 9.3 推荐提示词

```text
接管当前唯一在线的运行网络，只做 read-only。
不要根据例子名字猜。
只根据运行态告诉我谁是 traffic generator，谁是 receiver，
并给我一个最合理的小实验设计。
```

### 9.4 你人该看什么

- 它是不是根据进程、端口、日志、类角色来判断
- 它会不会空口断言 generator/receiver
- 它能不能把“角色识别”和“实验设计”连起来

### 9.5 当前建议

如果你想证明“它不是只会 BGP”，拿 `B28`。

---

## 10. 给老师讲时，每个 baseline 最短的一句话

| baseline | 一句话介绍 |
| --- | --- |
| `B00` | 这是通用 routing 运维场，重点看它能不能只靠运行态推断控制面关系。 |
| `B29` | 这是网络加服务联合排障场，重点看它能不能同时理解 routing 和 mail/DNS logs。 |
| `Y01` | 这是安全 drill 候选，重点不是直接攻击，而是设计观察与取证方案。 |
| `A02` | 这是控制面工具链验证场，重点看它能不能正确判断 FRR/MPLS 证据位点。 |
| `A12` | 这是 FRR 主线，重点看它能不能做 announce/withdraw/rollback 并保持网络稳定。 |
| `A13` | 这是 ExaBGP 工具节点场，重点看它能不能识别并复用 control-plane tool。 |
| `A14` | 这是 BGP 可观察性场，重点看它能不能区分 route-state 和 event-stream。 |
| `B28` | 这是非 BGP 泛化样本，重点看它能不能从运行态识别 generator/receiver。 |

---

## 11. 你自己操作时的最小建议

### 最稳主入口

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

### 切 baseline 的纪律

- 一次只起一个
- 切换前先 `down`
- 切换后再进 `ui`

### 你在现场不要默认做的事

- 不要默认补充源码或拓扑定义信息
- 不要默认把“谁坏了”直接点出来
- 不要默认替它选定所有节点

### 你应该让它自己回答的事

- 当前网络里谁是关键节点
- 它先做什么
- 为什么先做这个
- 哪些结论是证据，哪些只是推断

---

## 12. 当前最适合首秀的三个

如果你只想先拿三套最稳的：

1. `B29`
2. `A14`
3. `A12`

如果你还想补一个“泛化 routing 推理”：

4. `B00`

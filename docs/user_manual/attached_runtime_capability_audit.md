# SEED Attached-Runtime 展示手册与场景地图

Last updated: 2026-04-02

说明：

- 这个文件保留旧路径 `attached_runtime_capability_audit.md`，但当前用途已经从“纯能力审计”切到“展示手册 + 场景地图”。
- 今天展示的重点不是造网，而是 **SEED 已运行网络上的智能体 attached-runtime 闭环**。

---

## 1. 今天现场展示什么

先把口径说死：

- **B00/B29 不是全部潜力**，只是当前 agent/ops 闭环最成熟的样板。
- **真正要展示的，是 SEED 的场景广度**：A/B/D/S/Y 多个系列都能变成智能体场景池。
- 今天交付分两层：
  - **现场 live 层**：只跑最稳的 2 到 3 个样板，保证不翻车。
  - **潜力展示层**：把更多 example 组织成可扩展的 agent-ready 场景地图。

### 1.1 现场 live 层：两层三段

| 段落 | 故事类型 | 推荐入口 | 推荐样板 | 现场要证明什么 |
|---|---|---|---|---|
| 主线 1 | 运行时接管与环境理解 | `scripts/seed-codex up` + `scripts/seed-codex ui` | `examples/internet/B29_email_dns/output` | agent 进入运行中的网络后不是闲聊，而是知道自己在哪、有什么节点、下一步该问什么 |
| 主线 2 | 受控实验与回滚 | `examples/agent-base/S04_b29_packetloss_experiment/run.sh` | B29 packet-loss | 系统不只会观察，还能做受控扰动、前后对比、rollback 和证据输出 |
| 压轴备选 | 路由安全演练 | `examples/agent-missions/run_task_demo.sh --task TS_B00_PREFIX_HIJACK_LIVE ...` | B00 prefix hijack | 展示高冲击力的安全操作能力，但它是备选，不是唯一依赖 |

### 1.2 现场口径

今天现场只讲三件事：

1. agent 如何进入一个已经运行的网络并理解环境。
2. agent/ops 栈如何执行一次受控动作并验证结果。
3. 这只是样板，不是能力边界。

### 1.3 现场推荐命令

#### A. 进入 live 交互主线

```bash
cd /home/parallels/seed-email-service
scripts/seed-codex up
scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

进入 UI 后，主线提示词固定为：

```text
Attach to examples/internet/B29_email_dns/output, summarize the running environment, identify the key mail and DNS nodes, explain the current operational scope, and ask only for the missing inputs needed to debug a concrete mail reachability issue.
```

#### B. 第二幕：受控实验与回滚

```bash
cd /home/parallels/seed-email-service
./examples/agent-base/S04_b29_packetloss_experiment/run.sh \
  --mode canonical \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

#### C. 压轴备选：路由安全演练

```bash
cd /home/parallels/seed-email-service
examples/agent-missions/run_task_demo.sh \
  --task TS_B00_PREFIX_HIJACK_LIVE \
  --objective "Run live prefix hijack drill and rollback" \
  --attach-output-dir examples/internet/B00_mini_internet/output \
  --context-json '{"target_prefix":"10.150.0.0/24","attacker_asn":"151"}' \
  --risk on \
  --confirm-token YES_RUN_DYNAMIC_FAULTS
```

### 1.4 为什么不展示造网

今天展示的是 **runtime intelligence**，不是 build path。

- build path 证明 SEED 能造复杂网络。
- attached-runtime path 证明智能体能接管一个已经跑起来的网络，并在边界内观察、试验、验证、留证据。

这两件事都重要，但今天主角是后者。

---

## 2. SEED 的场景版图

这部分是今天必须展示给老师同学看的“潜力池”。

### 2.1 按系列看 example 版图

| 系列 | 代表例子 | 场景意义 | 是否适合转成 attached-runtime agent demo |
|---|---|---|---|
| `A` | `A20_nano_internet`, `A21_shadow_internet`, `A03_real_world`, `A07_compilers` | 从最小 Internet、真实网络接口到编译器/组件机制，体现 SEED 的建模与组合能力 | 适合做“网络运维入门”“拓扑解释”“build-to-runtime bridging” |
| `B` | `B22_botnet`, `B23_darknet_tor`, `B24_ip_anycast`, `B25_pki`, `B26_ipfs_kubo`, `B28_traffic_generator`, `B29_email_dns` | Internet、服务、基础设施、安全、分布式系统都在同一仿真器里 | 最适合转 agent，当前样板也主要集中在这里 |
| `D` | `D00_ethereum_poa`, `D01_ethereum_pos`, `D20_faucet`, `D31_chainlink`, `D60_monero` | 区块链网络、合约、oracle、链上服务编排 | 适合做“复杂系统运维”“链上实验助手”“协议事件排查” |
| `S` | `S01_scion`, `S02_scion_bgp_mixed`, `S05_scion_internet` | 新型网络体系、SCION/BGP 混合网络、跨协议实验平台 | 适合做“新协议实验伙伴”和“混合网络调试” |
| `Y` | `Y01_bgp_prefix_hijacking`, `Y02_morris_worm`, `Y03_mirai` | 历史攻击复现、攻防教学、传播与防护行为观察 | 适合做“路由安全演练”“攻击复现监督执行”“传播实验验证” |

### 2.2 按场景族看 attached-runtime 路线

| 场景族 | 当前样板 | 未来扩展来源 | 讲给别人听的意思 |
|---|---|---|---|
| 网络运维与诊断 | `TS_B29_MAIL_REACHABILITY_DEBUG`, `S02_b00_path_maintenance` | `A20`, `A21`, `B20`, `B21` | agent 不是聊天助手，而是运行中网络的维护助手 |
| 受控实验与扰动 | `S03_b00_latency_experiment`, `S04_b29_packetloss_experiment` | `B28`, `RS_B00_CONVERGENCE_COMPARISON` | agent 不只观察，还能组织实验、对比结果、回滚恢复 |
| 路由安全与攻防 | `TS_B00_PREFIX_HIJACK_LIVE` | `Y01_bgp_prefix_hijacking`, `B25_pki` | agent 可以在受控边界内做安全演练和恢复验证 |
| 服务与基础设施 | `B29_email_dns` | `B01/B02 DNS`, `B24 anycast`, `B25 PKI` | 邮件、DNS、PKI、Anycast 都能变成智能体目标网络 |
| 新型网络与平台 | 当前还没有 attached-runtime 样板包 | `B23`, `B26/B27`, `B50`, `S01/S02/S05` | 未来不是只做传统 Internet，还能做 IPFS、Tor、SCION |
| 区块链与复杂系统 | 当前还没有 attached-runtime 样板包 | `D00/D01/D20/D31/D60` | 未来可以把 agent 扩到链上节点、oracle、合约交互系统 |

### 2.3 固定场景地图

下面这些例子必须在文档里点名。每个例子只回答两个问题：

- 它体现了 SEED 的什么能力？
- 它未来如何转成 agent 示例？

| 例子 | 它体现了什么能力 | 未来如何转成 agent 示例 |
|---|---|---|
| `A20_nano_internet` | 最小 Internet 级建模、基础 AS/BGP 结构 | 做“最小运维样板”，适合新人理解 agent 如何读 topology 和 runtime |
| `A21_shadow_internet` | Shadow Internet、现实拓扑抽象 | 做“真实网络映射解释器”，让 agent 帮用户读懂复杂拓扑 |
| `B22_botnet` | 恶意控制面、C2、受感染节点行为 | 做“botnet 观察与 containment” 场景 |
| `B23_darknet_tor` | Tor/Darknet 网络、匿名通信环境 | 做“匿名网络健康与异常流量诊断” 场景 |
| `B24_ip_anycast` | Anycast 服务与路径差异 | 做“多入口服务 reachability/route selection” 场景 |
| `B25_pki` | PKI、证书、信任链与服务验证 | 做“证书故障/信任链排障/安全验证” 场景 |
| `B26_ipfs_kubo` | 分布式内容寻址网络 | 做“内容分发与节点健康诊断” 场景 |
| `B27_ipfs_kubo_dapp` | IPFS + dApp 复合系统 | 做“多层服务协同排障” 场景 |
| `B28_traffic_generator` | 流量生成、压力/负载实验 | 做“流量实验助手”和“性能对比场景” |
| `B29_email_dns` | 邮件、DNS、BGP、服务日志和跨域路径全都在一张网里 | 继续作为 attached-runtime 主样板，做运维、安全、实验三类故事 |
| `D00_ethereum_poa` | 私有链、节点编排、链上共识环境 | 做“链网络状态巡检”和“服务恢复” 场景 |
| `D01_ethereum_pos` | 更复杂的 PoS 链环境 | 做“多角色链网络运维”和“协议状态排障” 场景 |
| `S02_scion_bgp_mixed` | SCION 与 BGP 混合网络 | 做“混合协议实验助手” 场景 |
| `S05_scion_internet` | 更完整的 SCION Internet 拓扑 | 做“新协议运行状态理解”和“跨域实验编排” 场景 |
| `Y01_bgp_prefix_hijacking` | 经典路由安全攻击复现 | 做更强版本的 prefix hijack 教学和 rollback 演练 |
| `Y03_mirai` | 大规模感染、传播与攻击复现 | 做“传播实验观察”“安全响应” 和“证据驱动分析” 场景 |

---

## 3. 为什么今天 live 只用少数样板

这一段必须直说，不绕。

### 3.1 不是仓库里只有 B00/B29

仓库里明显不止 `B00/B29`：

- `A` 系列负责建模、组件、编译器和真实接口
- `B` 系列覆盖 Internet、DNS、Tor、Botnet、Anycast、PKI、IPFS、Email
- `D` 系列覆盖 Ethereum、oracle、Chainlink、Monero
- `S` 系列覆盖 SCION 和混合网络
- `Y` 系列覆盖 prefix hijack、Mirai、Morris worm 等历史攻击复现

### 3.2 但今天展示的是 attached-runtime agent 闭环

今天不是在比谁的 example 多，而是在比：

- agent 是否能 attach 到已运行网络
- 是否有稳定的风险门
- 是否有 rollback
- 是否有结构化 evidence
- 是否有任务/实验/报告闭环

从这个标准看，当前真正成熟的样板主要集中在少数场景。

### 3.3 三档划分

#### A 档：今天已经适合 live attached-runtime + agent 展示

| 样板 | 当前定位 |
|---|---|
| B29 邮件网络运维 | 主线 1，展示环境感知与多轮任务理解 |
| B29 packet-loss 实验 | 主线 2，展示受控实验与 rollback |
| B00 path / latency | maintenance / experiment 备选 |
| B00 live prefix hijack | 高冲击力压轴备选 |

#### B 档：今天适合展示为“SEED 场景池”，但不拿来冒险 live

| 例子 | 今天怎么讲 |
|---|---|
| `A20_nano_internet`, `A21_shadow_internet` | 讲基础网络样板和拓扑解释潜力 |
| `B22_botnet`, `B23_darknet_tor` | 讲安全与匿名网络场景池 |
| `B24_ip_anycast`, `B25_pki` | 讲服务基础设施和安全验证潜力 |
| `B26/B27 IPFS` | 讲分布式系统与 dApp 场景 |
| `D00/D01 Ethereum` | 讲区块链运行时实验平台潜力 |
| `S02 SCION+BGP mixed` | 讲新协议和混合网络潜力 |
| `Y01/Y03` | 讲历史攻击复现可转成智能体教学/演练 |

#### C 档：后续要系统化转成 agent-ready 的

后续不再平均撒网，而是每个大类先做一个标杆包：

- Internet
- Security
- Experiment
- SCION
- Blockchain

每个标杆包都要补齐：

- task
- playbook
- risk gate
- evidence contract
- review output

---

## 4. 后续扩展与协作方式

### 4.1 场景转 agent-ready 的标准

以后任何新 example 要转成 agent-ready，至少要补齐下面这些东西：

1. 已运行 `output/` 的 attach 入口。
2. 一个一句话能说清的目标。
3. 至少一个可观察信号。
4. 明确的成功条件。
5. 如果有风险动作，必须有确认门。
6. 如果会改状态，必须有 rollback。
7. 必须有结构化 evidence / artifact 输出。

这七条不满足，就还只是“好例子”，不是“可复用的智能体样板”。

### 4.2 建议分工

| 组别 | 负责什么 | 第一批 checkpoint |
|---|---|---|
| 网络运维组 | 把 Internet 类场景转成稳定 attached-runtime 任务 | `A20` 或 `B24` 补一个 maintenance 样板 |
| 安全演练组 | 把安全类场景做成有风险门和 rollback 的任务 | `Y01` 或 `B25` 补一个 security 样板 |
| 实验自动化组 | 把扰动和对比类场景做成 before/during/after 闭环 | `B28` 或 `RS_B00_CONVERGENCE_COMPARISON` 补一个 experiment 样板 |
| 新协议/新平台组 | 把 SCION/IPFS/Tor/区块链转成可 attach 的 runtime story | `S02` 或 `D00` 补一个 attached-runtime 样板 |
| 文档与 review 组 | 做口播、report、review pack、场景地图和证据规范 | 统一 example-to-agent 模板和 review 清单 |

### 4.3 最小后续计划

第一轮不求全覆盖，只求每个大类做出一个真正能复用的标杆：

- Internet：`B24_ip_anycast` 或 `A20_nano_internet`
- Security：`Y01_bgp_prefix_hijacking` 或 `B25_pki`
- Experiment：`B28_traffic_generator`
- SCION：`S02_scion_bgp_mixed`
- Blockchain：`D00_ethereum_poa`

每个标杆都按同一 contract 落地：

- 有任务定义
- 有 playbook
- 有策略门
- 有 evidence contract
- 有 review 输出

---

## 5. 今天交付的底线

最后只保留三句最重要的话：

1. **B00/B29 是样板，不是能力边界。**
2. **今天 live 只用少数样板，是为了稳，不是因为仓库里只有这两个。**
3. **真正的长期方向，是把 A/B/D/S/Y 多个系列逐步转成标准 agent-ready 场景包。**

# SEED Agent 运行与测试速查

Last updated: 2026-04-04

目标：

- 这不是设计文档。
- 这不是能力审计。
- 这是给你自己跑、切例子、现场兜底用的。

---

## 1. 先记住这几条

- 主路径是 `scripts/seed-codex ui`。
- `mission` 只是辅助，不是主展示方式。
- 一次只起一个网络。
- 先让网络跑起来，再让 agent 接管。
- 先用只读 prompt 探环境，再做更具体的诊断或实验。

### 1.1 演示前 30 秒自检

先别急着进 UI，先把这三条过掉：

```bash
./scripts/seed-codex status
./scripts/seed-codex inspect
./scripts/seed-codex probe-context \
  --attach-output-dir <OUTPUT_DIR> \
  --workspace-name pre_demo_probe \
  --model gpt-5.4 \
  --reasoning-effort low
```

这三条分别回答：

- `status`
  - MCP 服务有没有起来
- `inspect`
  - 自动激活的 prompt / MCP / skills 到底是什么，plugin 现在是不是空
- `probe-context`
  - 模型是否真的通过 Codex + MCP 理解了当前运行网络

如果这一步过不了，不要直接上老师面前开演。

当前工作区里，已经确认存在 `output/docker-compose.yml` 的 output 池，不止两个：

- `examples/internet/B29_email_dns/output`
- `examples/internet/B00_mini_internet/output`
- `examples/basic/A03_real_world/output`
- `examples/basic/A20_nano_internet/output`
- `examples/basic/A21_shadow_internet/output`
- `examples/internet/B22_botnet/output`
- `examples/internet/B23_darknet_tor/output`
- `examples/internet/B24_ip_anycast/output`
- `examples/internet/B25_pki/output`
- `examples/internet/B26_ipfs_kubo/output`
- `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output`
- `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output`
- `examples/yesterday_once_more/Y03_mirai/demo/output`
- `examples/blockchain/D60_monero/output`

查看本地当前有哪些 ready output：

```bash
find examples -path '*/output/docker-compose.yml' | sort
```

今天这台机子上，真实状态要分开看：

- 已经确认适合拿来演 attached-runtime 的：
  - `examples/internet/B29_email_dns/output`
  - `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output`
- 已经确认例子本身能起，但不适合当主秀的：
  - `examples/basic/A02_transit_as_mpls/output`
  - `examples/yesterday_once_more/Y01_bgp_prefix_hijacking/demo/output`
- 已经确认“容器能起，不等于 workload 真起来”的：
  - `examples/blockchain/D60_monero/output`
- 其他已有 output 但今天没继续压 live 结论的：
  - `examples/basic/A03_real_world/output`
  - `examples/basic/A20_nano_internet/output`
  - `examples/basic/A21_shadow_internet/output`
  - `examples/internet/B22_botnet/output`
  - `examples/internet/B23_darknet_tor/output`
  - `examples/internet/B24_ip_anycast/output`
  - `examples/internet/B25_pki/output`
  - `examples/internet/B26_ipfs_kubo/output`
  - `examples/yesterday_once_more/Y03_mirai/demo/output`
- 首启仍然有明确外部依赖风险：
  - `A03/A20/A21`：第一次 `up -d` 会现场构镜像，Dockerfile 里要在线装 `nginx-light`、`telnet` 等包
  - `Y01/B28/A02/D60`：如果没有本地基础镜像或网络差，第一次 `up -d` 会慢很多

### 1.1 今天真实结论

| 例子 | 结论 | 你该怎么用 |
|---|---|---|
| `B29_email_dns` | `Go` | 主秀，讲环境理解、诊断、实验边界 |
| `B28_traffic_generator` | `Go` | 第二梯队主力，讲运行时识别 generator/receiver 和实验设计 |
| `Y01_bgp_prefix_hijacking` | `Conditional Go` | 只当备选。修完地图镜像依赖后能部分拉起，但启动时间和稳定性都不够秀场友好 |
| `D60_monero` | `No-Go` | 容器和网络能起，但应用 workload 没真正起来，不适合讲“链角色识别” |
| `A02_transit_as_mpls` | `Conditional Go` | 例子可行，FRR/MPLS 证据可取，但更适合讲 control plane/tooling，不适合做主交互故事 |

### 1.2 一个非常有用的本机兜底

不少例子都依赖地图容器 `handsonsecurity/seedemu-internetmap:2.0`。

这台机子上如果它拉不下来，但你已经有：

- `handsonsecurity/seedemu-multiarch-map:buildx-latest`

就先补一个本地 tag：

```bash
docker tag handsonsecurity/seedemu-multiarch-map:buildx-latest \
  handsonsecurity/seedemu-internetmap:2.0
```

这不改仓库代码，只是减少首启被 Docker Hub 卡死的概率。

本轮未准备成功的例子：

- `examples/blockchain/D00_ethereum_poa`
  原因：`Web3.toChecksumAddress` API 已变更，脚本需要适配新版本 `web3.py`
- `examples/scion/S02_scion_bgp_mixed`
  原因：构建期需要访问 `github.com/scionproto/scion.git`，本次请求超时

---

## 2. 最稳的现场主路径

### 2.1 起网

这个环境用的是 `docker-compose` v1，不是 `docker compose`。

B29：

```bash
docker-compose -f examples/internet/B29_email_dns/output/docker-compose.yml up -d
```

B00：

```bash
docker-compose -f examples/internet/B00_mini_internet/output/docker-compose.yml up -d
```

B28：

```bash
docker-compose -f examples/internet/B28_traffic_generator/3-multi-traffic-generator/output/docker-compose.yml up -d
```

### 2.2 起 agent/ops

```bash
./scripts/seed-codex up
./scripts/seed-codex status
```

### 2.3 进入交互

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

### 2.4 参数最少记法

你真正需要记的只有这几个：

- `ui`
  - 主展示入口
  - 例子：
    ```bash
    ./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
    ```
- `-m <model>`
  - 直接指定模型
  - 例子：`-m gpt-5.4`
- `-c '<key=value>'`
  - 给 codex 传运行配置
  - 你今天最常用的是：
    ```bash
    -c 'model_reasoning_effort="low"'
    ```
- `run "<request>"`
  - 非交互自检入口，不是主秀
- `--attach-output-dir <path>`
  - 强制 attach 到你指定的 output，不让它猜
- `--policy <read_only|net_ops|danger>`
  - 先用 `read_only`
- `--workspace-name <name>`
  - 给这次 attach 起名字，方便复用

如果你只想记一条最小可用命令，就是这条：

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

---

## 3. 切换例子的硬规则

不要同时跑两个 baseline。

`B00` 和 `B29` 在这个 Docker host 上会冲突，直接同时起会报网络池重叠。

切换时这样做：

```bash
docker-compose -f examples/internet/B29_email_dns/output/docker-compose.yml down
docker-compose -f examples/internet/B00_mini_internet/output/docker-compose.yml up -d
```

或者反过来：

```bash
docker-compose -f examples/internet/B00_mini_internet/output/docker-compose.yml down
docker-compose -f examples/internet/B29_email_dns/output/docker-compose.yml up -d
```

如果你忘了当前谁在跑，先看：

```bash
docker ps --format '{{.Names}}\t{{.Label "com.docker.compose.project.working_dir"}}' | sort
```

---

## 4. 怎么灵活换别的例子

你以后不是只能玩 `B29/B00`。

真正的条件只有两个：

1. 这个例子已经生成了 `output/docker-compose.yml`
2. 它已经被你成功 `up -d`

只要满足这两个条件，下面所有 prompt 模板里的路径都可以直接替换：

```text
<OUTPUT_DIR>
```

例如以后你生成了这些 output：

- `examples/internet/B23_darknet_tor/output`
- `examples/internet/B24_ip_anycast/output`
- `examples/internet/B25_pki/output`
- `examples/internet/B28_traffic_generator/3-multi-traffic-generator/output`
- `examples/blockchain/D00_ethereum_poa/output`
- `examples/scion/S02_scion_bgp_mixed/output`

你只需要把 prompt 里的 `examples/internet/B29_email_dns/output` 换掉。

### 4.1 A / D 直接起网命令

A03：

```bash
docker-compose -f examples/basic/A03_real_world/output/docker-compose.yml up -d
```

A20：

```bash
docker-compose -f examples/basic/A20_nano_internet/output/docker-compose.yml up -d
```

A21：

```bash
docker-compose -f examples/basic/A21_shadow_internet/output/docker-compose.yml up -d
```

D60：

```bash
docker-compose -f examples/blockchain/D60_monero/output/docker-compose.yml up -d
```

A02 先生成 output，再起网：

```bash
cd examples/basic/A02_transit_as_mpls
PYTHONPATH=/home/parallels/seed-email-service python transit_as_mpls.py arm
docker-compose -f output/docker-compose.yml up -d
```

然后统一接：

```bash
./scripts/seed-codex up
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

如果你不是走 `seed-codex run/ui`，而是自己直接调 SeedOps HTTP/API 的 `workspace_attach_compose`，`output_dir` 要传绝对路径。

如果你只是上台前自检，不想进 UI：

```bash
./scripts/seed-codex run \
  "接管 <OUTPUT_DIR>，只做只读环境理解，告诉我当前网络类型、关键节点、现在适合做的三类任务。" \
  --workspace-name pre_demo_probe \
  --attach-output-dir <OUTPUT_DIR> \
  --policy read_only \
  --follow-job on \
  --download-artifacts off
```

### 4.2 两个你今天会真的用到的细节

- `B28` 已实测可以复用 workspace。
  - 第一次 attach：
    ```bash
    ./scripts/seed-codex run \
      "接管这个运行中的网络，只做只读环境理解。" \
      --workspace-name b28_eval \
      --attach-output-dir examples/internet/B28_traffic_generator/3-multi-traffic-generator/output \
      --policy read_only
    ```
  - 后续复用同一个 workspace，可以不再传 `--attach-output-dir`：
    ```bash
    ./scripts/seed-codex run \
      "继续用已有 workspace，只做只读刷新和证据采集。" \
      --workspace-name b28_eval \
      --policy read_only
    ```
- `A02` 如果你要讲 FRR/MPLS，不要只讲“网络起来了”。
  - 重点应该讲：`routing_protocol_summary`、`routing_looking_glass`、`vtysh` 证据。
  - 现在的 `auto` 会先探测 `birdc` / `vtysh` 和活跃 daemon，再决定顺序。
  - 对 `r2/r3` 这类只有 FRR OSPF/LDP、没有 `bgpd` 的 MPLS 核心节点，`auto` 会回到 `bird`，不会把 `bgpd is not running` 误当成成功摘要。
  - 如果你要讲 FRR/MPLS，本轮应该显式看 `vtysh` 证据，例如 `show running-config`、`show mpls ldp discovery`，而不是把 `backend=frr` 的负结果当成成功。

---

## 5. Prompt 模板

这些模板是主力。不要背复杂命令，直接在 UI 里换目标和故事。

### 5.1 环境理解

```text
接管这个正在运行的网络。优先使用已有 workspace；如果不可用，再 attach 到 <OUTPUT_DIR>。先告诉我你当前看到的运行环境、网络规模、关键节点/关键 AS、默认策略，以及你现在能直接做的三类事情。不要做写操作。
```

### 5.2 定向诊断

```text
接管 <OUTPUT_DIR>，只做只读检查。聚焦 <目标 AS / 目标节点 / 目标服务>，检查当前拓扑、BGP 状态、关键日志和最可疑异常。输出要求：结论、证据、下一步建议。
```

### 5.3 实验设计，不执行

```text
接管 <OUTPUT_DIR>。围绕 <目标节点/目标链路/目标服务> 设计一个受控实验。先不要执行，只给我：作用范围、预期现象、风险门、回滚方式、需要收集的证据。
```

### 5.4 安全演练，不执行

```text
接管 <OUTPUT_DIR>。围绕 <prefix hijack / abuse chain / botnet / service compromise> 设计一次受控安全演练。先不要执行，只给我：前置检查、边界、风险门、回滚、验证点。
```

### 5.5 迁移到别的例子

```text
接管 <OUTPUT_DIR>。先不要假设这是邮件网络。先根据当前运行时节点、服务和标签判断这是什么类型的网络，然后给我三种适合这个网络的 agent 任务。
```

这条很重要。它能让老师看到这不是给 `B29` 写死的。

### 5.6 A20 nano internet

```text
接管 examples/basic/A20_nano_internet/output。先不要假设这是邮件或安全场景。告诉我这个网络里有哪些 Internet Exchange、哪些 AS 是 transit、哪些 AS 是 stub、哪些节点承载了 web 服务。然后给我三个适合这个网络的 agent 任务，其中至少一个是只读诊断，一个是受控实验设计。
```

适合讲：

- 小型 Internet 结构识别
- transit / stub 关系
- web 服务与跨 AS 可达性
- 路由与应用联合观察

### 5.7 A21 shadow internet

```text
接管 examples/basic/A21_shadow_internet/output。识别这个网络里的 shadow stub、transit、real-world router、remote access 网络，告诉我哪些部分是纯仿真，哪些部分会和真实世界边界相连。只给只读结论，不做写操作。最后给我两个适合现场追问的后续任务。
```

适合讲：

- 仿真网络和真实世界边界
- real-world router
- remote access / VPN
- 安全边界与风险门

### 5.8 A03 real world

```text
接管 examples/basic/A03_real_world/output。先识别两个带 remote access 的 stub AS、承载 web 服务的节点、以及 real-world AS 11872 的角色。然后从 attached-runtime 视角告诉我：现在这个网络上有哪些事情适合只读做，哪些动作必须谨慎或不该现场做。
```

适合讲：

- 真实网络接口
- web 服务运维观察
- remote access 边界
- attached-runtime 的范围意识

### 5.9 D60 monero

```text
接管 examples/blockchain/D60_monero/output。先判断这是不是一个区块链网络，并识别 seed node、client、light wallet、pruned node、mining 节点分别落在哪些 AS。然后给我三个 agent 任务：一个同步/健康检查、一个受控实验设计、一个证据采集任务。
```

适合讲：

- 区块链节点角色识别
- 种子节点与客户端关系
- 轻钱包 / pruned node 差异
- 跨 AS 的服务健康与实验设计

但今天不要把它当强样板，因为实测里 Monero workload 没真正起来。

---

## 6. 当前最适合拿来讲的场景

### 6.1 B29

适合讲：

- 环境接管
- 邮件/DNS 诊断
- 跨域 reachability
- 日志与路由证据
- 受控实验设计

今天实测过的真实现象：

- agent 能拿到 `76` 节点运行态摘要
- 能跑任务式排查并落 artifact
- 实际证据里看到 `as202/dns-auth-gmail` 上 `named ...fail!`
- 实际证据里看到 `as200/router0` 和 `as202/router0` 的 BGP 状态不一致

### 6.2 B00

适合讲：

- 小型 Internet
- BGP 观察
- path / latency / prefix hijack
- 更干净的路由安全故事

但今天没有把它和 B29 同时 live 起，因为两者会冲突。

### 6.3 B28

适合讲：

- agent 不靠 output 文件，只靠运行时 inventory/process/connection 判断网络类型
- 谁是 traffic generator，谁是 receiver
- 先做只读诊断，再设计受控实验
- workspace 复用，不重复 attach

今天实测到的真实现象：

- `seed-codex run` 在 `b28_eval` 上两次都成功，第二次不传 `--attach-output-dir` 也能复用已 attach workspace
- runtime inventory 里能看到 `TrafficGenerator` / `TrafficReceiver`
- 运行时证据里能看到 generator 端存在 `ping ... multi-traffic-receiver`
- 运行时证据里能看到 receiver 端存在 `ITGRecv`、`iperf3 -s -D`，并监听 `9000` 和 `5201`

### 6.4 A02

适合讲：

- SEED 自身的 `Mpls` + `Docker` 编译链路
- attached-runtime 下的 FRR/MPLS 观测
- `routing_protocol_summary` / `routing_looking_glass` 的新控制面

今天实测到的真实现象：

- 例子能编译，`docker-compose up -d` 能起
- `r2/r3` 节点里同时存在 `bird` 和 `frr`
- `backend=frr` 时，`routing_protocol_summary` 会明确返回错误 `bgpd is not running`，这表示 FRR 在这些核心节点上没有 BGP 面，不该把它当成成功摘要
- `vtysh -c 'show running-config'` 和 `vtysh -c 'show mpls ldp discovery'` 有效
- `backend=auto` 现在会避开把 `bgpd is not running` 误判为成功，在 `r2/r3` 这类节点上回到 `bird`

### 6.5 Y01 和 D60

- `Y01_bgp_prefix_hijacking`
  - 今天不是完全不能起。
  - 修完地图镜像依赖后，部分关键节点能进入 `Up`。
  - 但整体启动时间长，`docker-compose up -d` 自身不够干脆，不适合临场押主秀。
- `D60_monero`
  - 网络和容器能起。
  - 但抽查关键节点时只有 `/start.sh` 和 `tail -f /dev/null`，没看到 `monerod` 一类实际 workload。
  - 所以它今天最多是“例子能起”，不是“复杂系统 agent 样板已闭环”。

---

## 7. `mission` 放在什么位置

`mission` 不是主交互方式。

把它理解成：

- 一个结构化任务入口
- 一个回归/留证据工具
- 一个“我要固定输入并复现一次”的辅助工具

适合用 `mission` 的情况：

- 你想固定任务和输入
- 你想要确认门
- 你想要结构化 artifact
- 你想做回归验证

不适合用 `mission` 的情况：

- 你想现场自由发挥
- 你想根据老师提问临时转话题
- 你想快速切场景

### 7.1 你现在可以直接跑的 B29 任务

```bash
./scripts/seed-codex mission list --baseline B29
```

今天实测跑通的是：

- `TS_B29_MAIL_REACHABILITY_DEBUG`

今天验证到的行为：

- 会先补齐输入
- 会先过确认门
- 会执行并下载 artifact
- 但执行规划仍可能走 `template_fallback`

所以它适合“辅助验证”和“落证据”，不适合做主秀。

---

## 8. 非交互验证怎么跑

这个是给你上台前自检，不是现场给老师看的。

### 8.1 看上下文链路是不是活的

```bash
./scripts/seed-codex status
./scripts/seed-codex context
```

### 8.2 只验证 attach 和环境感知

```bash
./scripts/seed-codex run \
  "接管 examples/internet/B29_email_dns/output，只做只读环境理解，给出运行环境、规模、关键节点与下一步可做的事情。" \
  --workspace-name pre_demo_probe \
  --attach-output-dir examples/internet/B29_email_dns/output \
  --policy read_only \
  --follow-job on \
  --download-artifacts off
```

注意：

- `run` 这条链今天验证过能 attach、能盘点、能出 summary
- 但它经常显示 `template_fallback`
- 所以它适合做“链路通不通”的自检，不适合拿来当主展示

### 8.3 不要把 `exec` 当主验证手段

今天额外测过一次：

- `./scripts/seed-codex exec ...`

结果是：

- Codex 会话能起来
- MCP resource 枚举能成功
- 但函数型 MCP 调用出现了连续 `user cancelled MCP tool call`

所以：

- `ui` 仍然是主交互入口
- `run` 仍然是最稳的非交互自检入口
- `exec` 今天不要拿来做主秀前的关键验证

---

## 9. 现场兜底顺序

如果现场开始不顺，按这个顺序退：

1. 先确认网络还在

```bash
docker ps --format '{{.Names}}\t{{.Status}}' | sort
```

2. 再确认 agent/ops 还在

```bash
./scripts/seed-codex status
```

3. 如果 UI 不稳，换成“只读固定 Prompt”

直接重新开：

```bash
./scripts/seed-codex ui -m gpt-5.4 -c 'model_reasoning_effort="low"'
```

然后喂 5.1 或 5.2 的 prompt。

4. 如果你需要结构化证据，改走 `mission`

```bash
./scripts/seed-codex mission list --baseline B29
```

---

## 10. 你后续自己批量玩的时候

推荐顺序：

1. 先确认这个例子有没有 `output/docker-compose.yml`
2. 单独起这个网络
3. 进 `ui`
4. 先用 5.1 跑环境理解
5. 再用 5.2/5.3/5.4 切成诊断/实验/安全故事
6. 真要留证据，再用 `mission`

不要一开始就上 `mission`。

不要一开始就上危险动作。

先看 agent 是否真的理解它处在什么网络里，这才是 attached-runtime 的核心价值。

### 10.1 今天这台机子的直接建议

如果你要稳：

1. 主秀继续用 `B29`
2. 扩展示意用 `B22/B23/B24/B25/B26/B28/Y01/Y03`
3. A / D 放在“我现在可以继续试”的第二梯队

如果你要试 A / D：

1. 先只起一个
2. 第一次 `up -d` 多等一会
3. 如果卡在外部拉包或拉镜像，不要死耗，先切回 B 类稳定池
4. UI 里先跑环境理解，不要直接上实验或危险动作

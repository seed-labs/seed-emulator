## 2026-10-06 - RIP 层、B51 示例与兼容性验证

- 用户需求：参考 `/home/lxl/papers/seed-arxiv2026/paper.pdf` 第三、四章，
  实现与 OSPF 并列的 RIP 协议层，提供论文所述分级配置能力，使 B00 只需
  替换 `emu.addLayer(Ospf())` 为 `emu.addLayer(RIP())`，并增加 B51 和 CI 验证。
- 执行范围：协议层、Intent、BIRD/FRR 渲染、iBGP 下一跳解析、组件合并、
  示例/文档/CI。按原始请求授权构建和启动 Docker 测试工作负载，结束后清理。
- 架构依据：协议层只生成软件无关 Intent；Routing 在所有协议层完成配置后
  生成原生配置；Base、编译器和执行阶段保持独立。

### 文件与实现

| 文件 | 改动 |
| --- | --- |
| `seedemu/layers/Rip.py` | 新增 RIP/Rip 层、四级设置、计时器、接口度量、被动接口、屏蔽和配置查询 API |
| `seedemu/layers/_rip_metadata.py` | RIP 参数校验、默认值及复制隔离的 Intent 存取 |
| `seedemu/layers/_igp_metadata.py` | 通用 IGP 身份及冲突检测 |
| `seedemu/layers/Routing.py` | BIRD/FRR RIP 渲染、FRR ripd 启动与后端能力校验 |
| `seedemu/layers/Ibgp.py` | 可选 IGP 依赖、按实际 IGP 选择解析表、禁用 RIP 节点的转发表回退 |
| `seedemu/layers/Ospf.py` | 声明通用 IGP 身份，保留既有 OSPF 行为 |
| `seedemu/layers/__init__.py` | 导出 Rip 和 RIP |
| `seedemu/mergers/DefaultRipMerger.py` | 合并 RIP 参数和屏蔽设置，拒绝冲突策略 |
| `seedemu/mergers/{__init__,DefaultMergers}.py` | 注册默认 RIP 合并器 |
| `examples/internet/B00_mini_internet/mini_internet.py` | 预导入 RIP；确保当前仓库在 Python 导入路径上优先 |
| `examples/internet/B00_mini_internet/README.md` | 说明单行替换与 B51 API 入口 |
| `examples/internet/B51_rip/{rip.py,example.yaml,test_runtime.py,README.md}` | 复用 B00 的分层组合；演示策略 API；混合后端 CI 和动态协议/路由/度量检查 |
| `examples/internet/README.md` | 添加 B51 入口 |
| `tests/test_rip_layer.py` | RIP、后端、组件合并/保存/加载、B00 替换与 CLI 路径回归测试 |
| `tests/test_frr_exabgp_foundation.py` | 修正原有 OSPF 测试的过时计时器断言，匹配原代码的 `dead 4` |
| `tests/ci/{feature_manifest.json,README.md}` | 注册 routing-rip 功能、单元测试组和 B51 编译/构建入口 |
| `.github/workflows/on-pull-request.yaml` | 添加 B51 选项、静态检查及编译/运行矩阵 |

RIP 不接收或发送 IX/跨 AS 接口上的更新；这些直连前缀仅用于 AS 内下一跳
解析。BIRD 的 t_rip 表只接收选定直连/RIP 路由并单向输出到 master4；FRR
通过精确前缀过滤重分发直连路由。两个后端均不重分发 BGP 到 RIP。

### 命令记录

以下命令均从 `/home/lxl/seed-emulator1211` 执行，除工具自身的只读文件检查。

| 命令/操作 | 目的及结果 |
| --- | --- |
| `rg --files`、`rg -n`、`cat`、`sed`、`git status --short` | 查找 AGENTS/技能、阅读 OSPF/BGP/Routing/merger/testing/CI；起始工作树干净 |
| `pdftotext -layout .../paper.pdf -` 及按页/原始文本读取 | 核对论文第三、四章的分层、Intent、参数层级及后端职责 |
| `docker info`、定向 `docker image ls/inspect`、`docker ps/events`、`free -h`、`df -h`、`/proc/loadavg` | 核对本机 Docker、镜像和测试资源，跟踪构建进度 |
| 官方 BIRD/FRR 文档及 FRR 8.4.4 `rip_cli.c` / RIP 接收代码查阅 | 核对原生语法、被动接口、接收侧度量和 FRR 计时器限制 |
| `python3 -m py_compile ...` | 检查所有修改的 Python 层、合并器、示例及测试文件 |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/unit.xml` | 验证新 RIP 功能及既有路由回归；详细结果见下方 |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/static` | 功能清单、空白、compileall、导入检查通过 |
| `create_runner(...)`、`yaml.safe_load(...)`、工作流矩阵断言 | B00/B51 清单合法；B51 在编译/运行矩阵各出现一次 |
| `docker compose -f examples/internet/B51_rip/output/docker-compose.yml config --quiet` | 生成的 Compose 配置通过检查 |
| `python3 seedemu/testing/cli.py compile examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/rip/b51-mixed` | 标准 CI 编译入口生成 Docker 输出 |
| TestRunner 的 `compile()`，分别用于 B00 原版、B00 单行替换、B51 bird/frr 副本 | 编译兼容性及后端变体；副本位于 ci-artifacts，B00 YAML/运行测试逐字相同 |
| `docker run --rm --network none --entrypoint sh -v <output>:/configs:ro handsonsecurity/seedemu-router:2.0 ... bird -p -c ...` | 实际 BIRD 2.17.2 原生配置检查 |
| `docker run --rm --network none --entrypoint sh -v <output>:/configs:ro output-brdnode_3_r105:latest ... vtysh -C -f ...` | 实际 FRR 8.4.4 原生配置检查 |
| `COMPOSE_PARALLEL_LIMIT=4 python3 ci-artifacts/rip/validateLifecycles.py` | 使用现有 TestRunner，依次执行 B51 mixed、B00 RIP 替换版、B00 OSPF 的 compile/build/up/probe/test/down |
| 同一脚本追加 `--reuse-b51-build` | 修正运行测试 JSON 解析后重启容器复测；对全部 B51 构建输入计算 SHA-256，核对与已成功构建的输入一致，复用 compile/build 结果；B00 两场景仍完整执行 |
| `docker run --rm --network none --entrypoint python3 -v <inputs>:/configs:ro output-brdnode_3_r105:latest -c <validator>` | 对最终 mixed/bird/frr 编译结果的 99 份配置执行 bird -p / vtysh -C；记录于 ci-artifacts/rip/native-syntax/summary.json |

### 调试与修复证据

- 首轮既有路由测试 28 通过、1 失败。`git show HEAD:seedemu/layers/Routing.py`
  证明仓库原代码使用 `dead {dead}`、默认 dead=4，而旧测试要求 dead count=2。
  已修正测试断言，未为此更改 OSPF 的计时器行为。
- 首轮 FRR 原生检查拒绝 `ip split-horizon poisoned-reverse` 和 update=2。
  核对 FRR 8.4.4 原生命令后，修正为 `ip rip split-horizon`，示例采用
  5/30/20 秒，FRR 渲染拒绝小于 5 秒和不同接口计时器的设置。修正后的原生检查通过。
- 一个此前缓存的 BIRD 镜像不含 vtysh（退出 127），随后使用本次生成的真实
  FRR 镜像完成检查。没有用缺少 FRR 的镜像判断产品兼容性。
- 直接执行 B51 时曾从 `/home/lxl/seed-emulator` 导入旧示例，导致 ImportError。
  已修正当前仓库的路径优先级，并添加故意注入其他 examples 命名空间的回归测试。
- 为避免继续构建已被语法修正替代的旧配置，终止了本任务首次构建的独立进程组
  （PID/PGID 3997986，退出 143），随后重新编译正确配置并用现有 Compose 并发选项构建。
  没有停止或修改原有 metacubexd 容器。
- 混合后端真实运行发现 FRR 8.4 的 non-passive-interface 创建回调执行 unset，
  导致“passive default + no passive interface”仍不发送更新。运行状态和源代码
  `/ripd/rip_nb_config.c` 均确认此问题；临时切换全局默认并重新应用接口状态后，
  BIRD 实际学到 FRR 环回路由，度量为 3，FRR 反向度量为 5。
  渲染已改为“no passive-interface default + 显式 passive-interface”。
  诊断运行被主动中断（PGID 4077608，退出 130），TestRunner 的 finally 完成
  down（退出 0）；后续从新镜像冷启动重新验证，不以临时修改后的状态报告成功。
- 第二次冷启动的 RIP 环回路由、BGP 会话正常，但跨 AS ICMP 在进入第一个
  路由器前消失。tcpdump 和宿主机 raw/PREROUTING 计数确认 Docker 29 的
  `-d <container-IP> ! -i <destination-bridge> -j DROP` 规则丢弃了这些帧。
  [Docker 官方文档](https://docs.docker.com/engine/network/firewall-iptables/)
  说明 raw 表先于 DOCKER-USER 过滤。该诊断运行退出 130，finally down 退出 0。
  原始日志保存在 `ci-artifacts/rip/b51-before-firewall-fixture/`。
- 最终本地验证在每次 up 之后读取该 Compose 项目带 SEED 前缀标签的网络，
  为其网桥添加临时 `sudo -n iptables -w 5 -t raw -I PREROUTING 1 -i <bridge>
  -d 10.0.0.0/8 -m physdev --physdev-is-in -m comment --comment
  seedemu-rip-ci-<case> -j ACCEPT`。只匹配本测试网桥的 L2 入站流量；finally
  用相同参数 `-D PREROUTING` 删除。每个场景的 `host-firewall-fixture.json`
  和 `host-firewall-restored.json` 保存完整参数及清理结果。没有清空防火墙、
  修改宿主机全局 sysctl、重启 Docker 或影响原有容器。
  对应独立 GitHub B00/B51 测试主机使用 `modprobe br_netfilter` 和
  `sysctl -w net.bridge.bridge-nf-call-iptables=0`；示例 README 说明前置条件。
- 补充层级优先级回归：默认 enabled=False 允许网络/接口选择性覆盖；显式
  router enabled=False 和 mask 仍强制禁用。运行测试另检查被 mask 的管理
  前缀未传播到远端 RIP 表。
- 冷启动后所有跨 AS ping 通过。运行检查发现 FRR 8.4 的
  `show bgp ipv4 unicast summary json` 使用顶层 peers，而测试只读取了
  ipv4Unicast.peers。已兼容两种格式，并测试 Established/Active 两种状态，
  避免放宽健康检查。终止仅此测试进程（退出 -2），TestRunner 返回 1 并
  finally down 退出 0；记录保存在 `b51-before-runtime-json-fix/`。
  此改动不改变守护进程配置；后续 SHA-256 校验后复用构建，重新冷启动验证。

### 最终验证

<!-- RIP_VALIDATION_START -->
最终全部通过，结果来自本机实际执行的现有 TestRunner 和原生路由软件。

- `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py
  --junitxml=ci-artifacts/rip/unit.xml`：78 通过，0 失败、0 错误、0 跳过
  （RIP 49 项，既有路由回归 29 项）。
- `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/static`：
  功能清单、空白、compileall、导入检查全部通过；B00/B51 清单和 B51 在
  两个 GitHub 工作流矩阵中的唯一条目也通过检查。
- 实际 BIRD 2.17.2 / FRR 8.4.4 解析 99 份最终配置，全部退出 0。
  mixed：27 BIRD、6 FRR；bird：33 BIRD；frr：6 BIRD 路由服务器、27 FRR。
  bird/frr 变体覆盖编译及原生解析；真实容器运行使用 mixed 和两种 B00。

| 场景 | compile | build | up | probe | test | down | 自定义运行检查 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B51 mixed | 0 | 0 | 0 | 0 | 0 | 0 | 72/72 通过 |
| B00 单行 RIP 替换 | 0 | 0 | 0 | 0 | 0 | 0 | 9/9 通过 |
| B00 原始 OSPF | 0 | 0 | 0 | 0 | 0 | 0 | 9/9 通过 |

每个场景的 readiness 及 3 组清单 ping 探测均通过。B51 检查全部 27 台
路由器的协议、AS 内远端环回路由和 BGP 会话；接收侧度量实测为 3 和 5；
管理前缀 10.2.250.0/24 未出现在远端 t_rip 表。B00 替换副本的 example.yaml
和 test_runtime.py 经字节比较与原版完全相同，mini_internet.py 经比较仅
替换 `emu.addLayer(Ospf())` 为 `emu.addLayer(RIP())`。

B51 的 compile/build 记录复用此前成功且全部构建输入 SHA-256 一致的结果；
只修正测试程序 JSON 解析，重新冷启动完成 up/probe/test/down。详细来源、
耗时和退出码保存在 `ci-artifacts/rip/lifecycle-summary.json`，没有将诊断中断
或临时修改过的容器作为成功证据。GitHub 工作流已经配置并本地检查；此处
记录的是本地运行结果。

清理核对：三个场景 down 全部退出 0，分别撤销 30、29、29 条临时规则；
raw/PREROUTING 中无 seedemu-rip-ci 规则，bridge-nf-call-iptables 仍为原值 1。
`docker ps` 仅剩原有 metacubexd（Up 4 days）。生成输出、镜像缓存和验证证据
保留供复查；`git diff --check` 通过。新增文件均为 RIP 实现、示例、文档或测试，
没有遗留跟踪的临时脚本。

证据入口：`ci-artifacts/rip/unit.xml`、`static/ci-summary.json`、
`native-syntax/summary.json`、`lifecycle-summary.json`，以及各场景目录下的
readiness-summary.json、probe-summary.json、test-summary.json、
b51-runtime-test.json / b00-runtime-test.json、host-firewall-restored.json。
<!-- RIP_VALIDATION_END -->

## 2026-10-07 10:56 - 独立 B51 拓扑与完整变更文档

- 用户意图：逐文件解释 RIP 实现的增删及作用，写入
  `add_rip.md`；将 B51 改为直接复制 B00 拓扑，替换 OSPF
  并添加 RIP API 示意代码。
- 范围：修改 `examples/internet/B51_rip/rip.py` 和对应 README，新增
  `add_rip.md`，追加本日志。生成编译输出和验证证据，
  未启动容器、构建镜像或修改宿主机网络。
- 改动：B51 直接包含 B00 的 IX、AS、主机和 eBGP 关系；删除从 B00 导入
  builder 后搬运层的实现。保留后端选择及已有 CI builder 入口，添加 RIP
  策略后调用 `emu.addLayer(rip)`。采用 B00 的 CLI/run/main 结构。README
  同步说明独立脚本。完整文档覆盖全部 24 个变更文件、API、后端与测试证据。

| 命令 / 操作 | 目的及结果 |
| --- | --- |
| `git status --short`、`git diff --numstat`、逐文件 diff / `rg` / `sed` / `cat` | 核对 13 个已有文件修改、10 个工程文件新增及文档位置 |
| `pdftotext -layout /home/lxl/papers/seed-arxiv2026/paper.pdf /tmp/seedemu-rip-paper-doc.txt` | 复核论文第三、四章与 Listing 1 的分级配置设计 |
| Python 读取旧 `unit.xml`、原生语法和生命周期 JSON | 核对此前 78 项测试、99 份原生配置及三场景运行证据，保留原日期 |
| 修改前对 `rip.py --backend bird/frr/mixed --output ci-artifacts/rip/b51-standalone/before-<backend>` 分别编译 | 保存三种后端的基准部署输入；全部退出 0 |
| `python3 -m py_compile examples/internet/B51_rip/rip.py` | 新独立脚本语法通过 |
| `yaml.safe_load(...)`、`create_runner(B51 manifest)` | 清单合法且成功构造 InternetTestRunner |
| `python3 seedemu/testing/cli.py compile examples/internet/B51_rip/example.yaml --artifact-dir ci-artifacts/rip/b51-standalone/manifest-compile` | mixed 通过标准清单编译入口 |
| 修改后对 `rip.py --backend bird/frr --output ci-artifacts/rip/b51-standalone/after-<backend>` 分别编译 | 另外两种后端编译通过 |
| Python SHA-256 文件清单比较和 Compose YAML 结构比较 | 三种后端的节点配置、启动脚本及 Dockerfile 全部逐字节相同，Compose 语义一致 |
| `diff -u` 比较新旧 Compose 和 B00/B51 脚本 | 确认 Compose 差异仅为两个 dummy 服务块的次序；拓扑代码直接来自 B00 |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/b51-standalone/unit.xml` | 78 通过，0 失败/错误/跳过，约 10.76 秒 |
| `docker compose -f examples/internet/B51_rip/output/docker-compose.yml config --quiet` | 最终 mixed Compose 配置通过；不启动服务 |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/b51-standalone/static` | manifest、whitespace、compileall、import-smoke 全部通过 |
| 文档本地链接、Git 变更清单和 API 检查 | 24 个文件均有说明，37 个本地链接有效，19 个公开 API 均覆盖；Markdown 代码块及空白检查通过 |
| `git diff --check` | 已跟踪文件的空白检查通过 |

初次严格文本比较因 bird/mixed 的 Compose 服务字典排列不同返回断言失败；
检查 diff 后确认仅有 dummy 服务块排序，改为 YAML 结构比较。节点文件仍
逐字节比较，没有忽略节点配置变化。最终 bird/frr/mixed 文件数分别为
385/412/391，均没有新增、缺失或变化的节点内容。

证据位于 `ci-artifacts/rip/b51-standalone/`：`unit.xml`、
`output-comparison.json`、`document-check.json`、`static/ci-summary.json`
及各编译日志。生成的部署输入等价，因此此次没有重跑 build/up/probe/test/down；
2026-10-06 的实际容器验证仍按其原日期记录，没有声称远端 GitHub CI 或
本次容器运行已经执行。

## 2026-10-07 - 全主机与 AS2 路由器连通性排查

- 用户意图：复现启动后 ping 失败，检查任意主机间及 AS2 边界路由器的
  连通性；若为 RIP 实现问题直接修复，否则报告实际原因。
- 范围：两轮本机 B51 mixed 实际容器运行、协议/FIB 检查、全主机矩阵、
  路由器地址和源地址对照、抓包及宿主机过滤/NAT 排查。更新 B51 README、
  `add_rip.md` 第 12 节和本日志，没有修改协议层代码。
- 初始状态：本机没有运行中的 B51，仅原有 metacubexd；Docker 29.0.0，
  `bridge-nf-call-iptables=1`。实际演示网络仍使用当前独立 B51 脚本的输出。

| 命令 / 操作 | 目的及结果 |
| --- | --- |
| `docker ps`、`docker compose ... ps`、`git status`、示例及测试框架读取 | 确认本机未运行用户所述网络，读取实际拓扑、探测范围及清单 |
| `sudo -n iptables -t raw -S/-nvL PREROUTING`、NAT POSTROUTING 检查 | 发现 Docker 直接路由 DROP 和 MASQUERADE 规则，记录包计数 |
| `/proc/loadavg`、桥接 sysctl、内存和磁盘读取 | 运行前及每次协议/FIB 验证前检查资源；等待 load1 < 50 |
| `COMPOSE_PARALLEL_LIMIT=4 python3 seedemu/testing/cli.py build .../B51_rip/example.yaml --artifact-dir ci-artifacts/rip/connectivity-20261007` | 构建返回 1 / unexpected EOF，原因见下方 Docker 崩溃记录；未报告成功 |
| `docker buildx history ls --filter status=running --format json` | 原本用于只读检查构建进度，但触发本机 BuildKit history 空指针崩溃；立即停止使用该接口 |
| `sudo -n journalctl -u docker ...`、`systemctl show docker ...` | 确认退出码 2、systemd 自动重启和 NRestarts=1；保存 docker-crash.log |
| `python3 .../connectivity-20261007/diagnose.py` | 使用现有 TestRunner 执行第一轮 up/test/probe/down、raw 对照及全矩阵，脚本退出 0 |
| 58 个节点的 `/start.sh`、`/interface_setup` 及 BIRD/FRR 配置 SHA-256 比较 | 149 份实际容器文件与当前生成输入一致；确认镜像运行配置正确，未以构建返回码代替配置核对 |
| 固定首节点 `birdc show protocols`、`birdc show route count` | 每轮 10 个不同 AS 的 BIRD 样本全部通过 |
| 16 个 BIRD AS 的 `ip route`、`ip -j -4 route show table all`、选定 RIB 前缀比较 | 计数门槛及实际前缀覆盖全部通过，没有 Linux FIB 缺失；FRR 由标准运行检查覆盖 |
| 临时 raw ACCEPT，限定本轮 30 个网桥及 10/8 L2 入站；撤销后重复 ping | 跨 AS 主机及 AS2 非直连接口由失败变成功，撤销后再次失败；对应 DROP 规则各增加 3 个包 |
| `python3 .../connectivity-20261007/phase2.py` | 第二轮临时排除 raw DROP 和 NAT，执行抓包及最终矩阵，脚本退出 0 |
| `timeout 8 tcpdump -l -nn -i any 'icmp and host 10.160.0.71'`，四台路由器同时观察 | raw-only 时源地址逐跳变成 10.100.0.1 / 10.3.0.1 / 10.103.0.1；排除 NAT 后全过程保持 10.2.0.254 并收到正常回包 |
| 临时 nat/POSTROUTING ACCEPT：`-o <own-bridge> -d 10.0.0.0/8 -m physdev --physdev-is-bridged` | 只为本轮仿真的 L2 流量跳过 Docker MASQUERADE，不修改其他网络或全局 sysctl |
| `ip route get`、默认 ping 与 `ping -I 10.2.0.254 10.160.0.71` 对照 | 证实普通 ping 自动用 IX 地址且 AS160 没有回程；内部源地址已公告，正确环境下可达 |
| 两轮 finally：逐条删除临时规则并 `down --remove-orphans` | 两轮 down 均为 0；最终第二轮删除 30 条 raw、30 条 NAT，桥接 sysctl 仍为 1 |

最终没有发现 RIP 缺陷：排除宿主机桥接过滤和 NAT 后，25 台主机互相
ping 的 600 个有向目标全部通过；AS2 四台路由器用公告过的内部 IP 为源，
访问所有 AS 路由器内部接口 130/130，通过所有主机 100/100。默认源地址
访问内部接口为 119/130，失败的 11 项是 IX 源地址缺少回程路由。跨 AS
环回和不参与的 IX 前缀也未由既有 BGP 策略公告，不能预期其全网可达。

第一轮 raw-only 的主机矩阵虽然是 600/600，但指定内部源地址访问路由器
仅 87/130，抓包证明宿主机仍在改写仿真流量。第二轮同时排除 NAT 后才
报告源地址保留及 130/130，因此没有将第一轮结果当作正确数据路径的完整证据。
第二轮开始及结束时标准 RIP/BGP 运行检查均通过，最终 load1=32.11。

额外故障：11:17 的构建历史查询触发 Docker/BuildKit 崩溃，systemd
自动重启 Docker，原有 metacubexd 也随之重启；本任务未执行 Docker
服务重启命令，但这次诊断 API 调用确实产生了上述副作用，已向用户说明。
不再访问该接口后，两轮实际网络运行完成并清理。未对 Docker 配置、版本
或用户已有容器做永久修复。

证据：`ci-artifacts/rip/connectivity-20261007/diagnosis-summary.json`、
`live-config-comparison.json`、`docker-crash.log`、`logs/build.log`，以及
`second-pass/diagnosis-summary.json` 中的抓包、矩阵、RIB/FIB 和清理记录。
此前 2026-10-06 仅验证三组 ping 且使用 raw fixture，没有证明任意路由器
地址可达或源地址未被 NAT；本次补齐这些验证。静态/单元测试未重复运行，
因本轮没有修改协议、示例脚本或测试代码。

完成核对：最终 raw 与 NAT 规则中均无 `seedemu-rip-ci-` 临时项，
`docker ps` 只剩原有 metacubexd（随上述 Docker 崩溃重启后 Up 20 minutes）。
`git diff --check` 通过，文档 24 个变更文件及 41 个本地链接均有效，
Markdown 代码块及行末空白检查通过。汇总为
`connectivity-20261007/document-check.json`，最终宿主机规则快照为
`raw-final.txt` 与 `nat-final.txt`。

## 2026-10-07 22:14 - 用户运行中的 AS163/router0 只读排查

- 用户反馈：进入 `as163brd-router0-10.163.0.254` 后不能 ping 其他路由器。
- `docker ps/inspect` 确认当前为用户启动的 B51 output 项目；没有执行
  build/up/down、重启 Docker、修改宿主机 sysctl 或添加过滤规则。
- `birdc show protocols`：AS163 RIP up、到 AS4 的 BGP Established；
  AS2/r100 的 RIP/BGP 同样正常。读取时 load1 为 24.19，低于 50。
- AS163 `ping -c 2 -W 1 10.104.0.4` 收到 2 个回复；普通 ping 与指定
  `-I 10.163.0.254` 到 `10.2.0.254` 各发 2 包，均无回复。
- `ip route get 10.2.0.254` 指向 AS4 `10.104.0.4`，默认源为
  `10.104.0.163`。AS2 对此 IX 源地址无回程，但有到 AS163 内部地址
  `10.163.0.254` 的 BGP 路由。AS163 对 AS2 的 IX 地址 `10.100.0.2`
  与环回 `10.0.0.1` 均返回 Network is unreachable。
- `sysctl net.bridge.bridge-nf-call-iptables` 仍为 1；
  `sudo -n iptables -t raw -L PREROUTING -n -v -x` 与
  `sudo -n iptables-save -c -t raw` 显示目标 `10.2.0.254` 的
  DROP 计数在本轮 4 个请求期间从 4 增加到 8。
- 将这组实际证据、宿主机环境准备及 AS163 源地址示例补入
  `add_rip.md` 第 12.7 节；协议与示例代码未修改。

## 2026-10-07 - B00 以前成功与当前桥接设置的区别

- 用户追问：以前自己手动运行 B00 可以正常 ping，为何现在要求修改
  `bridge-nf-call-iptables`。已收到“自己手动运行”的澄清；成功运行的
  时间、当时环境及具体 ping 源/目标尚未提供。
- YAML 结构对比：B00 的 29 个网络声明与 B51 的共有网络完全相同，
  AS163 的两接口地址相同；B51 仅额外增加 AS2 management 网络。
  `git diff -- seedemu/compiler/Docker.py` 为空；读取另一份已知仓库的
  Docker 模板也只显式设置 MTU。没有启动重叠地址的第二套网络。
- `docker version` 当前为 29.0.0；读取保留的 dpkg 日志显示
  2025-11-10 安装 28.5.2、2025-11-13 升级至 29.0.0。只读取
  daemon.json 的网络配置键，没有发现显式覆盖。这些记录不能证明
  用户过去那次成功是由版本差异造成。
- B00/OSPF 测试的 `host-firewall-fixture.json` 包含 29 条 raw 放行
  规则，`host-firewall-restored.json` 记录撤销 29 条。这是我执行的
  本地测试记录，不能替代用户手动运行时的环境记录。
- `git show HEAD:.github/workflows/on-pull-request.yaml` 与工作区
  diff 证实桥接 sysctl 步骤是本次工程工作新增，修正 add_rip.md 中
  “原来已有 CI 设置”的不准确表述，补充第 12.8 节解释开关与规则的
  关系及已知/未知信息。未改变协议源码、当前网络或宿主机设置。
- 查阅 Linux 内核 Bridge/Netfilter 与 Docker 28 官方发行说明，
  核对桥接流量进入 IP netfilter 钩子和 raw 防护变化。
- 验证：Python/YAML 比较断言通过，证据保存为
  `ci-artifacts/rip/b00-b51-network-compare-20261007.json`；Markdown
  代码块、行末空白、本地链接及 `git diff --check` 均通过。


## 2026-10-07 - 原始 B00 实际对照及 compile/build/up 用户流程修复

- 用户意图：实际运行 B00 判断当前是否同样失败；最终用户只进行 compile、build、up，所有 host 和 AS 边界路由器应能用普通 ping 互通，不能只靠 CI 特例通过。
- 授权范围：延续用户明确的运行验证和直接修复要求。B00/B51 的网络地址及容器名重叠，已告知需要临时切换；保存原 B51，最终留下修正后的 B51。没有再次请求确认。
- 适用技能：constructExample 的标准清单/runner 和只读运行验证；seedemu-bird-fib-verify 的 load1 < 50、固定 AS 协议/FIB 检查；codex-task-confirmation-worklog 的命令日志。已有运行和修复授权按会话及 developer 指令优先执行。

原始 B00 对照：

| 命令 / 操作 | 目的及结果 |
| --- | --- |
| 保存 B51 Compose、61 个服务的 image ID 和运行状态、其他容器 ID/StartedAt | 为暂时切换网络保留恢复依据，未输出敏感环境字段 |
| `python3 ci-artifacts/rip/b00-current-env-20261007/prepare.py` | 原始 B00 compile/build 返回 0；构建约 584.58 秒，使用其标准测试 runner |
| `python3 ci-artifacts/rip/b00-current-env-20261007/run.py` | B51 down → 原始 OSPF B00 up → 实测/对照 → B00 down → 原 B51 恢复；脚本退出 0 |
| load 门槛、27 个 OSPF/BGP router、10 个固定 Bird AS、17 个 Bird AS FIB | 全部正常；所选 RIB 前缀没有 FIB 缺失 |
| 52 个源节点到彼此主地址的普通 ping | 全局桥接开关 1、无排除时 93/2652；host 互 ping 仅 28/600，都是同 AS 路径 |
| 临时 29 raw + 29 NAT 排除，只限这轮测试的网桥 | host 普通 ping 1275/1275；路由器内部源地址 1377/1377；路由器默认源地址 752/1377 |
| 删除临时规则后再次执行代表 ping | 再次失败，确认 DROP/NAT 干扰；普通 router 的 IX 源地址另缺少全网回程 |
| 原 B51 恢复及标准运行检查 | 原 61 服务/原镜像恢复；72 项运行检查、协议/FIB 门槛通过；其他容器没有重启，桥接开关 1 |

产品修改：

- B00 和 B51 两个脚本使用既有 `Docker(selfManagedNetwork=True, dummyNetworksPool="10.128.0.0/16")`，把 Docker transport 地址与真实仿真地址分开。两例 IX LAN 使用 `setDirect(True)`，让独立 BGP connected-prefix 导出包含 IX，补齐普通 ping 的去程/回程。
- 删除本次工程工作此前加入工作流的 8 行 B00/B51 `modprobe`/`sysctl` 例外步骤。当前部署不依赖全局桥接开关改变或临时防火墙规则。
- `tests/test_rip_layer.py` 增加 5 个编译场景（B00 OSPF/RIP、B51 bird/frr/mixed），验证地址不重叠、实际接口映射、启动顺序及 IX BGP 导出；更新用户说明和完整文档。
- 首轮修正部署的 B00/OSPF 4386/4386 普通 ping 和四跳源地址保留均通过，但 Compose down 返回 0 后残留 23 网络/33 端点；B00/RIP up 报 Pool overlaps。Docker 日志说明地址替换后缺少 transport 网关链路路由，因此未把首轮认定为完整通过。
- `seedemu/compiler/Docker.py` 给内部地址映射增加 gateway 第三列，地址脚本添加该 gateway `/32` 的 scope-link 路由。第二轮实际 down 检查仍残留 23 网络，查明 `/interface_setup` 为重命名先关闭接口，会移除先前链路路由；于是改成精确匹配 dummy/real 地址的幂等脚本，并在接口配置之后再次调用恢复路由。此修正适用于通用 self-managed 模式，不涉及 RIP 后端语法或普通编译模式。
- 仅对首轮已移除容器的 `user-b00-ospf` 项目 force-disconnect 孤立端点并删除其网络，未清理其他项目、修改全局规则或重启 Docker。此清理仅恢复诊断环境，不作为产品操作步骤。

| 命令 / 操作 | 目的及结果 |
| --- | --- |
| `git status --short`、逐文件 diff、`rg`/`sed`、读取 runner 与两个 manifest/test_runtime | 核对用户实际路径、已有部署能力及测试范围 |
| `sudo -n iptables-save -c -t raw/nat`、`/proc/loadavg`、桥接 sysctl、Docker inspect | 验证开关始终 1、没有临时项，以及其他容器未重启 |
| 普通 Docker 原生 BuildKit build | 首轮三套部署均成功；加入网关修复后再次三套 compile/build 全部 0，构建约 46.24/16.25/17.66 秒；没有访问 buildx history API |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/user-workflow-20261007/unit-tests.xml` | 最终 83 项通过、18.43 秒。新增测试曾误读 build 字段，之后网关校验又遇到生成映射的首行空行；分别修正结构读取及跳过空行，地址/网关断言未放宽 |
| `python3 ci-artifacts/rip/user-workflow-20261007/prepare.py` | 每场景实际 Python compile + 普通 Compose build，保存每步命令、退出码、用时和完整日志 |
| `python3 ci-artifacts/rip/user-workflow-20261007/run.py` | 普通 Compose up、现有 manifest 的 readiness/probe/test、全实际接口普通 ping、四跳抓包及普通 down/up 验收；最终默认目录 B51 执行 compile/build/up 并保留运行 |

证据分为 `ci-artifacts/rip/b00-current-env-20261007/` 的修复前真实对照，以及 `ci-artifacts/rip/user-workflow-20261007/` 的用户流程验收。`first-attempt-summary.json`、`first-attempt-down.log`、`first-attempt-b00-rip-up.log` 保存首轮失败，`ghost-endpoint-cleanup.json` 记录限定清理；最新汇总没有把该失败掩盖为成功。

第二轮失败保存于 `second-attempt-acceptance-summary.json` 和 `second-attempt-b00-ospf-down.log`。限定清理时因恢复的旧 B51 已占用同名容器，第一次 force-disconnect 按名称返回 not connected，未产生改动；先普通 down 旧 B51 再限定清理测试残留，记录在 `second-ghost-endpoint-cleanup.json`。验收脚本增加每个节点真实地址和 transport 网关 `/32` 实际路由检查，以及普通 down 后项目网络必须为零的断言。


第三轮修复后的 B00/OSPF：普通 up、readiness/probe/test 全部 0；52 源节点到 86 个实际接口的 4386 个普通 ping 全通过，host 互 ping 600/600；58 节点真实地址和 transport 网关链路路由全部通过；四跳 ICMP 请求及回包保留默认 IX 源 `10.100.0.2`；普通 down 返回 0 且残留项目网络为零。随后 B00/RIP 的普通 up 成功，不再发生 Pool overlaps。

网关顺序最终修复后回归测试为 83 passed / 18.25s。读取实际路由时一次临时只读 shell 管道的引号错误返回 2，改成直接 Compose exec `ip -4 route show scope link` 后成功确认网关 `/32`，没有因此改变容器或宿主机配置。


B00/RIP 收敛检查中，验收辅助脚本误用“至少 6 列”解析 BIRD 输出，而 RIP/Device/Direct/Kernel 的空 Info 行只有 5 列；实际 RIP 为 up、BGP 全 Established，却被脚本认为没有 RIP。纠正辅助脚本为至少 5 列，未修改产品协议代码；主动 SIGINT 只中断验收控制器，使 finally 正常 down 并恢复旧 B51。B00/RIP 普通 down 无残留网络。中断证据保留在 `rip-parser-interruption-summary.json` 和 `rip-before-parser-fix.json`；随后用 `SEEDEMU_ACCEPTANCE_RESUME_FROM_RIP=1 python3 .../run.py` 继续，不重复已通过且部署输入未变化的 OSPF 场景。最新协议样本也按 5 列正确验证 RIP/Direct/Kernel/Device 状态。


## 2026-10-08 - 正常用户流程最终全量结果

- B00 OSPF：4386/4386 全接口普通 ping，600/600 host 互通，2652/2652 主地址节点方向；原清单 9/9。
- B00 仅添加层一行 Ospf→RIP：同样 4386/4386、600/600、2652/2652；原清单 9/9，正常 down 后零网络残留。
- B51 默认 mixed：默认目录普通 `python3 rip.py`、`docker compose build`、`docker compose up -d` 全部 0；4488/4488（包含管理接口），600/600、2652/2652；原清单 72/72。
- 每场景 58 节点的地址及网关链路路由全部正确；固定 10 BIRD AS 协议门槛通过；B00 17 / B51 16 BIRD AS FIB 计数和实际选定 RIB 前缀覆盖全通过，load1 < 50；FRR 由原清单真实运行检查覆盖。
- 每场景四跳 tcpdump 均记录普通 AS2 ping 的默认 IX 源 `10.100.0.2` 保持不变，并收到正常回包；AS163 普通 ping 到 AS2 内部和 IX 地址均通过。
- 开关保持 1，raw/NAT 中没有临时 `seedemu-rip-ci-` 项，metacubexd 的 ID/StartedAt 始终与本轮快照一致。
- `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/user-workflow-20261007/static`：manifest、whitespace、compileall、import-smoke 全 passed。生成结果和 full matrix 保存于 acceptance-summary.json 与三个场景的 diagnosis-summary.json。
- 为检查 FRR 混合节点的实际关闭清理，最后运行 `python3 .../user-workflow-20261007/restart.py`，普通 down/up 后保留 B51；启动后按技能再次验证协议/FIB、58 节点地址/网关、原清单和 AS163 代表路径，不重复已经通过的全矩阵。

最终混合后端普通 down/up 验收通过：down/up/readiness/probe/test 均为 0；项目网络残留为零；重启后 72 项运行检查、10 AS BIRD 协议样本、16 BIRD AS FIB/实际前缀覆盖、58 节点地址及网关路由全部通过，AS163 内部/IX 普通 ping 和 AS2/host 代表路径通过。最终 load1=13.63、桥接开关 1、临时项 0，其他容器 ID/StartedAt 不变。B51 留在默认 output 目录运行，61 服务中 59 运行、两个 image-build dummy 正常退出 0；最终状态保存为 final-services.json。

最终文档覆盖全部 25 个变更文件，Markdown 代码块、空白及本地链接校验通过；`git diff --check`、默认 B51 `docker compose ... config --quiet` 通过。已按用户要求完成真实 compile/build/up 和普通 ping 的验收，不再要求用户设置桥接 sysctl、添加过滤规则或指定源地址；未执行 git commit 或远端 GitHub CI。

## 2026-10-08 17:38 - 持久化服务器 IPv4 桥接开关为 0

- 用户意图：用户已手动将 `net.bridge.bridge-nf-call-iptables` 改成 0，明确要求服务器以后默认采用 0。按这项授权直接执行配置。
- 范围：服务器的两个新增配置文件，以及本工作日志和 `add_rip.md` 的环境记录。
- 修改：新增 `/etc/sysctl.d/99-zz-seedemu-bridge.conf`，写入 `net.bridge.bridge-nf-call-iptables = 0`；新增 `/etc/modules-load.d/seedemu-br-netfilter.conf`，启动时加载 `br_netfilter`，确保模块初始化先于 sysctl 应用。两个文件均为 root:root、0644；写入前确认不存在，使用排他创建，未覆盖已有配置。
- 读取命令：`sysctl net.bridge.bridge-nf-call-iptables` 确认当前已为 0；`sudo -n true` 确认已有管理权限；`rg` 核对 sysctl、模块加载和系统配置，没有重复设置；`systemctl show` 确认 `systemd-sysctl.service` 排在 `systemd-modules-load.service` 之后。检查工作目录及配置目录的适用 `AGENTS.md`，没有找到额外要求。对用户目录的文件搜索遇到部分实验目录权限不足，随后改为核对当前任务目录。
- 执行命令：通过 `sudo -n python3` 创建上述文件；`sudo -n sysctl -p /etc/sysctl.d/99-zz-seedemu-bridge.conf` 应用这一项；`sudo -n /usr/lib/systemd/systemd-sysctl --prefix=/net/bridge/bridge-nf-call-iptables` 验证系统启动采用的配置处理程序，限定到这一项，退出 0。
- 验证命令：`systemd-sysctl --cat-config --no-pager` 确认此键唯一有效定义来自新增文件，值为 0；`modinfo -n br_netfilter` 确认当前内核具有可加载模块；检查 `/sys/module/br_netfilter`、文件内容/所有权/权限、实际 `/proc/sys/net/bridge` 值，全部通过。IPv4 值保持 0，IPv6 和 ARP 值仍为 1。
- 证据：`ci-artifacts/rip/host-bridge-default-20261008/verification.json` 保存命令、退出码、应用前后值、配置内容及启动顺序检查。
- 边界：没有重启服务器、Docker 或当前实验容器，没有在本次运行新的连通性实验。此前开关为 1 的矩阵测试仍属于此前部署的历史结果，本次验证的是持久化配置。
- 文档验证：一次文档补丁含空 hunk，工具在写入前拒绝；修正后成功追加。`git diff --check` 及两个更新 Markdown 文件的行尾空白检查通过。

## 2026-10-08 18:43 - B51 按 AS 组合 OSPF/RIP 与三后端真实运行验证

- 用户意图：B51 同时包含 OSPF、RIP，示例可以不用 mask 函数，并且真实 compile/build/up 后网络能够正常运行。沿用用户已明确的运行及修复授权，没有重新要求批准。
- 实现选择：先通过可选异步问题说明按 AS 分配或同路由器并用两种选择；没有收到回复，等待超过 60 秒后按已说明的推荐方案执行。AS3/4/12 使用 OSPF（9 台），其他 AS 使用 RIP（18 台），AS 间保持 BGP。
- 适用技能：constructExample 的标准清单及只读测试；seedemu-bird-fib-verify 的 load1 < 50、固定 AS 协议及实际 RIB/FIB 覆盖；codex-task-confirmation-worklog 的命令与结果记录。已有用户授权及 developer 指令优先于重复确认流程。
- 代码文件：`_igp_metadata.py` 统一校验正向范围及协议标签；`Ospf.py`/`Rip.py` 增加 `asns`、setter/getter、未知 AS 检查、旧 dump 兼容；两个默认 IGP merger 保留作用范围；B51 `rip.py` 增加 OSPF 和正向范围，删除 management 网络、两个接口和 mask 调用；`test_runtime.py` 按声明检查两种 IGP、包括 FRR stub 的 BGP，并新增全部实际接口普通 ping；manifest、feature manifest 与回归测试同步。
- 文档文件：更新 B51 README、本文、`add_rip.md` 和 `tests/ci/README.md`。完整文档的当前清单改为 23 文件（12 已有修改、11 新增），明确当前 B00 与 HEAD 一致、需先添加 RIP 导入，早期 B00/纯 RIP 验收属于历史。
- 本轮没有修改 B00、Docker 编译器、Routing 或 Ibgp 的源码；保留本轮开始前已有 self-managed 启停修复。服务器的持久化桥接值 0 全程未改变。

| 命令 / 操作 | 目的与实际结果 |
| --- | --- |
| `rg`、`sed`、`git status`、逐文件 diff、读取适用技能与实际元数据 | 核对当前 B00/B51、层依赖、merger、部署和既有运行状态 |
| 定向运行原有 scope/B00/B51 测试基线 | 3 failed、3 passed、48 deselected；失败都是旧断言假设 B00 已导入 RIP/使用 self-managed，保留 baseline-tests.log |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/ospf-rip-coexist-20261008/unit-tests.xml` | 调整当前 B00 预期，增加 scope/merger/新旧 dump/双 IGP/FRR JSON 回归；先 103 项通过，补旧 dump 兼容后最终 105 passed / 17.96s |
| `python3 -m py_compile`，针对修改的 topology/runtime 和验收辅助脚本 | 语法验证通过 |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/ospf-rip-coexist-20261008/static` | manifest、whitespace、compileall、import-smoke 全 passed |
| `python3 ci-artifacts/rip/ospf-rip-coexist-20261008/prepare.py` | 保存此前 B51 输出及 61 服务的镜像 ID/状态，在原网络继续运行时完成三种后端真实 compile/build/config；全部退出 0 |
| `python3 ci-artifacts/rip/ospf-rip-coexist-20261008/validate.py` | 普通 down 原 B51 → BIRD up/验收/down → FRR up/验收/down → 默认 mixed up/验收并保留；所有运行命令退出 0 |
| 原生默认用户命令 `python3 examples/internet/B51_rip/rip.py`、`docker compose -f examples/internet/B51_rip/output/docker-compose.yml build` 和 `up -d` | mixed 使用默认脚本/默认输出目录；普通 compile/build/up 成功，与用户路径一致 |
| 原清单 readiness/probe/test 与动态普通 ping | BIRD 118/118、FRR 145/145、mixed 124/124；每种 4386/4386 普通方向、600/600 host 互通；源为全部 25 host 和 27 AS 路由器，目标为其他节点全部实际接口，不使用 ping -I |
| 读取实际地址、网关路由、协议和 FIB | 每种 58 节点地址/网关通过；BIRD 固定 10 AS 协议和 17 AS FIB，mixed 固定 10 AS 协议和 16 AS FIB/选定前缀覆盖全部通过；FRR 无 BIRD AS 样本，专用检查明确不适用，由 FRR 原生协议/BGP/学习路由及完整 ping 验证 |
| load1 门槛 | 三种后端启动后分别等待 70/80/70 秒，所有规定检查在 load1 < 50 时执行；最终 mixed load1=34.75 |
| 普通 Compose down 后按项目查询 networks | 原 B51、BIRD、FRR 残留均为空，下一场景 up 无地址池冲突；没有执行残留端点清理 |
| 最后独立读取 Docker 服务、配置路径、IGP/软件标签及 sysctl | 默认 mixed 的 61 服务中 59 运行、2 个 build-only dummy 正常退出 0；OSPF9/RIP18，BIRD21/FRR6；配置路径为实际 B51 默认 output；桥接值为 0 |

准备辅助脚本的前两次执行在只读 Docker 快照阶段停止：Docker `ps -a` 列出了一个无法 inspect 的 Dead 对象。该对象属于无关的 `seedemu-router/test`，无名称；B51 和所有运行容器均可检查。重试后仍存在，于是仅改辅助快照脚本，解析部分成功的 inspect JSON，并只跳过已明确无关的 Dead 对象，同时对任何丢失的运行/B51 容器保持错误。没有删除该对象、prune、重启 Docker 或停止其他项目。两次失败保存为 first-preparation-summary.json、second-preparation-summary.json，最终 preparation-summary.json 成功。正式运行三个场景均通过，无协议或 ping 失败。

验收辅助脚本在执行前纠正 runtime JSON 的 failures-list 读取方式；文档阶段一次只读汇总脚本误把 cases 字典当作列表，改为 items 后正常读出全部结果。两者均未修改网络状态或产品运行配置。两次 rg 查询的历史日志名不存在，实际证据以对应 JSON 中保存的路径及原日志为准。

最终证据目录：`ci-artifacts/rip/ospf-rip-coexist-20261008/`。acceptance-summary.json 的 success=true、三种 cases.success=true、default_mixed_network_left_running=true；各后端保留 diagnosis-summary.json、原生配置/命令日志、runtime JSON、协议/FIB 原始记录。当前 B51 未加入 management 网络，因此本轮方向数为 4386，早期纯 RIP 含该网络的 4488 记录保留为历史。全局环回公告和 IX route server 不属于全实际接口 ping 矩阵。

没有设置新的 sysctl、防火墙例外、静态补救路由或指定 ping 源地址；没有执行 ARM 容器运行、远端 GitHub Actions 或 git commit。当前默认 mixed 网络留给用户继续进入容器检查。

最终文档检查：`git diff --check` 通过；四个更新 Markdown 的行尾空白、代码块闭合及全部本地链接通过；AST 检查确认 B51 无 mask 调用；Git 清单核对为 23 文件（12 修改、11 新增），B00 无 diff；再次读取桥接值仍为 0。结果保存于 `ci-artifacts/rip/ospf-rip-coexist-20261008/documentation-checks.json`。代码和部署输入未再改变，未重复已通过的完整网络矩阵。

## 2026-10-08 22:26 - 恢复 Docker.py 并改用普通地址模式

- 用户意图：用户要求把 Docker.py 改回去，并希望确认桥接默认值 0 下网络能正常运行。结合用户此前希望 B51 关闭 selfManagedNetwork 的要求，直接回退编译器并关闭 B51 的地址改写，进行真实部署验收。
- 授权及技能：延续用户明确的恢复、运行和修复授权；使用 constructExample 的现有清单/只读运行检查、seedemu-bird-fib-verify 的 load1 < 50 和固定协议/FIB 样本、codex-task-confirmation-worklog 的实施记录。没有再次请求确认。
- 范围：恢复 `seedemu/compiler/Docker.py` 原始模板、地址映射和启动顺序，当前逐字节等于 HEAD；B51 `rip.py` 的 Docker 参数改为仅 `platform`，删除 self-managed 和 dummy 池；五场景编译回归改为严格核对真实 IPAM/节点地址及无 dummy 文件，保留 IX 导出验证。更新 B51 README、本文、`add_rip.md` 和 CI README。
- 保留：按 AS 的 OSPF/RIP 分配、RIP API 示例、三种后端、全部运行 ping 范围、IX 公告均不变。没有修改协议层、B00、宿主机桥接值或防火墙。
- 依据：桥接值 0 解决普通地址的宿主机 IPv4 bridge netfilter 干扰；旧补丁解决 self-managed 删除地址后 Docker 停止时找不到 transport 网关，是独立问题。本轮关闭 self-managed，因此可以完整恢复编译器，无需重新制造第 13.6 节记录的旧故障。

| 命令 / 操作 | 目的与结果 |
| --- | --- |
| `git status --short`、`git diff -- seedemu/compiler/Docker.py`、`rg`/`sed`、读取技能和适用 AGENTS | 确认三个编译器改动均属于本次工作，没有额外用户修改；当前桥接值 0，59 个旧 B51 服务运行 |
| 保存 `before/` 中原 Docker/B51/测试源码和 Docker.patch，保存旧生成目录、61 服务镜像 ID、运行状态及 restore-compose | 为实际切换保留恢复依据，不覆盖已有历史证据 |
| `apply_patch` | 撤销 Docker.py 三个改动，关闭 B51 selfManagedNetwork，更新回归断言和文档；未使用整体仓库 reset |
| `git diff --exit-code -- seedemu/compiler/Docker.py` 及 Python 对比 `git show HEAD:seedemu/compiler/Docker.py` 的字节内容 | 全部通过，SHA256 为 24d8b55250a6481771b82e5f480179a399ea9d502d292642847b1d7a44010efc |
| `python3 -m py_compile seedemu/compiler/Docker.py examples/internet/B51_rip/rip.py tests/test_rip_layer.py` | 通过；原始 Docker 模板的转义字符串产生既有 SyntaxWarning，未修改其内容 |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/docker-revert-20261008/unit-tests.xml` | 105 passed / 18.51s，RIP 76、基础路由 29 |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/docker-revert-20261008/static` | manifest、whitespace、compileall、import-smoke 全 passed |
| `python3 ci-artifacts/rip/docker-revert-20261008/prepare.py` | 旧网络继续运行时三后端普通 compile/build/config 全部退出 0；构建分别 15.50、29.54、16.87 秒 |
| `python3 ci-artifacts/rip/docker-revert-20261008/validate.py` | 普通 down 旧 B51，依次启动 BIRD、FRR、mixed，mixed 再实际 down/up；使用现有 readiness/probe/test 和协议/FIB 检查，最后保留默认网络 |

本轮证据目录为 `ci-artifacts/rip/docker-revert-20261008/`。验收辅助脚本复用上一轮命令管理、负载门槛及协议/FIB 检查，只将地址检查改为普通模式的 Docker inspect/元数据/容器实际地址一致，并增加 mixed restart 场景；没有调用早期诊断 fixture、添加防火墙例外、静态补救路由或指定 ping 源地址。

最终运行结果（22:43 完成）：

- BIRD 118/118、FRR 145/145、mixed 124/124、mixed 普通 down/up 后再次 124/124；每次 4386/4386 普通 ping 和 600/600 host 互通方向。四次 OSPF9/RIP18，全部 58 节点实际地址/Docker inspect/元数据一致，全部网络 IPAM 与真实前缀一致。
- 四次启动后等待负载门槛分别 10/30/90/0 秒；规定检查均在 load1 < 50 时进行。BIRD 固定 10 AS 协议及 17 AS FIB/实际前缀覆盖通过，两轮 mixed 固定 10 AS 协议及 16 AS FIB 通过；FRR 无 BIRD AS，专用检查明确不适用，由真实 FRR 协议/BGP/路由检查及完整 ping 覆盖。
- 旧 B51、BIRD、FRR、mixed 初次运行的普通 Compose down 均退出 0，项目网络残留为空；每轮普通 up 均成功，没有端点清理、地址池冲突或 Docker daemon 重启。
- `acceptance-summary.json` 的 success=true、四次 cases.success=true、default_mixed_network_left_running=true。默认普通地址 mixed 留在 B51/output 运行。
- 最后独立读取 Docker inspect、服务状态、实际配置路径、sysctl、负载及 Docker.py 字节内容：61 服务中 59 运行、两个 build-only dummy 正常退出 0；AS 路由器 OSPF9/RIP18、BIRD21/FRR6；Docker inspect 使用真实地址，没有 10.128.*；配置路径为默认 B51/output/docker-compose.yml；桥接值仍为 0、load1=26.83；Docker.py 精确等于 HEAD。写入 final-services.json。
- 源码回归 105 passed / 18.51s，静态 CI 四项通过。未执行 ARM 容器运行、远端 GitHub Actions 或 git commit，也未重复已经通过且输入未变的源码回归。
- 文档保持此前 self-managed 测试为历史，更新当前使用方法及完整文件清单为 22 文件（11 已有修改、11 新增）。Markdown 空白/代码块/本地链接、当前 Git 文件数、B00 无 diff、Docker.py 等于 HEAD 和桥接值 0 的检查通过，证据为 documentation-checks.json；最终文档补入本段结果后再做同一文档检查。

## 2026-10-08：AS 的 setIgpMode() API，缺省 OSPF

用户明确要求与 `as2.setCoreForwarding("mpls")` 风格一致，通过 `as2.setIgpMode("rip")` 选择 IGP，缺省 OSPF。按已授权的开发和实际验证范围继续实施，不再要求重复确认。继续应用前文已使用的任务 worklog、constructExample 和 BIRD/FIB 验证技能；适用目录没有新增 AGENTS 约束。

实施范围：AutonomousSystem 声明 API、共享 IGP 选择校验、Routing 调用入口、OSPF/RIP 按 AS 过滤、B51 示意代码、回归、描述性清单和文档。Docker.py 保持 HEAD，B00 保持原始源码；不修改宿主机已持久化的桥接值 0，不添加防火墙规则。

本轮证据目录为 `ci-artifacts/rip/as-igp-mode-20261008/`，独立于此前各轮。保存本轮开始时的相关源码、旧默认 output、61 服务镜像 ID 及 restore-compose；准备阶段不停止旧网络，运行阶段才正常 down 并切换。

| 命令 / 操作 | 用途和实际结果 |
| --- | --- |
| `git status --short`、`git diff`、`rg`、`sed`，核对 AS 的 `setCoreForwarding()`/`setOspfMode()`、层依赖及组件保存逻辑 | 确认 API 应由 AS 声明；协议层只消费选择，Routing 仍统一渲染 |
| `apply_patch` | 新增三个 AS API；缺省 OSPF；共享函数兼容旧 RIP-only/层范围，校验缺层与当前 MPLS 约束；两协议层按模式过滤；B51 删除范围集合、改用 AS setter |
| 首轮 `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/as-igp-mode-20261008/first-tests.xml` | 31 failed / 74 passed；均由 Rip 继承的抽象 `Layer.render()` 报 NotImplementedError 导致，保存到 first-tests.log/xml |
| 核对 `before/seedemu/layers/Rip.py`，补充 `Rip.render()` 的空操作实现 | 本轮开始前的源码也缺少 render；修复 Layer 生命周期，保持协议层不写原生配置 |
| 增加 AS API、默认两层/两后端/两种注册顺序、缺层/范围、序列化/合并和 MPLS 回归后执行 pytest | 126 passed / 19.21s；再补充显式 AS 选择优先于另一协议旧范围的两个用例 |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/as-igp-mode-20261008/unit-tests.xml` | 最终 128 passed / 20.27s，RIP/AS API 99、基础路由 29；unit-tests.log/xml |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/as-igp-mode-20261008/static` | manifest、whitespace、compileall、import-smoke 全 passed，static-ci.log 与 static/ci-summary.json |
| `python3 ci-artifacts/rip/as-igp-mode-20261008/prepare.py` | 三种后端的普通 CLI compile、Compose config/build 全退出 0；构建 BIRD16.96s、FRR15.45s、mixed14.60s |
| `python3 ci-artifacts/rip/as-igp-mode-20261008/validate.py` | 正常 down 旧默认项目，依次 up BIRD、FRR、mixed，再 mixed 正常 down/up；沿用 readiness/probe/test、负载门槛、协议/FIB 及真实地址检查 |

准备脚本复用已验证的生命周期辅助逻辑，将专用项目名改为 `b51-as-igp-bird`/`b51-as-igp-frr`，mixed 仍为默认 `output`。仍跳过此前已确认的唯一无关 Dead 旧对象：项目 seedemu-router/service test、空 Name、inspect NoSuchContainer；没有删除它，也没有跳过有效运行容器。当前项目、存活服务和镜像严格校验。

B51 将 AS2、AS11 和十二个 stub AS 显式设为 RIP，AS3/AS4/AS12 不设置，从而实际演示缺省 OSPF。层使用 `Ospf()`、`RIP()`，没有 mask 或层 asns 参数。原有 RIP 度量、被动接口、stub、水平分割示例和三后端选择均保留。AS 模式兼容旧 dump；既有 Base 合并机制保留不同 AS 的模式，不新增无必要的合并器改动。

23:48 完成全部实际运行验收，结果如下：

- BIRD 118/118、FRR 145/145、mixed 124/124、mixed 正常 down/up 后再次 124/124；四次各 4386/4386 普通 ping、600/600 host 互通方向。每次 OSPF9/RIP18，全部 58 节点的容器实际地址、Docker inspect 与元数据一致，网络 IPAM 对应真实前缀。
- BIRD 固定 10 AS 协议及 17 AS FIB/实际前缀覆盖检查通过；两轮 mixed 固定 10 AS 协议及 16 个 BIRD AS FIB 检查通过。FRR 全部 AS 路由器使用 FRR，BIRD 专用检查明确不适用，由 FRR daemon、原生路由、BGP 和完整连通性检查覆盖。
- 四轮启动后分别等待 20、60、30、20 秒达到 load1 < 50；规定检查和最终判断均符合门槛。旧默认项目及 BIRD、FRR、mixed 初次运行普通 down 全退出 0，项目网络残留为空，后续 up 正常。
- acceptance-summary.json 的 success=true、四次 cases.success=true、default_mixed_network_left_running=true。没有应用静态补救路由、ping -I、防火墙例外或修改宿主机桥接值。
- `python3 ci-artifacts/rip/as-igp-mode-20261008/final_checks.py` 独立读取当前 Docker 服务和地址、编译器字节、桥接值及文档：61 服务中 59 运行，两个 build-only dummy 正常退出 0；OSPF9/RIP18、BIRD21/FRR6；58 节点普通真实地址，配置路径全部为默认 B51/output/docker-compose.yml；桥接值 0、load1=9.33、Docker.py 精确等于 HEAD。写入 final-services.json。
- JUnit 独立计数确认 RIP/AS API99、基础路由29，总128；静态 CI 四项 passed。当前代码输入未再修改，没有无必要地重复源码测试或扩大运行矩阵。
- `git diff --check` 及 final_checks.py 的文档检查确认四份 Markdown 空白、代码块和本地链接通过；当前完整工作树 23 文件（12 已有修改、11 新增），B00 与 HEAD 一致，B51 零 mask/层 asns 调用；记录到 documentation-checks.json。
- 完整逐文件说明更新到 add_rip.md 第 16 节，README 的上一轮结果标记为历史。补入本段及最终证据链接后，再调用 final_checks.py 的 `documentation_checks()` 核对最终文档。
- 未执行 ARM 容器、远端 GitHub Actions、原生 MPLS 网络运行或 git commit。旧 B00 入口由单行替换副本的源码编译回归覆盖，本轮完整三后端容器验收针对 B51。默认 mixed 网络最后保留供用户直接使用。

## 2026-10-09 18:21 - 唯一 Rip 入口与通用 IGP 接口策略

用户意图：删除多余 RIP 类别名，统一为与 Ospf 一致的 Rip；解释 AS 的 legacy/router-transit-only，并将可以共用的 OSPF 接口分类抽象为 IGP 设置。工作期间用户补充要求新增 rip1009.md，仅说明 seedemu 内每一段源码修改。沿用此前已明确授权的修改、文档和实际运行验证范围继续完成。

范围：AutonomousSystem、Ospf、Rip、共用 IGP/BGP 元数据、层导出、B51 调用与描述、回归和文档。默认 OSPF 的协议选择不变；未设置接口策略时保留 OSPF all-local、RIP router-links 的行为。Docker.py、B00、宿主机桥接值及防火墙不修改。

设计与实现：

- legacy 表示全部 Local 网络默认主动，router-transit-only 表示仅至少两台路由器的 Local 网络默认主动，其他接口被动但公告前缀。用通用名称 all-local/router-links 和 set/get/hasIgpInterfacePolicy 表达这两个策略。
- 删除 OSPF 模式常量和新 AS 的独立 OSPF 字段；旧 set/get/hasOspfMode 只转接通用策略；旧保存组件的显式字段可以读取，新字段优先。
- 共用 is_igp_active_network/classify_igp_interfaces；删除 Ospf 内重复分类和 _bgp_metadata 中旧 classify_ospf_interfaces。Ospf 和 Rip 读取同一 AS 策略，协议专属参数及 Routing 原生语法继续保留。
- 删除 Rip.py 的 RIP=Rip 和包的 RIP 导出；代码、示例和单行替换测试统一使用 Rip。旧类别名不再提供。
- B51 在 AS2/RIP 和 AS3/OSPF 上演示同一个 router-links 策略，三后端及普通 Docker 工作流保留。
- 新增 rip1009.md，按 13 个 seedemu 源码文件逐函数/相关代码段解释完整 RIP 实现与本轮改动。add_rip.md 更新当前接口并保留历史；新文档不扩展到 examples/tests 的逐文件修改说明。

| 命令 / 操作 | 目的和结果 |
| --- | --- |
| `git status --short --untracked-files=all`、`git diff`、`rg`、`sed`；读取当前技能及适用 AGENTS | 核对已有 23 文件变更和 AS/层/组件关系；第一次 rg 包含不存在的 topology 目录返回提示，随后按实际 seedemu/tests/examples 范围核对 |
| 读取 B51 清单、拓扑和运行检查，以及 seedemu/testing 的 base/internet/runtime | 复用现有动态检查和生命周期，不重复实现固定探测 |
| 保存源码和文档到 `ci-artifacts/rip/igp-interface-policy-20261009/before/`；复制已验证运行辅助脚本到本轮目录 | 保留本轮开始时源码、后续旧 output、镜像 ID 和 restore-compose，避免覆盖前轮证据 |
| `apply_patch` 和 Python tokenize 按标识符替换 | 完成通用策略、单入口和逐段文档；协议术语和原生字符串中的 RIP 保留正确含义 |
| `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/igp-interface-policy-20261009/unit-tests.xml` | 首次 153 passed / 21.36s，RIP/IGP124、基础路由29；unit-tests.log/xml |
| `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/igp-interface-policy-20261009/static` | manifest、whitespace、compileall、import-smoke 四项 passed；static-ci.log 与 static/ci-summary.json |
| `python3 ci-artifacts/rip/igp-interface-policy-20261009/prepare.py` | 三种普通 CLI 编译、Compose config/build 退出 0；构建 BIRD14.20s、FRR14.15s、mixed14.35s，旧网络在准备阶段保持运行 |
| `python3 ci-artifacts/rip/igp-interface-policy-20261009/validate.py` | 正常 down 旧默认项目，顺序运行 BIRD、FRR、mixed 及 mixed 正常 down/up；复用负载门槛、readiness/probe/test、协议/FIB 和真实地址检查 |

新增 25 项回归：通用策略缺省/显式状态、7 项非法值、两协议×两策略×两后端的8项行为、旧 API 两项、旧字段 dump/load 六项、RIP 精细 passive 覆盖一项。原有组件保存/合并检查补充通用策略断言。旧 AS 缺省 OSPF、单层 Rip 替换和当前 MPLS 的 OSPF 约束继续通过。

运行证据目录为 `ci-artifacts/rip/igp-interface-policy-20261009/`，专用项目名 b51-if-policy-bird/frr，默认 mixed 仍用 B51/output。辅助脚本继续仅跳过此前确认的无关、不可 inspect 的 Dead 旧对象，没有 Docker prune、daemon 重启、端点强制清理或 host 配置写入。

18:46 用户补充后续验证偏好：修改过程中只做静态代码验证，全部源码改完以后统一实际运行，不随每次调整重复测速或启动网络。本轮源码在当前运行矩阵开始前已全部完成；正在运行的是最终统一验收，后续文档更新只检查格式、链接和覆盖范围，不重新执行源码测试或容器矩阵。

元数据集中前的上述运行矩阵已完成：BIRD118/118、FRR145/145、mixed及mixed-restart各124/124；四次各4386/4386普通ping、600/600主机互通方向，58节点真实地址一致，OSPF9/RIP18。启动后负载门槛分别等待90/30/80/20秒。普通down均退出0且无项目网络残留，默认mixed已保留运行。此证据只对应本轮接口策略源码；下面的新元数据修改需在全部改完后进行统一最终验证。

## 2026-10-09 18:50 - 集中 OSPF/RIP 元数据，简化 iBGP 表选择

用户新增六项要求：OSPF元数据移出BGP模块，RIP提供对应存取/计时器函数且不保留独立rip_metadata；检查MPLS与无IGP两处master4分支、helper默认参数及五处节点条件是否合理。继续已有授权，按用户偏好只在源码全部完成后统一实际运行。

实现范围及作用：

- _igp_metadata接收OSPF的属性键、默认计时器、normalize及Intent存取，接收RIP默认值/选项校验；新增RIP_INTERFACE_INTENTS_ATTR、DEFAULT_RIP_*、normalize/get_rip_timers和set/get_rip_interface_intents。RIP原属性键__rip_intent保留，避免丢失旧组件节点数据。
- 删除独立_rip_metadata；全部Python调用方改为统一模块。_bgp_metadata移除OSPF内容，内容完全相同的两组MPLS helper只保留一组，BGP和MPLS函数行为不变。
- Ibgp集中计算每台路由器的表：正常OSPF为t_ospf，RIP为t_rip，MPLS或没有Intent的节点为master4。两个helper必传映射，五处重复条件改为直接查本地节点名称。原line144仅处理MPLS，和line152的无提供者不是同一个条件。
- 新增10项回归：元数据输入输出复制及协议隔离1项、旧键和计时器缺省1项、三后端×禁用client/RR共6项、无IGP层的full-mesh/RR共2项。当前全部回归预期163项，真实结果由最终执行记录。
- rip1009.md更新为12个seedemu源码文件的逐代码段说明；add_rip和B51 README更新。Docker.py、B00、宿主机桥接值0和防火墙不修改。

命令记录：

| 命令 / 操作 | 目的与结果 |
| --- | --- |
| rg、sed、git diff/status、JSON读取 | 核对全部私有模块调用和旧iBGP分支；读取上一阶段验收时仅使用摘要字段，首次误读完整JSON输出过大后改为只打印摘要 |
| 保存源码/文档到ci-artifacts/rip/igp-metadata-20261009/before，复制此前运行辅助脚本 | 独立保留重构前源码；准备脚本随后保存现有output、镜像与restore-compose；专用项目改名b51-metadata-bird/frr |
| apply_patch及一次Python标识符替换 | 完成元数据合并、iBGP映射、回归和文档；没有重置工作树 |
| python3 -m py_compile 九个修改的Python文件 | 通过；修改期间没有运行单元用例、容器或性能测量 |
| git diff --check及rg扫描旧导入 | 通过；当前Python源码无_rip_metadata和旧set/get_rip_intent调用，rg无匹配返回1是预期 |

下面的最终验证统一执行，证据目录为 `ci-artifacts/rip/igp-metadata-20261009/`。继续复用现有普通Compose生命周期、负载门槛、readiness/probe/test与协议/FIB检查，不引入临时路由或网络配置。

### 本轮首次执行结果及停止测试要求

元数据和iBGP源码整理后、用户新增第7/8点之前，执行了一次pytest及静态CI。pytest为161 passed / 2 failed / 21.96s；失败的两个新元数据用例直接创建了尚未经过Registry.register的Router，_attrs还未初始化。这是新增测试的初始化错误，现已补充正常节点注册；生产Registry和节点构造函数不修改。静态CI manifest、whitespace、compileall、import-smoke四项通过。

原执行命令为 `python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/igp-metadata-20261009/unit-tests.xml` 和 `python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/igp-metadata-20261009/static`。在后续源码变化后，将结果改名保存为before-template-tests.log/xml、before-template-static-ci.log和before-template-static，明确其不代表最终源码。

用户继续要求第7点BIRD RIP采用文件顶部模板，第8点FRR采用统一igp_body；之后明确要求“中断测试，全部修改完成后经我同意再统一进行测试”。此要求覆盖此前的直接运行授权：停止后不再执行pytest、CI、compile/build/up或运行ping。已通过/proc进程参数定向检查确认matching_test_processes为空；容器验收尚未开始，原网络保持运行。

新增修改：RoutingFileTemplates增加bird_rip_connected_body、bird_rip_connected_interface、bird_rip_body、bird_rip_interface四个模板；_render_bird_rip删除内联BIRD语句，负责Intent筛选和模板参数组装，保留json接口名引用。_render_frr_control_plane按实际身份if/elif选择一个igp_body，统一body = igp_body + bgp_body + mpls_body；ospfd/ripd开关与所选配置一致，MPLS自带OSPF/LDP保留原逻辑。rip1009、add_rip及README同步更新。

后续仅进行AST语法/源码引用审查、git diff --check及Markdown链接/源文件覆盖核对，不导入SeedEMU执行代码或启动测试。完成后请求用户同意统一测试。待批准的命令为：

```sh
python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/igp-metadata-20261009/unit-tests.xml
python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/igp-metadata-20261009/static
python3 ci-artifacts/rip/igp-metadata-20261009/prepare.py
python3 ci-artifacts/rip/igp-metadata-20261009/validate.py
python3 ci-artifacts/rip/igp-metadata-20261009/final_checks.py
```

这些命令尚未对最终源码执行。网络验收将包含BIRD、FRR、mixed普通compile/build/up及mixed普通down/up，旧网络/镜像保存、全主机及路由器实际接口普通ping、readiness/probe/test与适用的协议/FIB检查。当前文档不宣称最终版本已通过。

停止测试后的源码审查已完成：只使用ast.parse解析16个变更Python文件，扫描私有导入，核对5份Markdown的空白/代码块/本地链接，确认rip1009恰好覆盖全部12个seedemu源码文件，git diff --check通过。当前24个变更文件（13修改、11新增），Docker.py逐字节等于HEAD，B00无diff，独立_rip_metadata不存在且Python调用方无旧导入。没有导入SeedEMU或运行测试。记录及源码SHA256见 [source-review.json](../../../ci-artifacts/rip/igp-metadata-20261009/source-review.json)。

## 2026-10-09 19:30 - AS 唯一选择协议及最终统一验收授权

- 用户意图：第9/12点要求删除Ospf/Rip的setAsns等层范围，只用AS.setIgpMode并保持缺省OSPF；删除两层空render。最新消息明确授权完成源码后的实验验证，解除此前暂停测试要求。
- 源码范围：Ospf/Rip删除范围与render覆写；_igp_metadata删除normalize_igp_asns、协议自动推断，只做协议层/MPLS校验；Layer.render提供公共默认空操作；DefaultRipMerger删除范围合并；DefaultOspfMerger逐字节恢复HEAD。AS已有构造和旧字段回退始终缺省OSPF。
- 回归与文档：测试显式声明RIP，移除旧范围API用例，检查Rip-only仍缺省OSPF及旧层字段不覆盖AS；B00副本显式选择AS而原始B00不修改。rip1009覆盖当前12个seedemu源码文件，add_rip第19节和README/CI描述同步。
- 命令：rg/git diff/status、源码和技能读取、apply_patch、AST/链接核对；备份到ci-artifacts/rip/as-only-igp-20261009/before，复制既有prepare/validate/diagnostic_helpers/final_checks，专用项目改为b51-as-only-bird/frr。
- 验证：停止要求生效期间未执行新测试或切换容器；现在将统一执行pytest、静态CI、三后端普通compile/build/up及mixed普通down/up，记录实际结果。运行前旧mixed仍为第17节生成配置，不能宣称它代表最新源码通过。
- 环境：Docker.py和B00保持HEAD，桥接值保持用户设定的0；不写sysctl/防火墙、不注入路由、不用ping -I。保存旧output、镜像ID和恢复Compose；普通down清理当前实验项目，最终保留默认mixed运行。

本轮统一命令（实际结果在执行后追加）：

```sh
python3 -m pytest -q tests/test_rip_layer.py tests/test_frr_exabgp_foundation.py --junitxml=ci-artifacts/rip/as-only-igp-20261009/unit-tests.xml
python3 tests/ci/run_ci.py static --artifact-dir ci-artifacts/rip/as-only-igp-20261009/static
python3 ci-artifacts/rip/as-only-igp-20261009/prepare.py
python3 ci-artifacts/rip/as-only-igp-20261009/validate.py
python3 ci-artifacts/rip/as-only-igp-20261009/final_checks.py
```

### 本轮统一源码回归结果

最终源码首次统一pytest执行为 **147 passed / 21.79s**（RIP/IGP118、既有基础路由29），unit-tests.log/xml保存在本轮as-only目录。数量变化来自删除已移除的层范围API用例，并补充AS唯一选择及旧字段兼容检查；此前两个未注册节点的元数据测试已正常通过。静态CI的manifest、whitespace、compileall、import-smoke四项通过。

运行前只读源码审查为16个Python AST、5份Markdown及全部12个seedemu源码链接覆盖通过，git diff --check通过；24个变更文件，Docker.py、DefaultOspfMerger.py逐字节等于HEAD，B00无diff。记录在本轮source-review.json。三种后端compile/config/build正在执行，尚未据此宣称真实网络通过。

### 2026-10-09 19:50 - 最终真实网络结果与根目录文档

| 命令 / 操作 | 实际结果 |
| --- | --- |
| prepare.py | 普通BIRD/FRR/mixed compile、Compose config/build全0；构建14.90/16.00/13.95s，旧网络及镜像先备份 |
| validate.py | 正常停止旧网络；BIRD118/118、FRR145/145、mixed124/124、mixed普通down/up后124/124；每轮4386/4386普通接口ping、600/600 host方向 |
| 固定BIRD协议/FIB与真实地址检查 | 适用轮次各10个协议样本；FIB全BIRD17AS、mixed两轮16AS，选中前缀无缺失；每轮58节点真实/Docker/元数据地址一致 |
| 负载门槛 | 四轮启动后等待70.00/120.01/40.00/0.00s；规定检查和最终判断load1<50 |
| final_checks.py 首次独立容器核对 | 61服务、59运行，2构建辅助容器退出0；OSPF9/RIP18、BIRD21/FRR6，桥接0，Docker.py等于HEAD；load1=47.94 |
| 最终源码SHA256核对 | 全部16个Python文件与本轮开始时一致，未中途修改源码或运行测试绕过失败 |
| 首次文档检查 | 两份文档在实验期间移到根目录，旧路径FileNotFoundError；网络和容器检查已通过，此失败只涉及文档位置 |
| 用户回复与文档修正 | 用户明确要求保留根目录并修正全部引用；重算add_rip82处、rip1009的12处源码链接、B51 README6处文档链接，更新路径文字及验收记录；修改本轮artifact checker的文档路径，不改生产代码 |

AS163 router0在四轮均到其他84个实际接口地址成功；AS2 r100/r101各83、r102/r105各84个目标均通过。每轮OSPF9/RIP18。默认mixed普通重启后已保留运行；普通down均退出0且无项目网络残留。桥接值始终0，未写sysctl、未加防火墙例外/静态补救路由、未用ping -I。Docker.py、DefaultOspfMerger.py与HEAD一致，B00未修改。

只读摘要检查曾有一次临时Python命令括号错误，已立即修正；未影响实验或源码。第一次查看选定ping行时输出包含较长command字段，后改为只输出name/status/attempts/exit/stdout。所有正式回归及四轮网络验收没有失败。

根目录文档为[add_rip.md](../../../add_rip.md)和[rip1009.md](../../../rip1009.md)；[最终报告](../../../ci-artifacts/rip/as-only-igp-20261009/validation-report.md)、[完整摘要](../../../ci-artifacts/rip/as-only-igp-20261009/acceptance-summary.json)、[精简证据](../../../ci-artifacts/rip/as-only-igp-20261009/validation-evidence.json)。文档收尾后只重查格式/链接/源码覆盖，不重复已通过的单元、构建或网络实验。

最终根目录文档检查退出0：5份Markdown格式/代码块/本地链接、rip1009完整覆盖12个seedemu源码文件、24文件清单、git diff --check、B51无mask和层asns调用、Docker/B00未修改均通过。库内扫描不再有旧文档路径引用；最终源码SHA256仍一致，完成判断load1=34.04<50。证据为本轮documentation-checks.json、final-documentation-checks.log及completion.json。未重跑单元或网络实验。

## 2026-10-10 10:27 - 保存完整修改到 backend 分支

- 用户意图：复制当前所有修改，创建名为backend的本地分支。
- 来源：development，基准提交964d1665b99aee2a915f3c6e22a4248cd01a1837；24个未提交文件（13修改、11新增），包含RIP/IGP源码、B51、测试/CI及根目录两份文档。
- 操作：先将24文件内容、SHA256、原始diff和分支位置保存到ci-artifacts/branch-backend-20261010；执行git switch -c backend，把这24个文件加入暂存区，并提交完整快照。原development分支保留在基准提交。
- 提交说明：Add RIP layer, AS-level IGP selection and validated B51 example。
- 核对：git diff --check、git diff --cached --check；逐文件校验工作区与提交内容，检查backend父提交、development引用和工作区状态；结果/提交ID另存本轮result.json。
- 验证范围：仅Git分支和快照操作，除本条工作日志外不修改现有文件内容，不重新运行已完成的单元或网络实验，不操作运行中的容器。本次生成本地分支。

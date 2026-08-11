# Benchmark 新场景开发规范

本文档用于指导新的 Agent 在 SEED Emulator benchmark 中设计、实现和验证新场景。目标是让新增场景与现有代码保持一致，并确保测试真正衡量 MIMO AI 的自主诊断和自主修复能力。

## 1. 强制边界

1. 只允许新增或修改 `benchmarks/` 下的文件。
2. 不得修改 `examples/`、`seedemu/` 或仓库其他目录的源码。
3. 可以导入已有 example 的 `build_emulator()`，但生成物必须输出到：

   ```text
   benchmarks/generated/<topology_name>/output
   ```

4. 软件安装应在拓扑构建阶段通过 `addSoftware()`、Dockerfile 构建命令或 benchmark 内的拓扑包装器注入，不得要求修改宿主机或 example 源码。
5. 测试报告必须由 `benchmarks/benchmark_cli.py` 生成，不得手工拼写测试结果。
6. 不得把 API 密钥、SSH 私钥、sudo 密码或其他凭据写入新文件、日志或报告。
7. 所有临时验证脚本、冒烟测试、调试入口和一次性测试程序必须放在：

   ```text
   benchmarks/tests/
   ```

   不得将临时测试脚本放在 `benchmarks/` 根目录、`benchmarks/scenarios/`、
   `benchmarks/topologies/` 或仓库其他路径。可长期复用的自动化测试也应优先
   放在 `benchmarks/tests/`，并使用能够说明测试目标的文件名。

## 2. 开发前审计

编码前必须完成以下检查：

1. 阅读：

   ```text
   benchmarks/scenarios/base.py
   benchmarks/scenarios/strict_network_software.py
   benchmarks/scenarios/__init__.py
   benchmarks/benchmark_cli.py
   benchmarks/manager.py
   benchmarks/agents/ai_agent.py
   ```

2. 查找一个故障生命周期最接近的新场景作为参考。
3. 确认目标拓扑、目标容器、正常基线、故障状态和恢复判据。
4. 确认故障是确定性的、可重复的、可安全恢复的。
5. 确认场景名称、故障类别和拓扑名称不与现有注册项冲突。

## 3. 场景设计原则

一个合格场景必须满足以下条件：

- **真实故障**：注入后必须改变实际配置、服务状态或数据面行为。
- **健康基线**：注入前必须证明目标功能正常。
- **确定性**：同一拓扑上重复执行应产生相同故障。
- **可观测性**：Agent 可以通过合理的只读命令发现根因。
- **独立验证**：验证器检查功能或配置事实，不能仅检查修复命令是否运行。
- **幂等恢复**：标准清理命令可以重复执行。
- **作用域明确**：故障和修复应限制在指定容器或 Docker 网络。
- **无答案泄漏**：通用 prompt 可以说明资产、目标和约束，但不应直接调用标准 `get_fix_cmd()`。

优先设计“一个主要根因、一个明确故障类别”的场景。双重或级联故障必须明确主要评分类别，并确保验证器覆盖所有必须恢复的状态。

## 4. 文件和命名规范

场景文件放在：

```text
benchmarks/scenarios/<scenario_module>.py
```

推荐命名：

```python
class ExampleFaultScenario(BaseScenario):
    name = "example_fault_01"
    description = "简洁描述故障和影响"
    topology = "B00_mini_internet"
    fault_type = "example_fault"
```

约束：

- 文件名、`name` 和 `fault_type` 使用小写 snake_case。
- `name` 必须包含稳定编号，例如 `_01`。
- 类名使用 PascalCase，并以 `Scenario` 结尾。
- 容器名、地址、接口名、配置路径应定义为类属性，避免散落在方法中。
- 文档字符串和注释应说明“为什么”，不要重复代码表面行为。

## 5. 选择基类

### 5.1 普通场景

继承 `BaseScenario`：

```python
from scenarios.base import BaseScenario


class ExampleFaultScenario(BaseScenario):
    ...
```

适用于已有拓扑内的配置、服务、接口、路由或 Docker 网络故障。

### 5.2 需要严格基线和注入确认的网络软件场景

继承 `StrictNetworkSoftwareScenario`：

```python
from scenarios.strict_network_software import StrictNetworkSoftwareScenario


class ExampleSoftwareScenario(StrictNetworkSoftwareScenario):
    topology = "B00_network_software_suite"
    ...
```

该基类会：

1. 执行 `get_setup_cmd()`；
2. 验证健康基线；
3. 注入故障；
4. 验证故障确实生效；
5. 注入无效时执行安全恢复并拒绝产生假阳性。

## 6. 必须实现的接口

每个场景至少实现：

```python
def get_inject_cmd(self) -> str:
    """返回故障注入命令。"""

def get_verify_cmd(self) -> str:
    """返回独立功能验证命令。"""

def get_fix_cmd(self) -> str:
    """返回标准安全清理命令；不作为 Agent 修复成绩。"""

def check_verified(self, output: str) -> bool:
    """解释验证命令输出，返回是否健康。"""
```

严格网络软件场景还必须实现：

```python
def get_setup_cmd(self) -> str:
    """创建可重复的健康基线。"""
```

`get_fix_cmd()` 的作用仅包括：

- 无 AI 验证时恢复场景；
- AI 修复失败后的安全清理；
- 保证下一个场景从健康状态开始。

在 `--repair-eval` 中，标准修复不得计入 Agent 修复成功。

## 7. 命令编写规范

1. 命令必须非交互执行。
2. 优先使用明确的 `docker exec <container> ...`。
3. 对配置文件使用精确替换、Base64 或可靠的 heredoc，避免脆弱的多层 shell 引号。
4. 多命令操作应保证关键步骤失败时不会被误判成功。
5. 删除接口、规则或 qdisc 时，清理命令应允许目标不存在：

   ```sh
   ... 2>/dev/null || true
   ```

6. 配置修改后应运行软件自带的语法检查或重载命令。
7. 不使用 `docker rm`、`docker kill`、`--privileged`、宿主机 `sudo` 或挂载 Docker socket。
8. 不依赖容器列表顺序；使用确定的容器名。
9. 不使用固定长时间 sleep 代替状态检查；路由收敛和服务恢复由验证器轮询。
10. `repair_commands` 不得在 `docker exec` 外使用重定向、管道、`;`、`&&` 或 `||`。容器内需要组合命令时，必须使用完整引用的 `docker exec <container> sh -c '<payload>'`；否则操作符会在 VM 宿主 shell 执行并被白名单拒绝。

## 8. 验证器规范

验证器是场景评分的事实来源，必须与 Agent 的修复建议解耦。

推荐验证：

- 连通性：`ping`、DNS 查询、HTTP 请求；
- 配置语法：`named-checkconf`、`bird -p`、`kea-dhcp4 -t`；
- 协议状态：`birdc show protocols`、`vtysh`；
- 内核状态：`ip route`、`ip link`、`wg show`、`tc qdisc`；
- Docker 状态：`docker inspect`、网络连接信息。

避免错误判断：

```python
# 错误："100% packet loss" 也包含字符串 "0% packet loss"
return "0% packet loss" in output

# 正确
return re.search(r"(?<!\d)0% packet loss", output) is not None
```

注入前健康、注入后故障和修复后健康必须是三个可区分状态。

## 9. Agent 自主修复协议

所有场景通过基类的 `run_repair_evaluation()` 接入统一协议：

```text
注入故障
→ MIMO 比较健康基线与故障后状态并诊断
→ MIMO 返回 repair_commands
→ 场景白名单审查
→ 实际执行 Agent 命令
→ 独立验证器轮询
→ 拒绝或验证失败时将结构化原因反馈给同一 Agent 会话继续修订
→ 失败时执行标准清理
```

诊断与修复必须独立评分：

1. `category == fault_type` 只决定 `correct_diagnosis`；
2. 即使类别识别错误，只要 MIMO 提供了 `repair_commands`，仍允许进入安全审查；
3. 只有通过场景容器和命令前缀白名单的命令才能实际执行；
4. `repair_verified` 只由至少一条实际执行的 Agent 命令和独立验证器共同决定；
5. 类别错误但功能修复成功时，必须记录为“诊断错误、修复成功”，不得改写诊断成绩。

不得在场景中重新实现“诊断正确后调用 `fix_fault()`”的旧模式。

### 跨场景隔离

repair-eval 会在 Agent 成绩确定后执行两层恢复：

1. 无论 Agent 修复成功或失败，都执行场景标准 `get_fix_cmd()` 并验证；
2. CLI 使用 Compose `down --remove-orphans` 和 `up -d` 重新创建拓扑容器。

因此，标准 fix 未覆盖的额外文件、iptables/tc 规则、接口修改和服务状态
不会进入下一个场景。快速重建失败时，CLI 会执行完整拓扑重建；完整重建
仍失败时，拓扑被标记为污染并立即停止批次。

新场景不得绕过该隔离流程。报告必须记录：

- `standard_cleanup_verified`；
- `isolation_recreated`；
- `isolation_fallback_rebuild`；
- `topology_tainted`。

### 诊断命令安全边界

Agent 的多轮问询只能执行 `AIAgent.is_read_only_diagnostic_command()` 允许的只读命令。禁止在诊断阶段执行 `docker start/stop/restart`、配置写入、服务重载、iptables/ip/tc/wg 修改或任意 shell 组合，从而绕过最终修复白名单。新增诊断工具时必须：

1. 添加足够具体的只读命令模式；
2. 添加允许与拒绝用例的回归测试；
3. 在报告中记录实际执行及被拒绝的诊断命令。

### 可观测性与低噪声

- 容器发现必须使用 `docker ps -a`，保证 stopped/exited 容器可见；
- 不得依赖 Docker 返回顺序或只检查前若干目标而漏掉异常；
- 全量扫描必须分别采集健康基线和故障后状态，只向 Prompt 输出差异；
- 每条观测必须包含采集命令、容器、配置/状态资产、接口和输出来源；
- 不输出空的专项状态章节；
- 盲测可以提供通用实时状态，但不得注入场景名称、目标容器或标准答案。

## 10. 修复命令白名单

`BaseScenario` 会从故障注入命令和常用类属性推导允许修改的容器。建议显式声明目标属性：

```python
container = "..."
target = "..."
target_container = "..."
left = "..."
right = "..."
```

需要更严格控制时：

```python
repair_containers = (
    "target-container-1",
    "target-container-2",
)
```

如果场景需要标准白名单以外的命令前缀，可以设置：

```python
repair_command_prefixes = (
    "允许的、足够具体的命令前缀",
)
```

不得使用过宽前缀，例如 `docker`、`python3` 或 `/bin/sh`。

特殊场景可以覆盖 `is_repair_command_allowed()`，但必须保持最小权限，并记录所有拒绝和执行的命令。

## 11. 场景专属 prompt

只有当通用状态不足以公平定位故障，或 shell 命令容易产生结构性错误时，才覆盖：

```python
def get_repair_context(self) -> str:
    return super().get_repair_context() + """
## 本场景专属约束

- 指定可修改资产和正确的不变量。
- 指出容易误判的正常状态。
- 说明必须使用的语法检查。
- 禁止修改无关生产配置。
"""
```

专属 prompt 可以提供：

- 故障资产路径；
- 正确服务器、前缀、接口或网络名称；
- 禁止使用的错误替代方案；
- 安全编码方式；
- 必须运行的验证工具。

专属 prompt 不得：

- 要求调用 `get_fix_cmd()`；
- 要求运行 benchmark 的 `repair` 辅助入口；
- 直接绕过 MIMO 返回预定义结果；
- 放宽容器白名单。

## 12. 新故障类别和 AI 可观测性

新增 `fault_type` 时，检查 `benchmarks/agents/ai_agent.py`：

1. 在系统 prompt 的故障类别列表中增加类别和定义。
2. 在专项直接证据中增加明确映射。
3. 如果默认状态采集看不到故障，向 `collect_network_state()` 增加确定性的只读命令。
4. 状态采集应限制输出长度，避免无界 token 消耗。
5. 不把标准修复答案放进初始状态。

随机或动态拓扑应在运行时发现容器和地址，不得硬编码某次随机生成结果。

## 13. 拓扑构建规范

新增拓扑包装器放在：

```text
benchmarks/topologies/<topology_name>.py
```

生成路径：

```text
benchmarks/generated/<topology_name>/output
```

示例结构：

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from seedemu.compiler import Docker, Platform

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "examples/..."
OUTPUT = REPO_ROOT / "benchmarks/generated/example/output"


def main():
    emulator = source_module.build_emulator()
    # 仅在这里注入 benchmark 所需软件或节点设置。
    emulator.render()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    emulator.compile(
        Docker(platform=Platform.AMD64),
        str(OUTPUT),
        override=True,
    )
```

不要让 example 默认写入 `examples/.../output`。如果原脚本支持 `--output`，CLI 应直接传入 benchmark 本地输出路径。

## 14. 注册步骤

### 14.1 场景注册

在 `benchmarks/scenarios/__init__.py`：

1. 导入场景类；
2. 加入 `ALL_SCENARIOS`；
3. 由 `SCENARIO_MAP` 自动生成名称映射。

### 14.2 CLI 注册

如果使用新拓扑，在 `benchmarks/benchmark_cli.py` 中更新：

- `get_topology_build_cmd()`；
- `get_topology_path()`；
- `start_topology()` 的构建和启动超时；
- 必要的同拓扑复用逻辑。

benchmark 专属镜像可能被清理，因此启动前应执行 Compose build。

### 14.3 Manager 注册

同步更新 `benchmarks/manager.py` 的构建和启动映射，路径必须与 CLI 一致。

## 15. 分层测试流程

### 阶段 A：静态检查

```bash
python3 -m py_compile \
  benchmarks/scenarios/<scenario>.py \
  benchmarks/benchmark_cli.py \
  benchmarks/manager.py \
  benchmarks/agents/ai_agent.py
```

```bash
python3 benchmarks/benchmark_cli.py --list
```

确认场景只注册一次，名称、类别和拓扑正确。

### 阶段 B：构建检查

1. 生成拓扑；
2. 确认输出只在 `benchmarks/generated/`；
3. 构建目标镜像；
4. 确认软件存在；
5. 确认容器名称与场景一致。

### 阶段 C：无 AI 生命周期验证

证明：

1. 健康基线通过；
2. 故障注入生效；
3. 标准清理恢复；
4. 重复运行不会留下污染。

可以使用统一 CLI 的 `--validate-only`，报告仍必须通过 CLI 生成。

### 阶段 D：MIMO 自主修复验证

```bash
python3 benchmarks/benchmark_cli.py \
  --agent ai \
  --repair-eval \
  --reuse-running \
  --scenario <scenario_name> \
  --report benchmarks/reports/<REPORT_NAME>.md
```

必须检查报告中的：

- 诊断类别；
- 提议命令数；
- 实际执行命令；
- 白名单拒绝命令；
- 功能验证；
- API 调用、token 和延迟。

CLI 通过全局参数 `--max-turns N` 控制 MIMO 交互上限，默认 20 轮，并统一传递给普通诊断、自主修复和随机拓扑 Agent。场景不得自行创建不同轮数的 Agent、提前注入答案或在轮数耗尽后调用标准 fix 来改变自主修复成绩。正式报告必须记录实际使用的问询上限。

CLI 将 `--max-turns` 限制在 1 到 1000，默认仍为 20；高上限只在用户明确要求的长时测试中使用。该参数只是上限；修复模式下，空的或纯查询型 `repair_commands` 不构成完整结果，Agent 会收到反馈并继续问询。

CLI 会自动将 stdout 和 stderr 同时显示在终端并保存到 `benchmarks/logs/BENCHMARK_CLI_<timestamp>_<pid>.log`，报告中会记录对应日志路径。直接运行即可：

```bash
python3 -u benchmarks/benchmark_cli.py \
  --agent ai --repair-eval --scenario <scenario_name> --max-turns 20 \
  --report benchmarks/reports/<REPORT_NAME>.md
```

日志按每次 CLI 进程单独创建，避免覆盖或混合并行测试。日志、报告和临时测试文件均不得写到 `benchmarks/` 以外。

如果失败，先区分：

- 模型诊断或修复能力失败；
- 场景状态不可观测；
- prompt 约束不足；
- 白名单误拒；
- 验证器等待不足；
- 拓扑或镜像构建失败。

不得通过直接调用标准 fix 来掩盖 AI 失败。

### 阶段 E：最终健康和范围检查

1. 执行场景独立验证命令；
2. 确认故障规则、接口、配置和服务均已恢复；
3. 编译全部 benchmark Python 文件；
4. 检查修改范围：

   ```bash
   git diff --name-only -- . ':(exclude)benchmarks/**'
   ```

5. 工作区已有的外部改动应记录为原有改动，不得覆盖或修改。

## 16. 报告要求

最终报告必须由 CLI 生成，并至少包含：

- 场景、拓扑和故障类别；
- MIMO 诊断和可信度；
- 诊断是否正确；
- Agent 修复是否授权；
- 实际执行的修复命令；
- 被白名单拒绝的命令；
- 独立修复验证结果；
- API 调用、token、延迟和耗时；
- 场景基础设施错误。
- 修复命令是否提交、是否至少一条通过白名单并执行；
- 诊断阶段执行和拒绝的命令；
- Agent 根因判断和实际问询轮数。
- `target_container`、`artifact`、`faulty_value`、`expected_value`；
- 类别、目标、资产、错误值和期望值的分项根因评分；
- 每次修复尝试的执行、拒绝原因和独立验证输出。

“修复验证通过”只表示 Agent 命令恢复了目标功能。失败后的标准清理不得改变该成绩。

### 16.1 盲测要求

CLI 默认启用 `--blind`。盲测时不得向 Agent 暴露场景名称、场景描述、预期故障类别、故障注入命令、目标容器、标准修复命令或场景专属提示；Agent 必须仅根据实时只读诊断证据生成并执行修复命令。

`--no-blind` 仅用于场景开发和定向调试，可向 Agent 传入 `get_repair_context()`。正式 MIMO 修复测试和交付报告必须使用默认盲测，并在报告中明确记录测试模式。

## 17. 完成定义

新场景只有满足以下全部条件才算完成：

- [ ] 所有修改位于 `benchmarks/`；
- [ ] 场景类和命名符合规范；
- [ ] 健康基线、故障注入和恢复均可重复；
- [ ] 验证器独立且无字符串误判；
- [ ] 已接入自主修复协议；
- [ ] 修复命令限制在最小容器范围；
- [ ] 新故障类别对 MIMO 可观测；
- [ ] CLI 和 manager 注册一致；
- [ ] 拓扑输出位于 `benchmarks/generated/`；
- [ ] `py_compile` 和 `--list` 通过；
- [ ] 无 AI 生命周期验证通过；
- [ ] MIMO `--repair-eval` 已运行；
- [ ] 报告由 benchmark CLI 生成；
- [ ] 测试后环境恢复健康；
- [ ] 未修改 `benchmarks/` 以外文件。

## 18. 交付说明模板

新 Agent 完成后应汇报：

```text
场景名称：
故障类别：
拓扑：
目标容器/资产：
故障注入效果：
独立验证方式：
Agent 实际修复命令：
自主修复结果：
CLI 报告路径：
最终健康检查：
修改文件：
尚存限制：
```

不要只汇报“代码已编写”。必须给出构建、注入、AI 修复、验证和报告证据。

#!/usr/bin/env python3
"""
AI 诊断代理 - 交互式版本

支持 AI 主动请求执行命令，进行多轮交互诊断。

交互协议:
- AI 返回 {"action": "diagnose", ...} → 诊断完成
- AI 返回 {"action": "execute_commands", "commands": [...], ...} → 执行命令后继续

使用方法:
1. 设置环境变量:
   export AI_API_KEY="your-api-key"
   export AI_API_BASE="https://api.xiaomimimo.com/v1"  # 可选
   export AI_MODEL="mimo-v2.5"  # 可选

2. 运行代理:
   python3 ai_agent.py
"""

import os
import json
import re
import shlex
import subprocess
import time
import requests
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime

from observations import capture_network_state, format_state_delta


@dataclass
class Diagnosis:
    """诊断结果。"""
    category: str
    root_cause: str
    symptoms: List[str]
    proposed_fix: str
    confidence: float
    reasoning: str
    repair_commands: List[str] = field(default_factory=list)
    target_container: List[str] = field(default_factory=list)
    artifact: str = ""
    faulty_value: str = ""
    expected_value: str = ""
    root_causes: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class CommandRequest:
    """命令执行请求。"""
    commands: List[str]
    reasoning: str


@dataclass
class APICallRecord:
    """单次API调用记录。"""
    turn: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    success: bool = True
    error: str = ""

@dataclass
class APIStats:
    """API使用统计（每个场景的累计统计）。"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    calls: List[APICallRecord] = field(default_factory=list)


@dataclass
class ConversationTurn:
    """对话轮次记录。"""
    timestamp: str
    role: str  # "assistant" or "user"
    content: str
    action: str  # "diagnose", "execute_commands", "provide_results"


@dataclass
class InvalidResponse:
    """A response that failed strict local validation."""

    error: str
    raw: str = ""


class AIResponseError(RuntimeError):
    """Raised when the API cannot produce a complete structured response."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


AGENT_RESPONSE_SCHEMA = {
    "name": "network_diagnosis_action",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action": {
                "type": "string",
                "enum": ["execute_commands", "diagnose"],
            },
            "commands": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 3,
            },
            "reasoning": {"type": "string"},
            "category": {"type": "string"},
            "root_cause": {"type": "string"},
            "symptoms": {
                "type": "array",
                "items": {"type": "string"},
            },
            "proposed_fix": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "repair_commands": {
                "type": "array",
                "items": {"type": "string"},
            },
            "target_container": {
                "type": "array",
                "items": {"type": "string"},
            },
            "artifact": {"type": "string"},
            "faulty_value": {"type": "string"},
            "expected_value": {"type": "string"},
            "root_causes": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "category": {"type": "string"},
                        "target_container": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "artifact": {"type": "string"},
                        "faulty_value": {"type": "string"},
                        "expected_value": {"type": "string"},
                    },
                    "required": [
                        "category",
                        "target_container",
                        "artifact",
                        "faulty_value",
                        "expected_value",
                    ],
                },
            },
        },
        "required": [
            "action",
            "commands",
            "reasoning",
            "category",
            "root_cause",
            "symptoms",
            "proposed_fix",
            "confidence",
            "repair_commands",
            "target_container",
            "artifact",
            "faulty_value",
            "expected_value",
            "root_causes",
        ],
    },
}


class AIAgent:
    """交互式 AI 诊断代理。"""

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None,
                 max_turns: int = 10, verbose: bool = True):
        """
        初始化 AI 代理。

        Args:
            api_key: AI API 密钥
            api_base: API 基础 URL
            model: 使用的模型
            max_turns: 最大交互轮次
            verbose: 是否输出详细信息
        """
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.api_base = api_base or os.environ.get("AI_API_BASE", "https://api.xiaomimimo.com/v1")
        self.model = model or os.environ.get("AI_MODEL", "mimo-v2.5")
        self.max_turns = max_turns
        self.verbose = verbose
        self._use_json_schema_transport = True
        self.max_completion_tokens = max(
            1024,
            min(
                16000,
                int(os.environ.get("AI_MAX_COMPLETION_TOKENS", "6000")),
            ),
        )
        self.max_consecutive_api_failures = max(
            1,
            min(
                10,
                int(os.environ.get("AI_MAX_CONSECUTIVE_API_FAILURES", "3")),
            ),
        )
        self.max_consecutive_invalid_responses = max(
            1,
            min(
                10,
                int(
                    os.environ.get(
                        "AI_MAX_CONSECUTIVE_INVALID_RESPONSES",
                        "3",
                    )
                ),
            ),
        )
        self.api_retry_base_seconds = max(
            0.1,
            min(
                10.0,
                float(os.environ.get("AI_API_RETRY_BASE_SECONDS", "1")),
            ),
        )

        if not self.api_key:
            raise ValueError("请提供 API 密钥，设置环境变量 AI_API_KEY 或在初始化时传入")

        # API资源监控统计
        self.api_stats = APIStats()
        self._current_api_turn = 0

        # 对话历史
        self.conversation_history: List[Dict] = []
        self.turns_log: List[ConversationTurn] = []
        self.diagnostic_commands_executed: List[str] = []
        self.diagnostic_commands_rejected: List[str] = []

    def log(self, message: str):
        """输出日志。"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_cmd(self, cmd: str, timeout: int = 30) -> str:
        """执行命令并返回输出。"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "命令执行超时"
        except Exception as e:
            return f"命令执行错误: {str(e)}"

    def collect_network_state(self) -> Dict:
        """Collect deterministic observations with complete source metadata."""
        return capture_network_state(self.run_cmd, self.log)

    def format_state_for_prompt(
        self,
        state: Dict,
        executed_commands: Dict[str, str] = None,
        baseline_state: Optional[Dict] = None,
    ) -> str:
        """Format only baseline deltas; command results retain their source."""
        baseline = baseline_state or {"observations": {}}
        prompt = format_state_delta(baseline, state)
        if executed_commands:
            prompt += "\n\n## 已执行的只读诊断命令结果\n\n"
            for command, output in executed_commands.items():
                prompt += (
                    f"### source.command: `{command}`\n"
                    f"```\n{output[:800]}\n```\n\n"
                )
        return prompt

    def get_system_prompt(self, repair_mode: bool = False) -> str:
        """获取系统提示。"""
        prompt = """你是一个网络故障诊断专家。你的任务是分析网络状态信息，检测可能的故障。

## 交互式诊断

你可以通过两种方式响应：

### 1. 请求执行命令（当需要更多信息时）

如果你需要更多信息来做出准确诊断，请返回：
```json
{
    "action": "execute_commands",
    "commands": ["命令1", "命令2"],
    "reasoning": "为什么需要这些命令",
    "category": "",
    "root_cause": "",
    "symptoms": [],
    "proposed_fix": "",
    "confidence": 0,
    "repair_commands": [],
    "target_container": [],
    "artifact": "",
    "faulty_value": "",
    "expected_value": "",
    "root_causes": []
}
```

**常用命令示例：**
- `docker exec <container> birdc show protocols` - 查看 BGP 协议状态
- `docker exec <container> birdc show protocols ospf` - 查看 OSPF 状态
- `docker exec <container> cat /etc/bird/bird.conf` - 查看 BIRD 配置
- `docker exec <container> ip route show` - 查看路由表
- `docker exec <container> cat /etc/resolv.conf` - 查看 DNS 配置
- `docker inspect --format '{{.State.Status}}' <container>` - 检查容器状态
- `docker exec <container> vtysh -c 'show running-config'` - 查看运行配置
- `docker exec <container> ping -c 3 <target>` - 测试连通性

### 2. 返回诊断结果（当有足够信息时）

当你有足够信息做出诊断时，请返回：
```json
{
    "action": "diagnose",
    "category": "故障类别",
    "root_cause": "根本原因",
    "symptoms": ["症状1", "症状2"],
    "proposed_fix": "建议的修复方法",
    "confidence": 0.85,
    "reasoning": "推理过程",
    "repair_commands": [],
    "commands": [],
    "target_container": ["故障目标容器"],
    "artifact": "故障文件、接口、协议或运行状态",
    "faulty_value": "观测到的错误值",
    "expected_value": "由健康基线或同类健康节点推导的正确值",
    "root_causes": [
        {
            "category": "故障类别",
            "target_container": ["故障目标容器"],
            "artifact": "故障资产",
            "faulty_value": "错误值",
            "expected_value": "正确值"
        }
    ]
}
```

## 故障类型

1. **wrong_asn** - 错误 ASN 配置：BGP 显示 "Bad peer AS"
2. **container_not_running** - 容器未运行：容器状态为 exited/stopped
3. **dns_failure** - DNS 故障：resolv.conf 配置错误
4. **missing_bgp_peering** - BGP 对等缺失：BGP peer 被禁用或删除
5. **missing_ospf_adjacency** - OSPF 邻接缺失：OSPF 区域配置错误
6. **wrong_docker_network** - Docker 网络错误：网络连接断开
7. **route_reflector_misconfig** - 路由反射器配置错误
8. **mpls_label_problem** - MPLS 标签问题
9. **ipv6_route_missing** - IPv6 路由缺失
10. **firewall_misconfiguration** - 防火墙配置错误：iptables INPUT 策略阻断流量
11. **frr_route_policy_error** - FRRouting route-map 错误拒绝前缀
12. **bird_route_policy_error** - BIRD export filter 错误拒绝前缀
13. **bind9_config_error** - BIND9 配置语法或选项错误
14. **wireguard_config_error** - WireGuard AllowedIPs/peer 配置错误
15. **netem_packet_loss** - tc/NetEm 注入异常丢包
16. **kea_dhcp_config_error** - Kea DHCP 子网或地址池配置错误
17. **randomized_transit_acl_shadowing** - 随机拓扑中带注释的隐藏
    iptables OUTPUT/FORWARD ACL 阻断指定路径
18. **multiple_faults** - 同一场景存在两个或更多独立根因；必须在
    `root_causes` 中逐项列出，每项使用其具体类别

## 诊断策略

1. 先检查容器状态，确定服务是否运行
2. `iptables -S INPUT` 中明确出现 `-P INPUT DROP` 是
   `firewall_misconfiguration` 的直接证据，优先级高于协议状态推断
3. mini Internet 的单路由器 stub AS 没有内部 OSPF 邻居，OSPF 显示
   `Alone` 是正常状态，不能据此诊断 `missing_ospf_adjacency`
4. 检查 BGP/OSPF 状态时只把明确错误作为故障证据
5. 自动状态只包含健康基线与故障后状态的变化。每条变化都附带采集命令、
   容器和资产来源；必须优先沿变化来源定位，不得用未变化的背景异常代替根因
6. 如有疑问，请求执行更多命令来验证假设
7. 最终诊断必须同时给出目标容器、故障资产、错误值和期望值；
   `root_causes` 必须逐项列出所有独立根因。单故障也必须包含一项
8. 当置信度 >= 0.7 且上述四项都有实时证据时返回诊断结果

诊断时优先使用来源明确的直接证据，但不要依赖 benchmark 文件名、
固定 IP、固定错误值或注释标记猜答案。配置、控制面和数据面证据应互相印证；
健康基线提供正确状态，故障后差异提供错误状态。

**重要：每次只请求执行 2-3 个最相关的命令，避免一次性请求太多。**"""
        if repair_mode:
            prompt += """

## 自主修复评估模式

你不只是诊断，还必须自行生成最终修复命令。确认根因后，在
`diagnose` JSON 的 `repair_commands` 中返回可直接由 shell 执行的命令数组。
这些命令将经过目标容器白名单审查后真实执行；benchmark 不会替你调用标准
修复函数。命令必须：
- 通常使用 `docker exec` 操作经诊断发现的故障容器；如果根因是容器停止，
  可以且必须使用精确的 `docker start <container>`；
- 只修复本场景故障，不停止、删除或重建容器，不修改无关资产；
- 使用非交互命令，并确保配置语法正确；
- `;`、`&&`、管道和重定向不得出现在宿主命令层；需要重定向或组合命令时，
  必须完整封装为 `docker exec <container> sh -c '<payload>'`，确保操作发生在容器内；
- 不把验证命令当作修复命令。
如果没有给出可执行的 `repair_commands`，修复评估将直接判为失败。
修复命令被安全门控拒绝或独立验证失败时，benchmark 会返回结构化原因。
你必须保留已确认的证据，在同一环境中修订命令；不要无依据切换到其他故障。
"""
        return prompt

    def call_ai_api(self, messages: List[Dict]) -> str:
        """Call the API with a strict JSON schema and reject truncation."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": self.max_completion_tokens,
        }
        if self._use_json_schema_transport:
            data["response_format"] = {
                "type": "json_schema",
                "json_schema": AGENT_RESPONSE_SCHEMA,
            }

        self._current_api_turn += 1
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            latency_ms = (time.time() - start_time) * 1000
            response.raise_for_status()
            result = response.json()

            usage = result.get('usage', {})
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            total_tokens = usage.get('total_tokens', 0)

            choice = result["choices"][0]
            finish_reason = choice.get("finish_reason", "")
            message = choice.get("message", {})
            parsed_content = message.get("parsed")
            content = (
                json.dumps(parsed_content, ensure_ascii=False)
                if isinstance(parsed_content, dict)
                else message.get("content", "")
            )
            complete = finish_reason not in ("length", "max_tokens")
            record = APICallRecord(
                turn=self._current_api_turn,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                success=complete,
                error=(
                    ""
                    if complete
                    else f"response truncated: finish_reason={finish_reason}"
                ),
            )

            self.api_stats.total_calls += 1
            if complete:
                self.api_stats.successful_calls += 1
            else:
                self.api_stats.failed_calls += 1
            self.api_stats.total_latency_ms += latency_ms
            self.api_stats.total_prompt_tokens += prompt_tokens
            self.api_stats.total_completion_tokens += completion_tokens
            self.api_stats.total_tokens += total_tokens
            self.api_stats.calls.append(record)

            if not complete:
                raise AIResponseError(
                    "模型响应因 token 上限被截断；请缩短推理和命令，"
                    "仅返回符合 schema 的紧凑 JSON",
                    retryable=True,
                )
            if not content:
                raise AIResponseError(
                    "API 返回空的结构化响应",
                    retryable=True,
                )
            return content
        except AIResponseError:
            raise
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            record = APICallRecord(
                turn=self._current_api_turn,
                latency_ms=latency_ms,
                success=False,
                error=str(e)
            )

            self.api_stats.total_calls += 1
            self.api_stats.failed_calls += 1
            self.api_stats.total_latency_ms += latency_ms
            self.api_stats.calls.append(record)

            status = getattr(getattr(e, "response", None), "status_code", None)
            retryable = (
                isinstance(e, (requests.ConnectionError, requests.Timeout))
                or status == 429
                or (isinstance(status, int) and status >= 500)
                or not isinstance(e, requests.HTTPError)
            )
            raise AIResponseError(
                f"API 调用失败: {e}",
                retryable=retryable,
            ) from e

    def parse_response(
        self, response: str
    ) -> Union[Diagnosis, CommandRequest, InvalidResponse]:
        """
        解析 AI 响应。

        Args:
            response: AI 响应

        Returns:
            Diagnosis 或 CommandRequest
        """
        try:
            # 提取 JSON
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                json_str = response.strip()

            # Some OpenAI-compatible providers occasionally append a second
            # JSON value or explanatory prose even when json_schema is set.
            # Decode exactly the first complete value, then apply the strict
            # local schema and the existing command safety gates to it.
            object_starts = [
                index for index, character in enumerate(json_str)
                if character == "{"
            ]
            if not object_starts:
                raise ValueError("response does not contain a JSON object")
            # MIMO's OpenAI-compatible endpoint can emit literal newlines in
            # JSON strings even with json_schema enabled. ``strict=False``
            # accepts only those JSON control characters; the complete local
            # schema and every command safety gate still run below.
            decoder = json.JSONDecoder(strict=False)
            data = None
            consumed = 0
            object_start = -1
            decode_error = None
            for candidate_start in object_starts:
                try:
                    candidate, candidate_consumed = decoder.raw_decode(
                        json_str[candidate_start:]
                    )
                except json.JSONDecodeError as exc:
                    decode_error = exc
                    continue
                if isinstance(candidate, dict) and "action" in candidate:
                    data = candidate
                    consumed = candidate_consumed
                    object_start = candidate_start
                    break
            if data is None:
                raise decode_error or ValueError(
                    "response does not contain an actionable JSON object"
                )
            trailing = json_str[object_start + consumed:].strip()
            if trailing:
                self.log(
                    "结构化响应包含尾随内容；已隔离首个完整 JSON "
                    f"并忽略 {len(trailing)} 个尾随字符"
                )
            allowed = set(AGENT_RESPONSE_SCHEMA["schema"]["properties"])
            if not isinstance(data, dict):
                raise ValueError("top-level response must be an object")
            extra = sorted(set(data) - allowed)
            if extra:
                raise ValueError(f"schema keys invalid: extra={extra}")

            action = data["action"]
            if action == 'execute_commands':
                commands = data.get("commands")
                if isinstance(commands, str):
                    commands = [commands]
                if (
                    not isinstance(commands, list)
                    or not commands
                    or len(commands) > 3
                    or not all(isinstance(item, str) for item in commands)
                ):
                    raise ValueError(
                        "execute_commands requires 1-3 string commands"
                    )
                return CommandRequest(
                    commands=commands,
                    reasoning=data.get(
                        "reasoning", "model requested read-only diagnostics"
                    ),
                )
            if action != "diagnose":
                raise ValueError(f"unsupported action: {action}")
            diagnosis_required = {
                "category",
                "root_cause",
                "symptoms",
                "proposed_fix",
                "confidence",
                "repair_commands",
                "target_container",
                "artifact",
                "faulty_value",
                "expected_value",
                "root_causes",
            }
            missing = sorted(diagnosis_required - set(data))
            if missing:
                raise ValueError(
                    f"diagnose schema keys missing: {missing}"
                )
            target_container = data["target_container"]
            repair_commands = data["repair_commands"]
            root_causes = data["root_causes"]
            if not isinstance(target_container, list) or not all(
                isinstance(item, str) for item in target_container
            ):
                raise ValueError("target_container must be a string array")
            if not isinstance(repair_commands, list) or not all(
                isinstance(item, str) for item in repair_commands
            ):
                raise ValueError("repair_commands must be a string array")
            root_keys = {
                "category",
                "target_container",
                "artifact",
                "faulty_value",
                "expected_value",
            }
            if not isinstance(root_causes, list) or not root_causes:
                raise ValueError("diagnose requires at least one root cause")
            for item in root_causes:
                if not isinstance(item, dict) or set(item) != root_keys:
                    raise ValueError("root_causes item does not match schema")
                if not isinstance(item["target_container"], list):
                    raise ValueError(
                        "root cause target_container must be an array"
                    )
                if (
                    not item["target_container"]
                    or not all(
                        isinstance(target, str) and target.strip()
                        for target in item["target_container"]
                    )
                    or not item["category"].strip()
                    or not item["artifact"].strip()
                    or not item["faulty_value"].strip()
                    or not item["expected_value"].strip()
                ):
                    raise ValueError(
                        "root cause fields must contain attributed evidence"
                    )
            confidence = data["confidence"]
            if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise ValueError("confidence must be between 0 and 1")
            return Diagnosis(
                category=data["category"],
                root_cause=data["root_cause"],
                symptoms=data["symptoms"],
                proposed_fix=data["proposed_fix"],
                confidence=float(confidence),
                reasoning=data.get("reasoning", data["root_cause"]),
                repair_commands=repair_commands,
                target_container=target_container,
                artifact=data["artifact"],
                faulty_value=data["faulty_value"],
                expected_value=data["expected_value"],
                root_causes=root_causes,
            )
        except Exception as e:
            if self._use_json_schema_transport:
                self._use_json_schema_transport = False
                self.log(
                    "结构化传输未产生完整对象；后续请求停用 provider "
                    "response_format，继续使用 prompt + 本地严格 schema"
                )
            self.log(
                f"解析响应失败: {e}; 原始响应片段={response[:500]!r}"
            )
            return InvalidResponse(error=str(e), raw=response[:1000])

    @staticmethod
    def is_read_only_diagnostic_command(command: str) -> bool:
        """Parse shell quoting and allow only auditable read-only commands."""
        if not isinstance(command, str) or not command.strip():
            return False
        if "\n" in command or "\r" in command:
            return False
        if "`" in command or "$(" in command:
            return False
        try:
            lexer = shlex.shlex(
                command,
                posix=True,
                punctuation_chars=";&|<>",
            )
            lexer.whitespace_split = True
            lexer.commenters = ""
            tokens = list(lexer)
        except ValueError:
            return False
        tokens = AIAgent._remove_safe_read_redirections(tokens)
        if tokens is None:
            return False
        segments: List[List[str]] = [[]]
        for token in tokens:
            if token == "|":
                segments.append([])
            elif token in (";", "&&", "||", "&", "<", "<<", ">", ">>", ">&"):
                return False
            else:
                segments[-1].append(token)
        if any(not segment for segment in segments):
            return False
        if any(
            not AIAgent._is_safe_filter(segment)
            for segment in segments[1:]
        ):
            return False
        return AIAgent._is_read_only_primary(segments[0])

    @staticmethod
    def _remove_safe_read_redirections(
        tokens: List[str],
    ) -> Optional[List[str]]:
        """Remove only stderr/stdout suppression redirections."""
        cleaned: List[str] = []
        index = 0
        while index < len(tokens):
            if (
                index + 2 < len(tokens)
                and tokens[index] in ("1", "2")
                and tokens[index + 1] == ">"
                and tokens[index + 2] == "/dev/null"
            ):
                index += 3
                continue
            if (
                index + 2 < len(tokens)
                and tokens[index] == "2"
                and tokens[index + 1] == ">&"
                and tokens[index + 2] == "1"
            ):
                index += 3
                continue
            cleaned.append(tokens[index])
            index += 1
        return cleaned

    @staticmethod
    def _is_safe_filter(tokens: List[str]) -> bool:
        if not tokens:
            return False
        if tokens[0] not in ("grep", "head", "tail", "awk", "sed", "wc"):
            return False
        joined = " ".join(tokens).lower()
        return not any(
            marker in joined
            for marker in ("system(", "--in-place", " -i", "tee ")
        )

    @staticmethod
    def _is_read_only_primary(tokens: List[str]) -> bool:
        if len(tokens) < 2 or tokens[0] != "docker":
            return False
        if tokens[1] in ("ps", "inspect", "logs"):
            return True
        if tokens[1:3] in (["network", "ls"], ["network", "inspect"]):
            return True
        if tokens[1] != "exec":
            return False

        index = 2
        while index < len(tokens) and tokens[index].startswith("-"):
            index += 1
        if index >= len(tokens):
            return False
        index += 1  # scoped container name
        inner_tokens = tokens[index:]
        if not inner_tokens:
            return False
        if inner_tokens[:2] in (["sh", "-c"], ["bash", "-c"]):
            if len(inner_tokens) != 3:
                return False
            try:
                lexer = shlex.shlex(
                    inner_tokens[2],
                    posix=True,
                    punctuation_chars=";&|<>",
                )
                lexer.whitespace_split = True
                lexer.commenters = ""
                payload_tokens = list(lexer)
            except ValueError:
                return False
            payload_tokens = AIAgent._remove_safe_read_redirections(
                payload_tokens
            )
            if payload_tokens is None:
                return False
            segments: List[List[str]] = [[]]
            for token in payload_tokens:
                if token == "|":
                    segments.append([])
                elif token in (
                    ";", "&&", "||", "&", "<", "<<", ">", ">>", ">&"
                ):
                    return False
                else:
                    segments[-1].append(token)
            return (
                bool(segments[0])
                and AIAgent._is_read_only_inner(segments[0])
                and all(
                    AIAgent._is_safe_filter(segment)
                    for segment in segments[1:]
                )
            )
        return AIAgent._is_read_only_inner(inner_tokens)

    @staticmethod
    def _is_read_only_inner(tokens: List[str]) -> bool:
        if not tokens:
            return False
        inner = shlex.join(tokens)
        if tokens[0] == "find" and any(
            item in tokens for item in ("-delete", "-exec", "-execdir", "-ok")
        ):
            return False
        container_read_only = (
            r"(?:cat|grep|head|tail|awk|wc|ls|ps|find|traceroute|sysctl)\b",
            r"sed\s+-n\b",
            r"birdc\s+(?:show|status)\b",
            r"bird\s+-p\b",
            r"ip\s+(?:-6\s+)?(?:route|addr|address|link|neigh)\s+(?:show|list)\b",
            r"ping\b",
            r"(?:dig|nslookup|host)\b",
            r"wg\s+show\b",
            r"tc\s+(?:-[A-Za-z]+\s+)*(?:qdisc|class|filter)\s+show\b",
            r"iptables\s+-(?:S|L)\b",
            r"named-checkconf\b",
            r"kea-dhcp4\s+-t\b",
            r"vtysh\s+-c\s+['\"]show\b",
        )
        return any(re.match(pattern, inner) for pattern in container_read_only)

    @staticmethod
    def has_mutating_repair_command(commands: List[str]) -> bool:
        """Reject empty or purely observational final repair plans."""
        mutation_patterns = (
            r"docker\s+(?:start|restart|network\s+(?:connect|disconnect))\b",
            r"docker\s+exec\b.*\b(?:sed\s+-i|tee|printf|echo|cp|mv|rm|touch|truncate)\b",
            r"docker\s+exec\b.*\b(?:birdc\s+configure|systemctl|service)\b",
            r"docker\s+exec\b.*\biptables\s+(?:-[AIDFPR]|--policy)\b",
            r"docker\s+exec\b.*\bip\s+(?:route|link|addr)\s+(?:add|del|replace|set)\b",
            r"docker\s+exec\b.*\btc\s+qdisc\s+(?:add|del|change|replace)\b",
            r"docker\s+exec\b.*\bwg\s+set\b",
        )
        return any(
            isinstance(command, str)
            and any(re.search(pattern, command) for pattern in mutation_patterns)
            for command in commands
        )

    def execute_commands(self, commands: List[str]) -> Dict[str, str]:
        """
        执行命令列表并返回结果。

        Args:
            commands: 命令列表

        Returns:
            命令输出字典
        """
        results = {}
        for cmd in commands:
            if not self.is_read_only_diagnostic_command(cmd):
                self.log(f"拒绝非只读诊断命令: {str(cmd)[:80]}")
                self.diagnostic_commands_rejected.append(str(cmd))
                results[str(cmd)] = "REJECTED: diagnostic commands must be read-only"
                continue
            self.log(f"执行命令: {cmd[:80]}...")
            output = self.run_cmd(cmd)
            results[cmd] = output
            self.diagnostic_commands_executed.append(cmd)
        return results

    def diagnose_interactive(
        self,
        task_context: str = "",
        repair_mode: bool = False,
        baseline_state: Optional[Dict] = None,
        current_state: Optional[Dict] = None,
        repair_attempt_handler: Optional[
            Callable[[Diagnosis], Dict[str, Any]]
        ] = None,
    ) -> Diagnosis:
        """
        执行交互式诊断。

        Returns:
            诊断结果
        """
        self.log("开始交互式诊断...")

        state = current_state or self.collect_network_state()
        initial_prompt = self.format_state_for_prompt(
            state,
            baseline_state=baseline_state,
        )

        # 初始化对话
        messages = [
            {
                "role": "system",
                "content": self.get_system_prompt(repair_mode=repair_mode),
            },
            {
                "role": "user",
                "content": (
                    f"请诊断以下网络故障：\n\n{task_context}\n\n"
                    f"{initial_prompt}"
                ),
            }
        ]

        # 记录已执行的命令
        executed_commands = {}
        last_diagnosis: Optional[Diagnosis] = None
        consecutive_api_failures = 0
        consecutive_invalid_responses = 0
        terminal_failure = ""

        # 交互循环
        for turn in range(self.max_turns):
            self.log(f"--- 第 {turn + 1} 轮 ---")

            # 调用 AI
            self.log("调用 AI API...")
            try:
                response = self.call_ai_api(messages)
            except AIResponseError as exc:
                self.log(str(exc))
                consecutive_api_failures += 1
                if (
                    not exc.retryable
                    or consecutive_api_failures
                    >= self.max_consecutive_api_failures
                ):
                    terminal_failure = (
                        "API 熔断：连续 "
                        f"{consecutive_api_failures} 次调用失败；最后错误: {exc}"
                    )
                    self.log(terminal_failure)
                    break
                delay = min(
                    10.0,
                    self.api_retry_base_seconds
                    * (2 ** (consecutive_api_failures - 1)),
                )
                feedback = (
                    "上一次 API 响应不可用："
                    f"{exc}。请缩短内容，只返回严格 schema JSON；"
                    "不要使用 Markdown 代码块。"
                )
                messages.append({"role": "user", "content": feedback})
                self.turns_log.append(
                    ConversationTurn(
                        timestamp=datetime.now().isoformat(),
                        role="user",
                        content=feedback,
                        action="structured_response_retry",
                    )
                )
                self.log(f"{delay:.1f}s 后重试 API")
                time.sleep(delay)
                continue
            consecutive_api_failures = 0

            # 记录 AI 响应
            self.turns_log.append(ConversationTurn(
                timestamp=datetime.now().isoformat(),
                role="assistant",
                content=response,
                action="unknown"
            ))

            # 解析响应
            parsed = self.parse_response(response)

            if isinstance(parsed, InvalidResponse):
                consecutive_invalid_responses += 1
                self.turns_log[-1].action = "invalid_response"
                if (
                    consecutive_invalid_responses
                    >= self.max_consecutive_invalid_responses
                ):
                    terminal_failure = (
                        "结构化响应熔断：连续 "
                        f"{consecutive_invalid_responses} 次未通过本地 schema；"
                        f"最后错误: {parsed.error}"
                    )
                    self.log(terminal_failure)
                    break
                feedback = (
                    "响应未通过严格 JSON schema 本地校验："
                    f"{parsed.error}。请仅返回 schema 要求的 JSON 对象，"
                    "所有字段都必须存在且不得增加字段。"
                )
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": feedback})
                continue
            consecutive_invalid_responses = 0

            if isinstance(parsed, Diagnosis):
                last_diagnosis = parsed
                if repair_mode and not self.has_mutating_repair_command(
                    parsed.repair_commands
                ):
                    self.log("最终结果缺少状态变更修复命令，要求 Agent 继续")
                    self.turns_log[-1].action = "incomplete_repair"
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "该结果中的 repair_commands 为空或只有查询/验证命令，"
                            "不能改变故障状态。请继续只读诊断；确认根因后返回至少一条"
                            "精确、可执行、能改变故障状态的修复命令。不要把 docker ps、"
                            "inspect、show、cat、grep 等查询命令放入 repair_commands。"
                        ),
                    })
                    continue
                if repair_mode and (
                    not parsed.target_container
                    or not parsed.artifact.strip()
                    or not parsed.faulty_value.strip()
                    or not parsed.expected_value.strip()
                    or not parsed.root_causes
                ):
                    self.log("最终结果缺少结构化根因字段，要求 Agent 继续")
                    self.turns_log[-1].action = "incomplete_root_cause"
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": (
                            "最终诊断必须基于实时证据完整填写 target_container、"
                            "artifact、faulty_value、expected_value。"
                            "root_causes 必须逐项包含每个独立根因；单故障也需一项。"
                            "请继续只读诊断或补全精确字段后重新返回。"
                        ),
                    })
                    continue

                if repair_mode and repair_attempt_handler is not None:
                    outcome = repair_attempt_handler(parsed)
                    if outcome.get("verified"):
                        self.log(
                            f"诊断与修复完成: {parsed.category} "
                            f"(置信度: {parsed.confidence:.0%})"
                        )
                        self.turns_log[-1].action = "repair_verified"
                        return parsed
                    self.log("修复尝试未通过，反馈给 Agent 继续修订")
                    self.turns_log[-1].action = "repair_retry"
                    feedback = {
                        "repair_attempt": "failed",
                        "rejections": outcome.get("rejections", []),
                        "executions": outcome.get("executions", []),
                        "verification_output": outcome.get(
                            "verification_output", ""
                        )[:1500],
                        "instruction": (
                            "保持已确认根因，在同一隔离环境中继续只读诊断，"
                            "然后提交修订后的完整诊断和 repair_commands。"
                        ),
                    }
                    messages.append({"role": "assistant", "content": response})
                    messages.append({
                        "role": "user",
                        "content": json.dumps(
                            feedback,
                            ensure_ascii=False,
                            indent=2,
                        ),
                    })
                    continue
                # 诊断完成
                self.log(f"诊断完成: {parsed.category} (置信度: {parsed.confidence:.0%})")

                # 记录最终动作
                self.turns_log[-1].action = "diagnose"

                return parsed

            elif isinstance(parsed, CommandRequest):
                # AI 请求执行命令
                self.log(f"AI 请求执行 {len(parsed.commands)} 个命令")
                self.log(f"原因: {parsed.reasoning}")

                # 记录动作
                self.turns_log[-1].action = "execute_commands"

                # 执行命令
                results = self.execute_commands(parsed.commands)
                executed_commands.update(results)

                # 格式化结果
                results_text = "## 命令执行结果\n\n"
                for cmd, output in results.items():
                    results_text += f"### `{cmd}`\n```\n{output[:500]}\n```\n\n"

                # 添加到对话历史
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": results_text})

                # 记录
                self.turns_log.append(ConversationTurn(
                    timestamp=datetime.now().isoformat(),
                    role="user",
                    content=results_text,
                    action="provide_results"
                ))

        # 超过最大轮次
        if terminal_failure:
            self.log(f"诊断提前终止: {terminal_failure}")
        else:
            self.log(f"达到最大轮次 {self.max_turns}")
        if last_diagnosis is not None:
            return last_diagnosis
        return Diagnosis(
            category='unknown',
            root_cause=terminal_failure or '诊断超时',
            symptoms=[],
            proposed_fix=(
                '恢复 API 可用性后重试'
                if terminal_failure
                else '增加 max_turns 或简化诊断'
            ),
            confidence=0.0,
            reasoning=(
                terminal_failure
                or f'在 {self.max_turns} 轮交互后未能完成诊断'
            ),
            target_container=[],
            artifact="",
            faulty_value="",
            expected_value="",
            root_causes=[],
        )

    def diagnose_and_fix(self) -> Dict:
        """
        执行诊断并返回修复建议。

        Returns:
            诊断和修复信息
        """
        diagnosis = self.diagnose_interactive()

        return {
            "diagnosis": {
                "category": diagnosis.category,
                "root_cause": diagnosis.root_cause,
                "symptoms": diagnosis.symptoms,
                "proposed_fix": diagnosis.proposed_fix,
                "confidence": diagnosis.confidence,
                "reasoning": diagnosis.reasoning,
                "root_causes": diagnosis.root_causes,
            },
            "turns": len(self.turns_log),
            "commands_executed": len([t for t in self.turns_log if t.action == "execute_commands"]),
            "fix_applied": False
        }

    def get_conversation_log(self) -> List[Dict]:
        """获取对话日志。"""
        return [
            {
                "timestamp": t.timestamp,
                "role": t.role,
                "action": t.action,
                "content_preview": t.content[:200] + "..." if len(t.content) > 200 else t.content
            }
            for t in self.turns_log
        ]


def main():
    """主函数。"""
    import sys

    # 检查 API 密钥
    if not os.environ.get("AI_API_KEY"):
        print("错误: 请设置环境变量 AI_API_KEY")
        print("示例: export AI_API_KEY='your-api-key'")
        sys.exit(1)

    # 创建代理
    agent = AIAgent(max_turns=10, verbose=True)

    # 执行诊断
    print("=" * 60)
    print("交互式 AI 诊断代理")
    print("=" * 60)

    result = agent.diagnose_and_fix()

    # 输出结果
    print("\n" + "=" * 60)
    print("诊断结果")
    print("=" * 60)
    print(f"类别: {result['diagnosis']['category']}")
    print(f"根本原因: {result['diagnosis']['root_cause']}")
    print(f"置信度: {result['diagnosis']['confidence']:.0%}")
    print(f"症状: {', '.join(result['diagnosis']['symptoms'])}")
    print(f"建议修复: {result['diagnosis']['proposed_fix']}")
    print(f"推理过程: {result['diagnosis']['reasoning']}")
    print(f"\n交互轮次: {result['turns']}")
    print(f"执行命令数: {result['commands_executed']}")
    print("=" * 60)

    # 输出对话日志
    print("\n" + "=" * 60)
    print("对话日志")
    print("=" * 60)
    for entry in agent.get_conversation_log():
        print(f"[{entry['timestamp']}] {entry['role']} ({entry['action']})")
        print(f"  {entry['content_preview']}")
        print()


if __name__ == "__main__":
    main()

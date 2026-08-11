#!/usr/bin/env python3
"""
改进的 AI 诊断代理 - 修复数据收集和解析问题。
"""

import os
import json
import subprocess
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Diagnosis:
    """诊断结果。"""
    category: str
    root_cause: str
    symptoms: List[str]
    proposed_fix: str
    confidence: float
    reasoning: str


class ImprovedAIAgent:
    """改进的 AI 诊断代理。"""

    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        """初始化 AI 代理。"""
        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.api_base = api_base or os.environ.get("AI_API_BASE", "https://api.xiaomimimo.com/v1")
        self.model = model or os.environ.get("AI_MODEL", "mimo-v2.5")

        if not self.api_key:
            raise ValueError("请提供 API 密钥")

    def run_cmd(self, cmd: str) -> str:
        """执行命令并返回输出。"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "命令执行超时"
        except Exception as e:
            return f"命令执行错误: {str(e)}"

    def collect_network_state(self) -> Dict:
        """收集网络状态信息 - 改进版本。"""
        state = {}

        # 1. 获取所有容器（不限制数量）
        containers = self.run_cmd("docker ps --format '{{.Names}}'").strip().split('\n')
        state['containers'] = [c.strip() for c in containers if c.strip()]

        # 2. 检查容器状态（检查所有容器）
        state['container_status'] = {}
        for container in state['containers']:
            status = self.run_cmd(f"docker inspect --format '{{{{.State.Status}}}}' {container}").strip()
            state['container_status'][container] = status

        # 3. 检查 BGP 状态（检查所有路由器）
        state['bgp_status'] = {}
        routers = [c for c in state['containers'] if 'router' in c.lower() or 'brd' in c.lower()]
        for router in routers:
            bgp = self.run_cmd(f"docker exec {router} birdc show protocols 2>/dev/null")
            if 'BIRD' in bgp:
                state['bgp_status'][router] = bgp[:1000]  # 增加长度限制

        # 4. 检查 OSPF 状态（检查所有路由器）
        state['ospf_status'] = {}
        for router in routers:
            ospf = self.run_cmd(f"docker exec {router} birdc show protocols ospf 2>/dev/null")
            if 'ospf' in ospf.lower():
                state['ospf_status'][router] = ospf[:500]

        # 5. 检查网络连接（检查所有路由器）
        state['network_connectivity'] = {}
        for router in routers:
            networks = self.run_cmd(f"docker inspect --format '{{{{json .NetworkSettings.Networks}}}}' {router}")
            state['network_connectivity'][router] = networks[:300]

        # 6. 检查 DNS 配置（检查所有主机）
        state['dns_config'] = {}
        hosts = [c for c in state['containers'] if 'host' in c.lower()]
        for host in hosts:
            dns = self.run_cmd(f"docker exec {host} cat /etc/resolv.conf 2>/dev/null")
            state['dns_config'][host] = dns[:300]

        # 7. 检查 IPv6 配置（新增）
        state['ipv6_status'] = {}
        for router in routers[:5]:  # 检查前 5 个路由器
            ipv6 = self.run_cmd(f"docker exec {router} ip -6 route show 2>/dev/null")
            if ipv6.strip():
                state['ipv6_status'][router] = ipv6[:300]

        # 8. 检查 MPLS 状态（新增）
        state['mpls_status'] = {}
        for router in routers[:3]:
            mpls = self.run_cmd(f"docker exec {router} vtysh -c 'show mpls ldp neighbor' 2>/dev/null")
            if mpls.strip():
                state['mpls_status'][router] = mpls[:300]

        return state

    def format_state_for_prompt(self, state: Dict) -> str:
        """将网络状态格式化为提示信息 - 简化版本。"""
        prompt = "网络状态信息:\n\n"

        # 容器状态（只显示异常的）
        prompt += "## 异常容器\n"
        for container, status in state.get('container_status', {}).items():
            if status != 'running':
                prompt += f"- {container}: {status}\n"
        prompt += "\n"

        # BGP 状态（只显示有问题的）
        prompt += "## BGP 状态\n"
        for router, bgp in state.get('bgp_status', {}).items():
            if 'Bad peer AS' in bgp or 'Idle' in bgp or 'Active' in bgp:
                prompt += f"### {router}\n```\n{bgp}\n```\n"
        prompt += "\n"

        # OSPF 状态
        prompt += "## OSPF 状态\n"
        for router, ospf in state.get('ospf_status', {}).items():
            prompt += f"### {router}\n```\n{ospf}\n```\n"
        prompt += "\n"

        # 网络连接（只显示断开的）
        prompt += "## 网络连接\n"
        for router, networks in state.get('network_connectivity', {}).items():
            if 'output_net_ix' not in networks:
                prompt += f"### {router}\n```\n{networks}\n```\n"
        prompt += "\n"

        # DNS 配置（只显示错误的）
        prompt += "## DNS 配置\n"
        for host, dns in state.get('dns_config', {}).items():
            if '192.0.2.1' in dns:
                prompt += f"### {host}\n```\n{dns}\n```\n"
        prompt += "\n"

        # IPv6 状态
        prompt += "## IPv6 状态\n"
        for router, ipv6 in state.get('ipv6_status', {}).items():
            prompt += f"### {router}\n```\n{ipv6}\n```\n"
        prompt += "\n"

        # MPLS 状态
        prompt += "## MPLS 状态\n"
        for router, mpls in state.get('mpls_status', {}).items():
            prompt += f"### {router}\n```\n{mpls}\n```\n"

        return prompt

    def call_ai_api(self, prompt: str) -> str:
        """调用 AI API - 改进版本。"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 简化系统提示词
        system_prompt = """你是网络故障诊断专家。分析网络状态，检测故障。

故障类型:
1. wrong_asn: BGP 显示 "Bad peer AS"
2. service_not_running: 容器状态为 exited/stopped
3. dns_failure: DNS 配置错误 (192.0.2.1)
4. missing_bgp_peering: BGP 协议被注释
5. missing_ospf_adjacency: OSPF 区域错误 (area 99)
6. wrong_docker_network: 网络连接断开
7. route_reflector_misconfig: 路由反射器配置错误
8. mpls_label_problem: MPLS 未启用
9. ipv6_route_missing: IPv6 路由缺失
10. firewall_misconfiguration: iptables INPUT 策略阻断流量

请以 JSON 格式返回:
{"category": "故障类别", "root_cause": "原因", "symptoms": ["症状"], "proposed_fix": "修复方法", "confidence": 0.85, "reasoning": "推理"}"""

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1500  # 减少 token 数量
        }

        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=60  # 减少超时时间
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            return json.dumps({
                "category": "unknown",
                "root_cause": f"API 调用失败: {str(e)}",
                "symptoms": [],
                "proposed_fix": "检查 API 配置",
                "confidence": 0.0,
                "reasoning": str(e)
            })

    def parse_diagnosis(self, response: str) -> Diagnosis:
        """解析 AI 响应 - 简化版本。"""
        try:
            # 尝试提取 JSON
            if '```json' in response:
                json_str = response.split('```json')[1].split('```')[0].strip()
            elif '```' in response:
                json_str = response.split('```')[1].split('```')[0].strip()
            else:
                # 尝试直接解析整个响应
                json_str = response.strip()

            # 尝试解析 JSON
            data = json.loads(json_str)

            return Diagnosis(
                category=data.get('category', 'unknown'),
                root_cause=data.get('root_cause', '未知'),
                symptoms=data.get('symptoms', []),
                proposed_fix=data.get('proposed_fix', '无'),
                confidence=data.get('confidence', 0.0),
                reasoning=data.get('reasoning', '')
            )
        except json.JSONDecodeError as e:
            # 尝试修复 JSON
            try:
                # 移除不完整的部分
                import re
                # 找到最后一个完整的 JSON 对象
                match = re.search(r'\{[^{}]*\}', json_str)
                if match:
                    json_str = match.group()
                    data = json.loads(json_str)
                    return Diagnosis(
                        category=data.get('category', 'unknown'),
                        root_cause=data.get('root_cause', '未知'),
                        symptoms=data.get('symptoms', []),
                        proposed_fix=data.get('proposed_fix', '无'),
                        confidence=data.get('confidence', 0.0),
                        reasoning=data.get('reasoning', '')
                    )
            except:
                pass

            # 如果都失败，返回 unknown
            return Diagnosis(
                category='unknown',
                root_cause=f'解析失败: {str(e)}',
                symptoms=[],
                proposed_fix='无',
                confidence=0.0,
                reasoning=response[:200]
            )

    def diagnose(self) -> Diagnosis:
        """执行诊断。"""
        print("收集网络状态...")
        state = self.collect_network_state()

        print("格式化提示信息...")
        prompt = self.format_state_for_prompt(state)

        print("调用 AI API...")
        response = self.call_ai_api(prompt)

        print("解析诊断结果...")
        diagnosis = self.parse_diagnosis(response)

        return diagnosis

    def diagnose_and_fix(self) -> Dict:
        """执行诊断并返回修复建议。"""
        diagnosis = self.diagnose()

        return {
            "diagnosis": {
                "category": diagnosis.category,
                "root_cause": diagnosis.root_cause,
                "symptoms": diagnosis.symptoms,
                "proposed_fix": diagnosis.proposed_fix,
                "confidence": diagnosis.confidence,
                "reasoning": diagnosis.reasoning
            },
            "fix_applied": False,
            "commands": 0
        }


def main():
    """主函数。"""
    import sys

    # 检查 API 密钥
    if not os.environ.get("AI_API_KEY"):
        print("错误: 请设置环境变量 AI_API_KEY")
        sys.exit(1)

    # 创建代理
    agent = ImprovedAIAgent()

    # 执行诊断
    print("开始诊断...")
    result = agent.diagnose_and_fix()

    # 输出结果
    print("\n" + "="*60)
    print("诊断结果")
    print("="*60)
    print(f"类别: {result['diagnosis']['category']}")
    print(f"根本原因: {result['diagnosis']['root_cause']}")
    print(f"置信度: {result['diagnosis']['confidence']:.0%}")
    print(f"症状: {', '.join(result['diagnosis']['symptoms'])}")
    print(f"建议修复: {result['diagnosis']['proposed_fix']}")
    print(f"推理过程: {result['diagnosis']['reasoning']}")
    print("="*60)


if __name__ == "__main__":
    main()

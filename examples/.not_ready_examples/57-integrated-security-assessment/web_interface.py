#!/usr/bin/env python3
"""57 综合安全评估实验 - 集成控制台

该 Web 服务用于：
1. 快速查看 Gophish / PentestAgent / OpenBAS / Seed 邮件系统的运行状态。
2. 展示 Seed-Emulator 网络叠加配置与项目文档。
3. 为后续真实工具集成预留 REST API 扩展点。
"""

from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request, send_from_directory

try:  # 可选依赖
    import requests
except Exception:  # pragma: no cover - 环境缺少 requests 时退化
    requests = None  # type: ignore[assignment]

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
DOCS_DIR = BASE_DIR / "docs"
TOOLS_DIR = BASE_DIR / "external_tools"

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("integration-console")

app = Flask(__name__)
app.secret_key = "seed_integrated_security_2025"


@dataclass
class ServiceStatus:
    key: str
    display_name: str
    description: str
    host: str
    port: int
    status: str = "unknown"
    status_label: str = "未知"
    extra: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    health_message: Optional[str] = None
    container_name: Optional[str] = None
    container_status: Optional[str] = None
    healthcheck: Optional[Dict[str, Any]] = None
    detail_config: Optional[Dict[str, Any]] = None

    @property
    def address(self) -> str:
        scheme = "https" if self.port in (3333, 443, 8443) else "http"
        return f"{scheme}://{self.host}:{self.port}"


class IntegrationMonitor:
    """管理外部工具与 Seed 服务的状态检查。"""

    def __init__(self) -> None:
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        config_path = CONFIG_DIR / "integration_config.json"
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8"))
                logger.info("Loaded integration_config.json")
                return data
            except Exception as exc:
                logger.warning("加载 integration_config.json 失败: %s", exc)
        # 默认配置
        return {
            "services": [
                {
                    "key": "gophish",
                    "display_name": "Gophish 钓鱼平台",
                    "description": "真实钓鱼活动管理与模板生成",
                    "host": "localhost",
                    "port": 3333,
                    "actions": [
                        {"label": "打开控制台", "href": "https://localhost:3333", "external": True},
                        {"label": "查看 README", "href": "/external/gophish/README", "external": False},
                    ],
                },
                {
                    "key": "pentestagent",
                    "display_name": "PentestAgent 渗透测试编排",
                    "description": "LLM 驱动的情报收集与漏洞利用",
                    "host": "localhost",
                    "port": 5001,
                    "extra": "默认使用 Docker Compose，端口可按需修改",
                    "actions": [
                        {"label": "项目说明", "href": "https://github.com/nbshenxm/pentest-agent", "external": True},
                    ],
                },
                {
                    "key": "openbas",
                    "display_name": "OpenBAS 演练调度平台",
                    "description": "攻防演练任务编排与指标追踪",
                    "host": "localhost",
                    "port": 8443,
                    "actions": [
                        {"label": "登录 Web 控制台", "href": "https://localhost:8443", "external": True},
                    ],
                },
                {
                    "key": "seed_email_29",
                    "display_name": "29 基础邮件系统",
                    "description": "Seed-Emulator 基础邮件实验环境",
                    "host": "localhost",
                    "port": 5000,
                    "actions": [
                        {"label": "访问 Web UI", "href": "http://localhost:5000", "external": True},
                    ],
                },
                {
                    "key": "seed_email_29_1",
                    "display_name": "29-1 真实网络邮件系统",
                    "description": "多服务商仿真与跨域路由",
                    "host": "localhost",
                    "port": 5001,
                },
                {
                    "key": "seed_email_30",
                    "display_name": "30 AI 钓鱼检测系统",
                    "description": "AI 辅助钓鱼检测与生成",
                    "host": "localhost",
                    "port": 5002,
                },
                {
                    "key": "seed_email_31",
                    "display_name": "31 高级 APT 仿真系统",
                    "description": "高级对抗演练平台",
                    "host": "localhost",
                    "port": 5003,
                },
            ]
        }

    def list_services(self) -> List[ServiceStatus]:
        services: List[ServiceStatus] = []
        for item in self.config.get("services", []):
            status = ServiceStatus(
                key=item["key"],
                display_name=item["display_name"],
                description=item.get("description", ""),
                host=item.get("host", "localhost"),
                port=int(item.get("port", 0)),
                extra=item.get("extra"),
                actions=item.get("actions", []),
                container_name=item.get("container_name"),
                healthcheck=item.get("healthcheck"),
                detail_config=item.get("detail"),
            )
            probe = self._probe_service(item)
            status.status = probe.get("status", "unknown")
            status.status_label = probe.get("status_label", "未知")
            status.container_status = probe.get("container_status")
            status.health_message = probe.get("health_message")
            services.append(status)
        return services

    def _probe_service(self, service: Dict[str, Any]) -> Dict[str, Optional[str]]:
        host = service.get("host", "localhost")
        port = int(service.get("port", 0))
        container_name = service.get("container_name")
        result = {
            "status": "unknown",
            "status_label": "未配置",
            "container_status": None,
            "health_message": None,
        }

        if container_name:
            result["container_status"] = self._check_container_status(container_name)

        if port == 0 and not service.get("healthcheck"):
            return result

        health_status, health_label, health_message = self._perform_healthcheck(
            host,
            port,
            service.get("healthcheck"),
        )
        result.update({
            "status": health_status,
            "status_label": health_label,
            "health_message": health_message,
        })
        return result

    def _perform_healthcheck(
        self,
        host: str,
        port: int,
        healthcheck: Optional[Dict[str, Any]],
    ) -> tuple[str, str, Optional[str]]:
        hc = healthcheck or {}
        hc_type = hc.get("type", "tcp").lower()

        if hc_type == "http" and requests is not None:
            url = hc.get("url") or (f"http://{host}:{port}" if port else None)
            method = hc.get("method", "GET").upper()
            verify = hc.get("verify", True)
            headers = hc.get("headers")
            timeout = float(hc.get("timeout", 3))
            if url:
                try:
                    response = requests.request(  # type: ignore[call-arg]
                        method,
                        url,
                        timeout=timeout,
                        headers=headers,
                        verify=verify,
                    )
                    if response.ok:
                        return "running", "运行中", f"HTTP {response.status_code}"
                    return "error", f"HTTP {response.status_code}", None
                except Exception as exc:  # pragma: no cover
                    logger.debug("HTTP healthcheck failed for %s: %s", host, exc)
                    return "error", "健康检查失败", str(exc)

        # 默认使用 TCP 检测
        if port and self._check_tcp_port(host, port):
            return "running", "运行中", None
        return "stopped", "未就绪", None

    @staticmethod
    def _check_container_status(container_name: str) -> Optional[str]:
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3,
            )
        except FileNotFoundError:  # docker 未安装
            return None
        except subprocess.SubprocessError:
            return "error"

        if result.returncode == 0:
            return (result.stdout or "").strip() or "unknown"
        return "not found"

    @staticmethod
    def _check_tcp_port(host: str, port: int) -> bool:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        finally:
            sock.close()

    # ---- 外部工具细节 ---- #

    def fetch_gophish_campaigns(self, detail_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        if requests is None:
            return []

        api_key: Optional[str] = None
        api_key_env = detail_cfg.get("api_key_env")
        if api_key_env:
            api_key = os.environ.get(api_key_env)

        config_candidates = []
        config_path = detail_cfg.get("config_path")
        if config_path:
            config_candidates.append(BASE_DIR / config_path)
        config_candidates.extend(
            [
                TOOLS_DIR / "gophish" / "config.json",
                TOOLS_DIR / "gophish" / "config" / "config.json",
            ]
        )

        admin_endpoint = detail_cfg.get("base_url", "https://localhost:3333")

        for path in config_candidates:
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    api_key = api_key or data.get("api_key")
                except Exception as exc:  # pragma: no cover
                    logger.debug("读取 Gophish 配置失败 %s: %s", path, exc)
                    continue

        if not api_key:
            return []

        verify = detail_cfg.get("verify", True)
        timeout = float(detail_cfg.get("timeout", 3))

        try:
            resp = requests.get(
                f"{admin_endpoint.rstrip('/')}/api/campaigns",
                headers={"Authorization": api_key},
                timeout=timeout,
                verify=verify,
            )
            if resp.ok:
                campaigns = resp.json()
                return [
                    {
                        "name": campaign.get("name"),
                        "status": campaign.get("status") or "unknown",
                    }
                    for campaign in campaigns
                ]
        except Exception as exc:  # pragma: no cover
            logger.debug("fetch_gophish_campaigns failed: %s", exc)
        return []

    def fetch_pentestagent_tasks(self, detail_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        planning_dir = detail_cfg.get("planning_dir")
        if planning_dir:
            tasks_path = (BASE_DIR / planning_dir).resolve()
        else:
            tasks_path = TOOLS_DIR / "pentest-agent" / "data" / "planning"

        if not tasks_path.exists():
            return []

        items: List[Dict[str, Any]] = []
        for file in tasks_path.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                items.append({"name": data.get("topic", file.stem), "status": data.get("status", "未知")})
            except Exception as exc:  # pragma: no cover
                logger.debug("解析 PentestAgent 任务失败 %s: %s", file, exc)
                continue
        return items

    def fetch_openbas_scenarios(self, detail_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        if requests is None:
            return []

        token_env = detail_cfg.get("token_env", "OPENBAS_TOKEN")
        base_url_env = detail_cfg.get("base_url_env", "OPENBAS_BASE_URL")
        token = os.environ.get(token_env)
        if not token:
            return []

        base_url = os.environ.get(base_url_env, "https://localhost:8443")
        api_path = detail_cfg.get("path", "/api/scenarios")
        verify = detail_cfg.get("verify", True)
        timeout = float(detail_cfg.get("timeout", 3))

        try:
            resp = requests.get(
                f"{base_url.rstrip('/')}{api_path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=timeout,
                verify=verify,
            )
            if resp.ok:
                scenarios = resp.json().get("data", [])
                return [
                    {
                        "name": s.get("attributes", {}).get("name", "unknown"),
                        "status": s.get("attributes", {}).get("status", "draft"),
                    }
                    for s in scenarios
                ]
        except Exception as exc:  # pragma: no cover
            logger.debug("fetch_openbas_scenarios failed: %s", exc)
        return []

    def aggregate_external_details(self, services: List[ServiceStatus]) -> List[Dict[str, Any]]:
        sections: List[Dict[str, Any]] = []
        for service in services:
            detail_cfg = service.detail_config or {}
            detail_type = detail_cfg.get("type")
            if not detail_type:
                continue

            title = detail_cfg.get("title", f"{service.display_name} 详情")
            entries: List[Dict[str, Any]] = []

            if detail_type == "gophish_campaigns":
                entries = self.fetch_gophish_campaigns(detail_cfg)
            elif detail_type == "pentestagent_plans":
                entries = self.fetch_pentestagent_tasks(detail_cfg)
            elif detail_type == "openbas_scenarios":
                entries = self.fetch_openbas_scenarios(detail_cfg)

            sections.append({"title": title, "entries": entries})

        return sections


monitor = IntegrationMonitor()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/dashboard")
def dashboard() -> str:
    services = monitor.list_services()
    external_details = monitor.aggregate_external_details(services)
    return render_template("dashboard.html", services=services, external_details=external_details)


@app.route("/overview")
def overview() -> str:
    overlay_path = CONFIG_DIR / "seed_network_overlay.yaml"
    overlay_content = overlay_path.read_text(encoding="utf-8") if overlay_path.exists() else None
    return render_template("overview.html", overlay=overlay_content)


@app.route("/docs")
def docs() -> str:
    return render_template("docs.html")


@app.route("/showcase")
def showcase() -> str:
    services = monitor.list_services()

    foundation_layers = [
        {
            "title": "网络虚拟化基座",
            "points": [
                "MiniInternet 路由系统映射真实运营商链路，支持 BGP/OSPF 复合实验",
                "seed_network_overlay.yaml 将邮件、攻防、情报域统一编排，便于课堂快速切换场景",
                "run_demo_57.sh 调度 Docker Compose 栈，保障演示环境一键复原",
                "压缩镜像与镜像仓库缓存策略，支撑百人课堂的并发启动效率",
            ],
        },
        {
            "title": "安全邮件全链路",
            "points": [
                "Postfix/IMAP、DNSSEC、SPF/DMARC 等组件完整仿真真实企业邮件体系",
                "AI 钓鱼检测、APT 攻击模拟与 42 威胁狩猎实验形成闭环教学",
                "sitecustomize.py 与日志基线脚本兼容 Python 3.11 / Docker Compose 运行环境",
                "统一采集 ELK/Pipeline 指标，可扩展到 Sysmon、Suricata 等多源日志",
            ],
        },
        {
            "title": "外部工具联动",
            "points": [
                "IntegrationMonitor 监控 Gophish、PentestAgent、OpenBAS 等关键工具运行态",
                "prepare_external_tools.sh 快速拉起 Docker 服务，缩短课堂准备时间",
                "REST API 预留扩展点，支持自动化评分与剧本触发",
                "结合 Seed-Emulator API 可生成多主题拓扑，支撑滚动式实验设计",
            ],
        },
    ]

    experiment_timeline = [
        {
            "id": "29",
            "name": "29 基础邮件系统",
            "focus": "SMTP/IMAP 服务搭建与基础防护",
            "teaching": [
                "理解 Postfix、Dovecot 的核心配置并完成端到端收发",
                "掌握 SPF/DKIM/DMARC 对可信送达率的影响",
                "在 Wireshark 中分析 SMTP STARTTLS 握手与证书链",
            ],
        },
        {
            "id": "29-1",
            "name": "29-1 真实网络邮件系统",
            "focus": "跨自治系统路由与公网仿真",
            "teaching": [
                "观察 MiniInternet 中 BGP 宣告的收敛过程",
                "评估多运营商场景下 MX 记录的高可用策略",
                "模拟 Anycast 邮件网关，讨论路由抖动对 SLA 的影响",
            ],
        },
        {
            "id": "30",
            "name": "30 AI 钓鱼检测系统",
            "focus": "AI 钓鱼检测与对抗生成",
            "teaching": [
                "使用 LLM/Python 模型识别高风险邮件并分析置信度",
                "设计对抗样本，评估检测模型的鲁棒性",
                "结合 Embedding 检索实现正文主题聚类，辅助 SOC 分流",
            ],
        },
        {
            "id": "31",
            "name": "31 高级 APT 仿真系统",
            "focus": "多阶段渗透与投递链路",
            "teaching": [
                "演练鱼叉邮件投递后的主机侦察与横向移动",
                "结合 IDS/日志进行 IOC 提取与响应",
                "串联 ATT&CK T1566、T1059、T1021 等技术，分析攻击链",
            ],
        },
        {
            "id": "42",
            "name": "42 企业级邮件威胁狩猎",
            "focus": "跨域威胁情报与狩猎",
            "teaching": [
                "关联日志、威胁情报实现跨域追踪",
                "构建自定义检测规则与自动化响应剧本",
                "讲解 STIX/TAXII 情报订阅与可信度评分方法",
            ],
        },
        {
            "id": "57",
            "name": "57 综合安全评估",
            "focus": "真实工具协同演练",
            "teaching": [
                "汇总攻防指标产出端到端评估报告",
                "使用 run_demo_57.sh / cleanup_seed_env.sh 保证演示可重复",
                "引导学生撰写 Lessons Learned 对照真实攻防案例",
            ],
        },
    ]

    toolchain = [
        {
            "name": "Gophish 钓鱼演练平台",
            "summary": "用于模拟鱼叉邮件攻击并跟踪用户行为，课堂中可实时查看投递指标。",
            "highlights": [
                "支持定时与即时 Campaign，适配不同教学节奏",
                "结合 IntegrationMonitor API 呈现成功率、点击率等实时数据",
                "导出 CSV/PDF 报告，便于学生完成实验总结",
            ],
            "link": "https://github.com/gophish/gophish",
        },
        {
            "name": "PentestAgent 自动化攻防助手",
            "summary": "管理渗透测试计划与脚本执行，帮助学生理解攻击者视角的行动路径。",
            "highlights": [
                "规划文件与任务执行记录可作为课堂评分依据",
                "可触发自定义脚本，对接邮件与横向渗透场景",
                "与 OpenBAS 情景剧本联动，形成攻防协同",
            ],
            "link": "https://github.com/seed-labs/pentest-agent",
        },
        {
            "name": "OpenBAS 蓝队演练平台",
            "summary": "提供蓝队响应剧本与评分看板，帮助学生练习应急流程。",
            "highlights": [
                "Webhook 可与 IntegrationMonitor 互通，记录演练节点",
                "自带评分模型支持 Bloom 目标层次化评估",
                "可导入 MITRE ATT&CK 场景，拓展更多攻防主题",
            ],
            "link": "https://github.com/OpenBAS-Platform/openbas",
        },
        {
            "name": "IntegrationMonitor 状态看板",
            "summary": "本项目内置的健康检查服务，统一展示关键组件运行状态。",
            "highlights": [
                "HTTP/TCP/容器三种健康检查方式覆盖课堂常用组件",
                "支持扩展外部情报源状态，辅助学生观测依赖链",
                "API 提供 JSON 输出，可嵌入自定义可视化界面",
            ],
            "link": "https://github.com/seed-labs/seed-emulator-email-system",
        },
    ]

    gophish_guide = [
        {
            "title": "环境准备",
            "details": "执行 prepare_external_tools.sh，确保 Gophish 容器启动并监听 3333 端口。",
            "tips": "如启用自签名证书，可在浏览器中手动信任或导入 CA。",
        },
        {
            "title": "模板与受众导入",
            "details": "创建邮件模板、登陆页面，利用 CSV 导入目标分组，并与真实业务邮件进行对照。",
            "tips": "鼓励学生分析邮件语言风格，设计针对性的钓鱼话术。",
        },
        {
            "title": "活动编排与发送",
            "details": "配置 SMTP 指向 29-1 实验中继，发布钓鱼活动并观察实时指标变化。",
            "tips": "结合 PentestAgent 剧本自动触发邮件发送，模拟攻击波次。",
        },
        {
            "title": "结果分析",
            "details": "下载报告并与 30 实验的 AI 判定、42 实验的狩猎日志对比，形成闭环。",
            "tips": "利用 OpenBAS 得分面板开展红蓝双方复盘。",
        },
    ]

    pedagogy_blueprint = [
        {
            "phase": "引入（15min）",
            "objectives": [
                "以真实案例短视频或新闻导入，提高威胁感知",
                "设置课堂投票：统计同学近三个月收到钓鱼邮件的比例",
            ],
            "facilitation": "教师演示邮件链路拓扑，强调红/蓝/情报三域协同。",
        },
        {
            "phase": "探究（60min）",
            "objectives": [
                "分组扮演攻防角色，运行 Gophish、PentestAgent、OpenBAS",
                "记录点击率、检测率、响应时间等关键指标",
            ],
            "facilitation": "助教巡回指导，提示观察日志证据与战术映射。",
        },
        {
            "phase": "总结（30min）",
            "objectives": [
                "展示 IntegrationMonitor 数据，完成经验教训汇报",
                "引导学生撰写个人反思：如何提升组织抗钓鱼能力",
            ],
            "facilitation": "结合 Rubric 反馈技术表现与沟通协同表现。",
        },
    ]

    case_studies = [
        {
            "title": "能源企业鱼叉攻击复盘",
            "insights": [
                "映射 ATT&CK T1566.002 + T1059.003，突出邮件入口与脚本执行",
                "利用 OpenBAS 还原事件时间线，讨论蓝队检测盲点",
                "延伸供应链持久化策略，强调多域协同防御",
            ],
            "link": "https://attack.mitre.org/versions/v13/techniques/T1566/002/",
        },
        {
            "title": "银狐木马投递链与 57 实验对照",
            "insights": [
                "对比真实木马载荷与 42 实验模拟流程，识别差异",
                "强调多阶段取证：邮件头、Payload、C2 流量",
                "结合 PentestAgent 探测横向移动迹象，强化攻防思维",
            ],
            "link": "https://www.cisa.gov/news-events/cybersecurity-advisories",
        },
        {
            "title": "多云环境的邮件合规挑战",
            "insights": [
                "分析 SaaS 邮件网关与自建系统的日志整合痛点",
                "引导学生思考 DMARC 报告自动化与情报联动",
                "讨论数据主权与跨境邮件备份策略的风险",
            ],
            "link": "https://cloudsecurityalliance.org/",
        },
    ]

    assessment_rubric = [
        {
            "dimension": "技术执行",
            "indicators": [
                "能够独立部署并验证 Gophish/PentestAgent/OpenBAS",
                "解释邮件安全协议与攻击链条的关键节点",
            ],
            "scales": ["初阶", "熟练", "专家"],
        },
        {
            "dimension": "协作与沟通",
            "indicators": [
                "攻防双方利用共享笔记或 OpenBAS 注释对齐行动",
                "蓝队在汇报中引用证据与时间线，提出改进建议",
            ],
            "scales": ["描述事实", "分析原因", "提出策略"],
        },
        {
            "dimension": "反思与迁移",
            "indicators": [
                "撰写 Lessons Learned，识别组织流程缺口",
                "提出可落地的防钓鱼宣传或培训方案",
            ],
            "scales": ["识别问题", "提出改进", "形成持续改进计划"],
        },
    ]

    insight_cards = [
        {
            "headline": "钓鱼检测阈值对用户体验的影响",
            "detail": "在 30 实验中比较不同阈值设置的误报率，引导学生设计分层响应策略。",
        },
        {
            "headline": "情报驱动的攻防共创",
            "detail": "利用 PentestAgent 输出与 OpenBAS 场景联动，将红队行动转化为可复用的蓝队检测规则。",
        },
        {
            "headline": "教学与实战的数据循环",
            "detail": "借助 IntegrationMonitor 记录的日志与指标构建数据资产，支持课程迭代与科研分析。",
        },
    ]

    future_tracks = [
        {
            "title": "自动化剧本与评分",
            "focus": "结合 OpenBAS、Atomic Red Team 将实验转化为课堂评分规则",
            "actions": [
                "使用 OpenBAS Webhook 调用 IntegrationMonitor API 更新状态",
                "通过 Jupyter Notebook 或 Streamlit 生成实时课堂看板",
            ],
        },
        {
            "title": "真实威胁情报接入",
            "focus": "扩展到 OpenCTI / MISP 等威胁情报平台，实现 IOC 自动同步",
            "actions": [
                "在 42 实验中订阅 TAXII Feed 丰富狩猎指标",
                "对接 PentestAgent 任务结果，形成情报回流",
            ],
        },
        {
            "title": "沉浸式演示与跨学科合作",
            "focus": "结合 Aurora-demos、CALDERA 与传播学课程开展沉浸式演练",
            "actions": [
                "构建 WebGL 拓扑动画，直观呈现攻击链",
                "记录 run_demo_57.sh 日志供学生复盘并撰写案例分析",
            ],
        },
    ]

    return render_template(
        "showcase.html",
        services=services,
        foundation_layers=foundation_layers,
        experiment_timeline=experiment_timeline,
        toolchain=toolchain,
        gophish_guide=gophish_guide,
        pedagogy_blueprint=pedagogy_blueprint,
        case_studies=case_studies,
        assessment_rubric=assessment_rubric,
        insight_cards=insight_cards,
        future_tracks=future_tracks,
    )


@app.route("/docs/<path:filename>")
def serve_docs(filename: str):
    return send_from_directory(DOCS_DIR, filename)


@app.route("/config/<path:filename>")
def serve_config(filename: str):
    return send_from_directory(CONFIG_DIR, filename)


@app.route("/external/<tool>/<path:resource>")
def serve_external(tool: str, resource: str):
    tool_path = TOOLS_DIR / tool
    if resource.lower() == "readme":
        candidates = [tool_path / "README.md", tool_path / "README".lower(), tool_path / "README".upper()]
        for candidate in candidates:
            if candidate.exists():
                return send_from_directory(candidate.parent, candidate.name)
    return ("未找到资源", 404)


@app.route("/api/status")
def api_status():
    services = monitor.list_services()
    external_details = monitor.aggregate_external_details(services)
    return jsonify(
        {
            "services": [service.__dict__ for service in services],
            "external_details": external_details,
        }
    )


@app.route("/api/execute", methods=["POST"])
def api_execute():
    payload = request.json or {}
    cmd = payload.get("cmd")
    if not cmd:
        return jsonify({"success": False, "message": "缺少 cmd 参数"}), 400
    if cmd not in {"prepare_tools"}:
        return jsonify({"success": False, "message": "不支持的命令"}), 400

    script_path = BASE_DIR / "scripts" / "prepare_external_tools.sh"
    if not script_path.exists():
        return jsonify({"success": False, "message": "脚本不存在"}), 500

    try:
        result = subprocess.run(
            ["/bin/bash", str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=900,
        )
        success = result.returncode == 0
        return jsonify({"success": success, "output": result.stdout})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "message": "执行超时"}), 504


def main() -> None:
    logger.info("57 综合安全评估实验控制台已启动: http://localhost:4257")
    app.run(host="0.0.0.0", port=4257, debug=False, threaded=True)


if __name__ == "__main__":  # pragma: no cover
    main()

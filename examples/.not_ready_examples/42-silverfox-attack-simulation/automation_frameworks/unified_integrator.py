#!/usr/bin/env python3
"""
自动化框架统一集成器
Unified Automation Framework Integrator

该模块统一管理所有自动化框架的集成，提供统一的接口来协调钓鱼、攻击链自动化和渗透测试
"""

import logging
import time
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from .gophish_integration import GophishIntegration
from .aurora_demos_integration import AuroraDemosIntegration
from .pentest_agent_integration import PentestAgentIntegration

class UnifiedAutomationIntegrator:
    """
    统一自动化框架集成器
    """

    def __init__(self, config_path: str = "automation_frameworks/unified_config.json"):
        """
        初始化统一集成器

        Args:
            config_path: 统一配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.frameworks = {}
        self.logger = logging.getLogger(__name__)

        self._load_config()
        self._setup_logging()
        self._initialize_frameworks()

    def _load_config(self):
        """加载统一配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self.logger.info("统一自动化配置加载成功")

        except Exception as e:
            self.logger.error(f"统一自动化配置加载失败: {e}")
            raise

    def _setup_logging(self):
        """设置日志"""
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _initialize_frameworks(self):
        """初始化各个框架"""
        try:
            # 初始化Gophish
            if self.config.get("frameworks", {}).get("gophish", {}).get("enabled", False):
                gophish_config = self.config["frameworks"]["gophish"].get("config_path", "config/gophish_config.json")
                self.frameworks["gophish"] = GophishIntegration(gophish_config)
                self.logger.info("Gophish框架初始化成功")

            # 初始化Aurora-demos
            if self.config.get("frameworks", {}).get("aurora_demos", {}).get("enabled", False):
                aurora_config = self.config["frameworks"]["aurora_demos"].get("config_path", "config/aurora_config.yaml")
                self.frameworks["aurora_demos"] = AuroraDemosIntegration(aurora_config)
                self.logger.info("Aurora-demos框架初始化成功")

            # 初始化PentestAgent
            if self.config.get("frameworks", {}).get("pentest_agent", {}).get("enabled", False):
                pentest_config = self.config["frameworks"]["pentest_agent"].get("config_path", "config/pentest_agent_config.json")
                self.frameworks["pentest_agent"] = PentestAgentIntegration(pentest_config)
                self.logger.info("PentestAgent框架初始化成功")

        except Exception as e:
            self.logger.error(f"框架初始化失败: {e}")
            raise

    def run_integrated_attack_simulation(self) -> Dict[str, Any]:
        """
        运行集成攻击模拟

        Returns:
            模拟结果
        """
        self.logger.info("开始运行集成攻击模拟")

        results = {
            "phishing_campaign": {},
            "attack_chain": {},
            "pentest_assessment": {},
            "overall_status": "running",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            # 阶段1: 钓鱼活动 (如果Gophish可用)
            if "gophish" in self.frameworks:
                self.logger.info("执行钓鱼活动阶段")
                gophish = self.frameworks["gophish"]

                # 设置钓鱼基础设施
                infrastructure = gophish.setup_phishing_infrastructure()
                if infrastructure:
                    # 运行钓鱼活动
                    phishing_results = gophish.run_phishing_campaign(infrastructure)
                    results["phishing_campaign"] = phishing_results

                    if not phishing_results["success"]:
                        results["overall_status"] = "phishing_failed"
                        return results
                else:
                    results["phishing_campaign"] = {"success": False, "error": "基础设施设置失败"}
                    results["overall_status"] = "infrastructure_failed"
                    return results

            # 阶段2: 攻击链自动化 (如果Aurora-demos可用)
            if "aurora_demos" in self.frameworks:
                self.logger.info("执行攻击链自动化阶段")
                aurora = self.frameworks["aurora_demos"]

                # 运行银狐木马攻击链模拟
                chain_results = aurora.run_silverfox_simulation()
                results["attack_chain"] = chain_results

                if not chain_results["success"]:
                    results["overall_status"] = "attack_chain_failed"
                    return results

            # 阶段3: 渗透测试评估 (如果PentestAgent可用)
            if "pentest_agent" in self.frameworks:
                self.logger.info("执行渗透测试评估阶段")
                pentest = self.frameworks["pentest_agent"]

                # 定义目标
                targets = self.config.get("targets", ["mail-qq-tencent", "web-server"])

                # 运行综合渗透测试
                pentest_results = pentest.run_comprehensive_pentest(targets)
                results["pentest_assessment"] = pentest_results

                if not pentest_results["success"] and pentest_results["overall_status"] == "failed":
                    results["overall_status"] = "pentest_failed"
                    return results

            # 所有阶段成功完成
            results["overall_status"] = "completed"
            self.logger.info("集成攻击模拟完成")

        except Exception as e:
            self.logger.error(f"集成攻击模拟失败: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)

        return results

    def run_phased_attack_simulation(self, phases: List[str] = None) -> Dict[str, Any]:
        """
        运行分阶段攻击模拟

        Args:
            phases: 要执行的阶段列表

        Returns:
            模拟结果
        """
        if phases is None:
            phases = ["recon", "phishing", "execution", "lateral", "exfil", "cleanup"]

        self.logger.info(f"开始分阶段攻击模拟，阶段: {phases}")

        results = {
            "phases_executed": [],
            "phase_results": {},
            "overall_status": "running",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            for phase in phases:
                self.logger.info(f"执行阶段: {phase}")
                phase_result = self._execute_phase(phase)
                results["phase_results"][phase] = phase_result
                results["phases_executed"].append(phase)

                if not phase_result["success"]:
                    results["overall_status"] = f"{phase}_failed"
                    break

                # 阶段间延迟
                time.sleep(2)

            if results["overall_status"] == "running":
                results["overall_status"] = "completed"

        except Exception as e:
            self.logger.error(f"分阶段攻击模拟失败: {e}")
            results["overall_status"] = "error"
            results["error"] = str(e)

        return results

    def _execute_phase(self, phase: str) -> Dict[str, Any]:
        """
        执行单个阶段

        Args:
            phase: 阶段名称

        Returns:
            阶段执行结果
        """
        phase_configs = {
            "recon": self._execute_recon_phase,
            "phishing": self._execute_phishing_phase,
            "execution": self._execute_execution_phase,
            "lateral": self._execute_lateral_phase,
            "exfil": self._execute_exfil_phase,
            "cleanup": self._execute_cleanup_phase
        }

        if phase in phase_configs:
            return phase_configs[phase]()
        else:
            return {"success": False, "error": f"未知阶段: {phase}"}

    def _execute_recon_phase(self) -> Dict[str, Any]:
        """执行侦察阶段"""
        if "pentest_agent" in self.frameworks:
            targets = self.config.get("targets", ["mail-qq-tencent"])
            return self.frameworks["pentest_agent"].run_reconnaissance_scan(targets)
        return {"success": False, "error": "PentestAgent不可用"}

    def _execute_phishing_phase(self) -> Dict[str, Any]:
        """执行钓鱼阶段"""
        if "gophish" in self.frameworks:
            infrastructure = self.frameworks["gophish"].setup_phishing_infrastructure()
            if infrastructure:
                return self.frameworks["gophish"].run_phishing_campaign(infrastructure)
            return {"success": False, "error": "基础设施设置失败"}
        return {"success": False, "error": "Gophish不可用"}

    def _execute_execution_phase(self) -> Dict[str, Any]:
        """执行执行阶段"""
        if "aurora_demos" in self.frameworks:
            return self.frameworks["aurora_demos"].run_silverfox_simulation()
        return {"success": False, "error": "Aurora-demos不可用"}

    def _execute_lateral_phase(self) -> Dict[str, Any]:
        """执行横向移动阶段"""
        # 这里可以集成具体的横向移动逻辑
        return {"success": True, "message": "横向移动阶段模拟完成"}

    def _execute_exfil_phase(self) -> Dict[str, Any]:
        """执行数据窃取阶段"""
        # 这里可以集成具体的数据窃取逻辑
        return {"success": True, "message": "数据窃取阶段模拟完成"}

    def _execute_cleanup_phase(self) -> Dict[str, Any]:
        """执行清理阶段"""
        # 这里可以集成具体的清理逻辑
        return {"success": True, "message": "清理阶段模拟完成"}

    def get_framework_status(self) -> Dict[str, Any]:
        """
        获取框架状态

        Returns:
            框架状态信息
        """
        status = {
            "frameworks": {},
            "overall_health": "healthy"
        }

        for name, framework in self.frameworks.items():
            try:
                # 这里可以添加具体的健康检查逻辑
                status["frameworks"][name] = {
                    "status": "active",
                    "last_check": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            except Exception as e:
                status["frameworks"][name] = {
                    "status": "error",
                    "error": str(e)
                }
                status["overall_health"] = "degraded"

        return status

    def generate_integrated_report(self, results: Dict, output_path: str) -> bool:
        """
        生成集成报告

        Args:
            results: 模拟结果
            output_path: 输出路径

        Returns:
            是否生成成功
        """
        self.logger.info(f"生成集成报告: {output_path}")

        report_data = {
            "title": "银狐木马自动化攻击模拟集成报告",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "frameworks_used": list(self.frameworks.keys()),
            "results": results,
            "summary": {
                "phishing_success": results.get("phishing_campaign", {}).get("success", False),
                "attack_chain_success": results.get("attack_chain", {}).get("success", False),
                "pentest_success": results.get("pentest_assessment", {}).get("overall_status") == "completed",
                "overall_status": results.get("overall_status", "unknown")
            },
            "recommendations": self._generate_recommendations(results)
        }

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)

            self.logger.info("集成报告生成成功")
            return True

        except Exception as e:
            self.logger.error(f"集成报告生成失败: {e}")
            return False

    def _generate_recommendations(self, results: Dict) -> List[str]:
        """
        生成建议

        Args:
            results: 结果数据

        Returns:
            建议列表
        """
        recommendations = []

        if not results.get("phishing_campaign", {}).get("success", False):
            recommendations.append("检查Gophish配置和邮件服务器连接")

        if not results.get("attack_chain", {}).get("success", False):
            recommendations.append("验证Aurora-demos攻击链配置")

        if results.get("pentest_assessment", {}).get("overall_status") != "completed":
            recommendations.append("检查PentestAgent扫描配置和目标可达性")

        if not recommendations:
            recommendations.append("所有自动化框架运行正常，建议进行实际环境测试")

        return recommendations


if __name__ == "__main__":
    # 测试统一集成器
    integrator = UnifiedAutomationIntegrator()

    # 检查框架状态
    status = integrator.get_framework_status()
    print(f"框架状态: {status}")

    # 运行集成攻击模拟
    results = integrator.run_integrated_attack_simulation()
    print(f"集成攻击模拟结果: {results}")

    # 生成报告
    report_path = "/tmp/integrated_attack_report.json"
    integrator.generate_integrated_report(results, report_path)
    print(f"集成报告已生成: {report_path}")
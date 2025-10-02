#!/usr/bin/env python3
"""
Aurora-demos攻击链自动化集成模块
Aurora-demos Attack Chain Automation Integration Module

该模块负责与Aurora-demos攻击链自动化框架的集成，实现完整的攻击链自动化执行
"""

import subprocess
import json
import yaml
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import os

class AuroraDemosIntegration:
    """
    Aurora-demos攻击链自动化集成类
    """

    def __init__(self, config_path: str = "automation_frameworks/aurora_config.yaml"):
        """
        初始化Aurora-demos集成

        Args:
            config_path: Aurora-demos配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.aurora_path = ""
        self.logger = logging.getLogger(__name__)

        self._load_config()
        self._setup_logging()

    def _load_config(self):
        """加载Aurora-demos配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            self.aurora_path = self.config.get("aurora_path", "/opt/aurora-demos")
            self.logger.info("Aurora-demos配置加载成功")

        except Exception as e:
            self.logger.error(f"Aurora-demos配置加载失败: {e}")
            raise

    def _setup_logging(self):
        """设置日志"""
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _run_aurora_command(self, command: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        执行Aurora-demos命令

        Args:
            command: 命令列表
            cwd: 工作目录

        Returns:
            执行结果
        """
        try:
            full_command = [os.path.join(self.aurora_path, "aurora")] + command
            self.logger.info(f"执行Aurora命令: {' '.join(full_command)}")

            result = subprocess.run(
                full_command,
                cwd=cwd or self.aurora_path,
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }

        except subprocess.TimeoutExpired:
            self.logger.error("Aurora命令执行超时")
            return {"success": False, "error": "命令执行超时"}
        except Exception as e:
            self.logger.error(f"Aurora命令执行失败: {e}")
            return {"success": False, "error": str(e)}

    def create_attack_chain_config(self, chain_config: Dict) -> str:
        """
        创建攻击链配置文件

        Args:
            chain_config: 攻击链配置

        Returns:
            配置文件路径
        """
        config_file = f"/tmp/aurora_chain_{int(time.time())}.yaml"

        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(chain_config, f, default_flow_style=False)

            self.logger.info(f"攻击链配置文件创建成功: {config_file}")
            return config_file

        except Exception as e:
            self.logger.error(f"攻击链配置文件创建失败: {e}")
            return ""

    def execute_attack_chain(self, chain_config: Dict) -> Dict[str, Any]:
        """
        执行攻击链

        Args:
            chain_config: 攻击链配置

        Returns:
            执行结果
        """
        self.logger.info("开始执行攻击链")

        # 创建配置文件
        config_file = self.create_attack_chain_config(chain_config)
        if not config_file:
            return {"success": False, "error": "配置文件创建失败"}

        # 执行攻击链
        result = self._run_aurora_command(["execute", "--config", config_file])

        # 清理配置文件
        try:
            os.remove(config_file)
        except:
            pass

        if result["success"]:
            self.logger.info("攻击链执行成功")
            return {"success": True, "output": result["stdout"]}
        else:
            self.logger.error(f"攻击链执行失败: {result['stderr']}")
            return {"success": False, "error": result["stderr"]}

    def get_attack_chain_status(self, chain_id: str) -> Dict[str, Any]:
        """
        获取攻击链执行状态

        Args:
            chain_id: 攻击链ID

        Returns:
            状态信息
        """
        result = self._run_aurora_command(["status", "--chain", chain_id])

        if result["success"]:
            try:
                status = json.loads(result["stdout"])
                return status
            except:
                return {"status": "unknown", "output": result["stdout"]}
        else:
            return {"status": "error", "error": result["stderr"]}

    def stop_attack_chain(self, chain_id: str) -> bool:
        """
        停止攻击链执行

        Args:
            chain_id: 攻击链ID

        Returns:
            是否停止成功
        """
        result = self._run_aurora_command(["stop", "--chain", chain_id])

        if result["success"]:
            self.logger.info(f"攻击链 {chain_id} 停止成功")
            return True
        else:
            self.logger.error(f"攻击链 {chain_id} 停止失败: {result['stderr']}")
            return False

    def create_silverfox_attack_chain(self) -> Dict[str, Any]:
        """
        创建银狐木马攻击链配置

        Returns:
            攻击链配置
        """
        chain_config = {
            "chain_name": "silverfox_attack_chain",
            "description": "银狐木马完整攻击链自动化执行",
            "stages": [
                {
                    "name": "reconnaissance",
                    "type": "recon",
                    "description": "情报收集阶段",
                    "targets": ["mail-qq-tencent", "web-server"],
                    "tools": ["nmap", "masscan"],
                    "config": {
                        "ports": "1-65535",
                        "timing": "aggressive",
                        "output_format": "json"
                    }
                },
                {
                    "name": "phishing_delivery",
                    "type": "phishing",
                    "description": "钓鱼邮件投递阶段",
                    "depends_on": ["reconnaissance"],
                    "config": {
                        "template": "chrome_update",
                        "smtp_server": "mail-qq-tencent",
                        "targets": ["victim1@company.com", "victim2@company.com"],
                        "attachment": "chrome_update.exe"
                    }
                },
                {
                    "name": "malware_execution",
                    "type": "execution",
                    "description": "恶意软件执行阶段",
                    "depends_on": ["phishing_delivery"],
                    "config": {
                        "payload": "silverfox_trojan.exe",
                        "execution_method": "rundll32",
                        "persistence": True
                    }
                },
                {
                    "name": "lateral_movement",
                    "type": "lateral",
                    "description": "横向移动阶段",
                    "depends_on": ["malware_execution"],
                    "config": {
                        "technique": "pass_the_hash",
                        "targets": ["dc.company.com", "fileserver.company.com"],
                        "credentials": {
                            "source": "dumped_hashes",
                            "method": "mimikatz"
                        }
                    }
                },
                {
                    "name": "data_exfiltration",
                    "type": "exfil",
                    "description": "数据窃取阶段",
                    "depends_on": ["lateral_movement"],
                    "config": {
                        "data_types": ["credentials", "documents", "emails"],
                        "method": "dns_tunneling",
                        "destination": "attacker.controlled.domain"
                    }
                },
                {
                    "name": "cleanup",
                    "type": "cleanup",
                    "description": "清理痕迹阶段",
                    "depends_on": ["data_exfiltration"],
                    "config": {
                        "remove_logs": True,
                        "clear_event_logs": True,
                        "remove_artifacts": True
                    }
                }
            ],
            "global_config": {
                "timeout": 3600,
                "retry_attempts": 3,
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "output": "/var/log/aurora/silverfox_chain.log"
                },
                "reporting": {
                    "format": "html",
                    "output": "/var/reports/silverfox_attack_report.html"
                }
            }
        }

        return chain_config

    def run_silverfox_simulation(self) -> Dict[str, Any]:
        """
        运行银狐木马攻击链模拟

        Returns:
            模拟结果
        """
        self.logger.info("开始运行银狐木马攻击链模拟")

        # 创建攻击链配置
        chain_config = self.create_silverfox_attack_chain()

        # 执行攻击链
        result = self.execute_attack_chain(chain_config)

        if result["success"]:
            # 等待执行完成
            chain_id = f"silverfox_{int(time.time())}"
            time.sleep(5)  # 简化的等待逻辑

            # 获取最终状态
            status = self.get_attack_chain_status(chain_id)

            return {
                "success": True,
                "chain_id": chain_id,
                "status": status,
                "output": result["output"]
            }
        else:
            return result

    def create_custom_attack_chain(self, stages: List[Dict], name: str = "custom_chain") -> Dict[str, Any]:
        """
        创建自定义攻击链

        Args:
            stages: 攻击阶段列表
            name: 链名称

        Returns:
            攻击链配置
        """
        chain_config = {
            "chain_name": name,
            "description": f"自定义攻击链: {name}",
            "stages": stages,
            "global_config": {
                "timeout": 1800,
                "retry_attempts": 2,
                "logging": {
                    "level": "INFO",
                    "format": "json",
                    "output": f"/var/log/aurora/{name}.log"
                },
                "reporting": {
                    "format": "json",
                    "output": f"/var/reports/{name}_report.json"
                }
            }
        }

        return chain_config

    def validate_attack_chain(self, chain_config: Dict) -> Dict[str, Any]:
        """
        验证攻击链配置

        Args:
            chain_config: 攻击链配置

        Returns:
            验证结果
        """
        result = self._run_aurora_command(["validate", "--config", "-"], input=json.dumps(chain_config))

        if result["success"]:
            return {"valid": True, "message": "攻击链配置验证通过"}
        else:
            return {"valid": False, "error": result["stderr"]}


if __name__ == "__main__":
    # 测试Aurora-demos集成
    aurora = AuroraDemosIntegration()

    # 运行银狐木马攻击链模拟
    result = aurora.run_silverfox_simulation()
    print(f"银狐攻击链模拟结果: {result}")

    # 创建自定义攻击链
    custom_stages = [
        {
            "name": "initial_access",
            "type": "phishing",
            "description": "初始访问阶段",
            "config": {"method": "spear_phishing"}
        },
        {
            "name": "privilege_escalation",
            "type": "privesc",
            "description": "权限提升阶段",
            "depends_on": ["initial_access"],
            "config": {"technique": "uac_bypass"}
        }
    ]

    custom_chain = aurora.create_custom_attack_chain(custom_stages, "test_chain")
    print(f"自定义攻击链配置: {custom_chain}")

    # 验证攻击链
    validation = aurora.validate_attack_chain(custom_chain)
    print(f"攻击链验证结果: {validation}")
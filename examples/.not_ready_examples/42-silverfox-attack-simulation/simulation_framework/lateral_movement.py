"""
横向移动模拟器 - 模拟网络内的主机间移动
Lateral Movement Simulator - Simulates movement between hosts in the network
"""

import random
import logging
from typing import List, Dict, Any, Optional
import time

class LateralMovementSimulator:
    """
    横向移动模拟器，负责模拟攻击者在网络内的移动
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化横向移动模拟器

        Args:
            config: 网络配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 网络拓扑信息
        self.network_topology = self.config.get("network", {}).get("topology", {})
        self.hosts = self.network_topology.get("hosts", [])

        # 横向移动统计
        self.movement_stats = {
            "discovered_targets": 0,
            "successful_compromises": 0,
            "failed_attempts": 0,
            "compromised_hosts": []
        }

        # 凭据数据库（模拟）
        self.credentials_db = self._initialize_credentials_db()

    def _initialize_credentials_db(self) -> Dict[str, List[str]]:
        """初始化凭据数据库"""
        # 模拟一些常见的凭据
        return {
            "admin": ["password", "admin123", "Admin@123"],
            "user": ["password", "user123", "User@123"],
            "root": ["toor", "root123", "Root@123"],
            "guest": ["guest", "Guest@123"],
            "test": ["test", "Test@123"]
        }

    def discover_targets(self) -> List[Dict[str, Any]]:
        """
        发现潜在的目标主机

        Returns:
            发现的目标主机列表
        """
        self.logger.info("开始目标主机发现", extra={"stage": "lateral_movement"})

        discovered_targets = []

        # 模拟网络扫描发现主机
        for host in self.hosts:
            if random.random() < 0.8:  # 80% 的发现率
                target_info = {
                    "ip": host.get("ip", "unknown"),
                    "hostname": host.get("hostname", "unknown"),
                    "os": host.get("os", "unknown"),
                    "services": host.get("services", []),
                    "vulnerabilities": host.get("vulnerabilities", [])
                }
                discovered_targets.append(target_info)
                self.logger.info(f"发现目标主机: {target_info['ip']} ({target_info['hostname']})",
                               extra={"stage": "lateral_movement"})

        self.movement_stats["discovered_targets"] = len(discovered_targets)
        self.logger.info(f"目标发现完成，共发现 {len(discovered_targets)} 个目标",
                        extra={"stage": "lateral_movement"})

        return discovered_targets

    def attempt_compromise(self, target: Dict[str, Any]) -> bool:
        """
        尝试入侵目标主机

        Args:
            target: 目标主机信息

        Returns:
            是否成功入侵
        """
        target_ip = target.get("ip", "unknown")
        self.logger.info(f"尝试入侵目标: {target_ip}", extra={"stage": "lateral_movement"})

        # 尝试多种入侵方法
        compromise_methods = [
            self._try_credential_stuffing,
            self._try_exploit_vulnerability,
            self._try_pass_the_hash,
            self._try_smb_exploit
        ]

        for method in compromise_methods:
            if method(target):
                self.movement_stats["successful_compromises"] += 1
                self.movement_stats["compromised_hosts"].append(target_ip)
                self.logger.info(f"成功入侵目标: {target_ip}", extra={"stage": "lateral_movement"})
                return True

            # 短暂延迟模拟尝试间隔
            time.sleep(random.uniform(0.5, 1.5))

        self.movement_stats["failed_attempts"] += 1
        self.logger.warning(f"入侵目标失败: {target_ip}", extra={"stage": "lateral_movement"})
        return False

    def _try_credential_stuffing(self, target: Dict[str, Any]) -> bool:
        """尝试凭据填充攻击"""
        target_ip = target.get("ip", "unknown")

        # 检查目标是否运行SMB或其他服务
        if "SMB" not in target.get("services", []):
            return False

        self.logger.info(f"尝试凭据填充攻击: {target_ip}", extra={"stage": "lateral_movement"})

        # 尝试常见的用户名密码组合
        for username, passwords in self.credentials_db.items():
            for password in passwords:
                if random.random() < 0.1:  # 10% 的成功率
                    self.logger.info(f"凭据填充成功: {username}:{password} @ {target_ip}",
                                   extra={"stage": "lateral_movement"})
                    return True

                time.sleep(random.uniform(0.1, 0.3))  # 模拟尝试延迟

        return False

    def _try_exploit_vulnerability(self, target: Dict[str, Any]) -> bool:
        """尝试利用漏洞入侵"""
        target_ip = target.get("ip", "unknown")
        vulnerabilities = target.get("vulnerabilities", [])

        if not vulnerabilities:
            return False

        self.logger.info(f"尝试漏洞利用: {target_ip}", extra={"stage": "lateral_movement"})

        # 尝试利用已知漏洞
        for vuln in vulnerabilities:
            vuln_name = vuln.get("name", "unknown")
            vuln_severity = vuln.get("severity", "low")

            # 高严重性漏洞更容易利用
            success_rate = 0.3 if vuln_severity == "high" else 0.1

            if random.random() < success_rate:
                self.logger.info(f"漏洞利用成功: {vuln_name} @ {target_ip}",
                               extra={"stage": "lateral_movement"})
                return True

            time.sleep(random.uniform(0.5, 1.0))  # 模拟利用尝试

        return False

    def _try_pass_the_hash(self, target: Dict[str, Any]) -> bool:
        """尝试哈希传递攻击"""
        target_ip = target.get("ip", "unknown")

        # 检查目标是否运行SMB
        if "SMB" not in target.get("services", []):
            return False

        self.logger.info(f"尝试哈希传递攻击: {target_ip}", extra={"stage": "lateral_movement"})

        # 模拟哈希传递
        if random.random() < 0.15:  # 15% 的成功率
            self.logger.info(f"哈希传递成功: {target_ip}", extra={"stage": "lateral_movement"})
            return True

        return False

    def _try_smb_exploit(self, target: Dict[str, Any]) -> bool:
        """尝试SMB漏洞利用"""
        target_ip = target.get("ip", "unknown")

        # 检查目标是否运行SMB
        if "SMB" not in target.get("services", []):
            return False

        self.logger.info(f"尝试SMB漏洞利用: {target_ip}", extra={"stage": "lateral_movement"})

        # 常见的SMB漏洞
        smb_vulns = ["EternalBlue", "SMBGhost", "SMBleed"]

        for vuln in smb_vulns:
            if random.random() < 0.2:  # 20% 的成功率
                self.logger.info(f"SMB漏洞利用成功: {vuln} @ {target_ip}",
                               extra={"stage": "lateral_movement"})
                return True

            time.sleep(random.uniform(0.3, 0.8))

        return False

    def execute_lateral_movement_path(self, start_host: str, max_hops: int = 5) -> List[str]:
        """
        执行横向移动路径

        Args:
            start_host: 起始主机
            max_hops: 最大跳数

        Returns:
            入侵路径列表
        """
        self.logger.info(f"开始横向移动路径执行，从 {start_host} 开始",
                        extra={"stage": "lateral_movement"})

        current_host = start_host
        movement_path = [current_host]

        for hop in range(max_hops):
            # 发现当前主机的邻居
            neighbors = self._discover_neighbors(current_host)

            if not neighbors:
                break

            # 尝试入侵邻居
            next_host = None
            for neighbor in neighbors:
                if neighbor not in movement_path:  # 避免循环
                    neighbor_info = self._get_host_info(neighbor)
                    if neighbor_info and self.attempt_compromise(neighbor_info):
                        next_host = neighbor
                        break

            if next_host:
                movement_path.append(next_host)
                current_host = next_host
                self.logger.info(f"横向移动到: {next_host} (跳数: {hop + 1})",
                               extra={"stage": "lateral_movement"})
            else:
                break

        self.logger.info(f"横向移动路径完成: {' -> '.join(movement_path)}",
                        extra={"stage": "lateral_movement"})

        return movement_path

    def _discover_neighbors(self, host: str) -> List[str]:
        """发现邻居主机"""
        # 模拟网络邻居发现
        neighbors = []
        for h in self.hosts:
            if h.get("ip") != host and random.random() < 0.6:  # 60% 的邻居发现率
                neighbors.append(h.get("ip"))

        return neighbors[:random.randint(1, 3)]  # 最多3个邻居

    def _get_host_info(self, host_ip: str) -> Optional[Dict[str, Any]]:
        """获取主机信息"""
        for host in self.hosts:
            if host.get("ip") == host_ip:
                return host
        return None

    def get_movement_stats(self) -> Dict[str, Any]:
        """获取横向移动统计信息"""
        return self.movement_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.movement_stats = {
            "discovered_targets": 0,
            "successful_compromises": 0,
            "failed_attempts": 0,
            "compromised_hosts": []
        }
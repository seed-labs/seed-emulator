"""
数据外泄模拟器 - 模拟敏感数据的窃取和外传
Data Exfiltration Simulator - Simulates theft and exfiltration of sensitive data
"""

import random
import logging
import base64
import time
from typing import Dict, Any, List, Optional
import json

class DataExfiltrationSimulator:
    """
    数据外泄模拟器，负责模拟敏感数据的收集和外泄过程
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据外泄模拟器

        Args:
            config: 配置字典
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 数据外泄统计
        self.exfiltration_stats = {
            "total_data_collected": 0,
            "data_exfiltrated": 0,
            "methods_used": [],
            "failed_attempts": 0
        }

        # 模拟的数据类型
        self.data_types = [
            "user_credentials",
            "database_records",
            "financial_data",
            "intellectual_property",
            "system_configuration",
            "email_data"
        ]

        # 外泄方法配置
        self.exfiltration_methods = self.config.get("exfiltration", {}).get("methods", [
            "http",
            "dns",
            "icmp",
            "smtp"
        ])

    def collect_sensitive_data(self) -> List[Dict[str, Any]]:
        """
        收集敏感数据

        Returns:
            收集到的数据列表
        """
        self.logger.info("开始收集敏感数据", extra={"stage": "exfiltration"})

        collected_data = []

        # 模拟从不同位置收集数据
        collection_sources = [
            "/etc/passwd",
            "/home/user/documents/",
            "/var/www/database/",
            "C:\\Users\\Admin\\Documents\\",
            "/opt/application/config/"
        ]

        for source in collection_sources:
            if random.random() < 0.7:  # 70% 的收集成功率
                # 随机选择数据类型
                data_type = random.choice(self.data_types)

                # 生成模拟数据
                data_item = {
                    "source": source,
                    "type": data_type,
                    "size": random.randint(1000, 100000),  # 字节大小
                    "content": self._generate_mock_data(data_type),
                    "timestamp": time.time()
                }

                collected_data.append(data_item)
                self.exfiltration_stats["total_data_collected"] += data_item["size"]

                self.logger.info(f"收集到数据: {data_type} ({data_item['size']} bytes) 从 {source}",
                               extra={"stage": "exfiltration"})

        self.logger.info(f"数据收集完成，共收集 {len(collected_data)} 项数据",
                        extra={"stage": "exfiltration"})

        return collected_data

    def exfiltrate_data(self, method: str, data: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        通过指定方法外泄数据

        Args:
            method: 外泄方法 (http, dns, icmp, smtp)
            data: 要外泄的数据，如果为None则自动收集

        Returns:
            外泄是否成功
        """
        if data is None:
            data = self.collect_sensitive_data()

        if not data:
            self.logger.warning("没有数据可供外泄", extra={"stage": "exfiltration"})
            return False

        self.logger.info(f"开始数据外泄，使用方法: {method}", extra={"stage": "exfiltration"})

        try:
            if method == "http":
                success = self._exfiltrate_via_http(data)
            elif method == "dns":
                success = self._exfiltrate_via_dns(data)
            elif method == "icmp":
                success = self._exfiltrate_via_icmp(data)
            elif method == "smtp":
                success = self._exfiltrate_via_smtp(data)
            else:
                self.logger.warning(f"不支持的外泄方法: {method}", extra={"stage": "exfiltration"})
                return False

            if success:
                self.exfiltration_stats["data_exfiltrated"] += sum(item["size"] for item in data)
                self.exfiltration_stats["methods_used"].append(method)
                self.logger.info(f"数据外泄成功: {method} 方法传输 {len(data)} 项数据",
                               extra={"stage": "exfiltration"})
            else:
                self.exfiltration_stats["failed_attempts"] += 1
                self.logger.warning(f"数据外泄失败: {method}", extra={"stage": "exfiltration"})

            return success

        except Exception as e:
            self.logger.error(f"数据外泄异常: {method} - {e}", extra={"stage": "exfiltration"})
            self.exfiltration_stats["failed_attempts"] += 1
            return False

    def _exfiltrate_via_http(self, data: List[Dict[str, Any]]) -> bool:
        """通过HTTP外泄数据"""
        self.logger.info("通过HTTP通道外泄数据", extra={"stage": "exfiltration"})

        # 模拟HTTP POST请求
        c2_server = self.config.get("exfiltration", {}).get("c2_server", "http://c2.example.com/upload")

        for item in data:
            try:
                # 编码数据
                encoded_data = self._encode_data(item)

                # 模拟HTTP请求
                time.sleep(random.uniform(0.5, 2.0))

                if random.random() < 0.85:  # 85% 成功率
                    self.logger.info(f"HTTP外泄成功: {item['type']} 数据已发送",
                                   extra={"stage": "exfiltration"})
                else:
                    self.logger.warning(f"HTTP外泄失败: {item['type']} 数据发送失败",
                                      extra={"stage": "exfiltration"})
                    return False

            except Exception as e:
                self.logger.error(f"HTTP外泄异常: {e}", extra={"stage": "exfiltration"})
                return False

        return True

    def _exfiltrate_via_dns(self, data: List[Dict[str, Any]]) -> bool:
        """通过DNS外泄数据"""
        self.logger.info("通过DNS通道外泄数据", extra={"stage": "exfiltration"})

        # DNS外泄通常用于小量数据
        max_dns_size = 63  # DNS标签最大长度

        for item in data:
            try:
                # 将数据编码为DNS查询
                encoded_chunks = self._encode_for_dns(item["content"])

                for chunk in encoded_chunks:
                    # 模拟DNS查询
                    time.sleep(random.uniform(0.1, 0.5))

                    if random.random() < 0.7:  # 70% 成功率
                        self.logger.info(f"DNS外泄成功: 数据块 {chunk[:20]}...",
                                       extra={"stage": "exfiltration"})
                    else:
                        self.logger.warning("DNS外泄失败: 查询被阻挡",
                                          extra={"stage": "exfiltration"})
                        return False

            except Exception as e:
                self.logger.error(f"DNS外泄异常: {e}", extra={"stage": "exfiltration"})
                return False

        return True

    def _exfiltrate_via_icmp(self, data: List[Dict[str, Any]]) -> bool:
        """通过ICMP外泄数据"""
        self.logger.info("通过ICMP通道外泄数据", extra={"stage": "exfiltration"})

        # ICMP外泄通常用于小量数据
        icmp_mtu = 1472  # ICMP最大传输单元

        for item in data:
            try:
                # 分块数据
                chunks = self._chunk_data(item["content"], icmp_mtu)

                for chunk in chunks:
                    # 模拟ICMP包发送
                    time.sleep(random.uniform(0.2, 0.8))

                    if random.random() < 0.6:  # 60% 成功率（ICMP容易被过滤）
                        self.logger.info(f"ICMP外泄成功: 发送 {len(chunk)} 字节数据",
                                       extra={"stage": "exfiltration"})
                    else:
                        self.logger.warning("ICMP外泄失败: 包被防火墙阻挡",
                                          extra={"stage": "exfiltration"})
                        return False

            except Exception as e:
                self.logger.error(f"ICMP外泄异常: {e}", extra={"stage": "exfiltration"})
                return False

        return True

    def _exfiltrate_via_smtp(self, data: List[Dict[str, Any]]) -> bool:
        """通过SMTP外泄数据"""
        self.logger.info("通过SMTP通道外泄数据", extra={"stage": "exfiltration"})

        smtp_server = self.config.get("exfiltration", {}).get("smtp_server", "smtp.example.com")

        for item in data:
            try:
                # 将数据编码为邮件附件
                encoded_data = self._encode_data(item)

                # 模拟SMTP发送
                time.sleep(random.uniform(1.0, 3.0))

                if random.random() < 0.8:  # 80% 成功率
                    self.logger.info(f"SMTP外泄成功: {item['type']} 数据作为邮件发送",
                                   extra={"stage": "exfiltration"})
                else:
                    self.logger.warning("SMTP外泄失败: 邮件被反垃圾邮件系统拦截",
                                      extra={"stage": "exfiltration"})
                    return False

            except Exception as e:
                self.logger.error(f"SMTP外泄异常: {e}", extra={"stage": "exfiltration"})
                return False

        return True

    def _generate_mock_data(self, data_type: str) -> str:
        """生成模拟数据"""
        if data_type == "user_credentials":
            return json.dumps({
                "username": "admin",
                "password": "P@ssw0rd123",
                "email": "admin@company.com"
            })
        elif data_type == "database_records":
            return json.dumps([
                {"id": 1, "name": "John Doe", "ssn": "123-45-6789"},
                {"id": 2, "name": "Jane Smith", "ssn": "987-65-4321"}
            ])
        elif data_type == "financial_data":
            return json.dumps({
                "account": "123456789",
                "balance": 1000000.00,
                "transactions": ["deposit", "withdrawal", "transfer"]
            })
        elif data_type == "intellectual_property":
            return "Company proprietary algorithm: for(i=0;i<n;i++) { result += data[i] * weights[i]; }"
        elif data_type == "system_configuration":
            return json.dumps({
                "database_host": "db.internal.company.com",
                "api_keys": ["key1", "key2", "key3"],
                "admin_users": ["admin", "root"]
            })
        elif data_type == "email_data":
            return json.dumps({
                "from": "ceo@company.com",
                "to": "partner@external.com",
                "subject": "Confidential Merger Discussion",
                "body": "The merger will be announced next quarter..."
            })
        else:
            return f"Mock data for {data_type}"

    def _encode_data(self, data_item: Dict[str, Any]) -> str:
        """编码数据用于传输"""
        data_str = json.dumps(data_item)
        return base64.b64encode(data_str.encode()).decode()

    def _encode_for_dns(self, data: str) -> List[str]:
        """将数据编码为DNS查询格式"""
        encoded = base64.b32encode(data.encode()).decode()
        return [encoded[i:i+63] for i in range(0, len(encoded), 63)]

    def _chunk_data(self, data: str, chunk_size: int) -> List[str]:
        """将数据分块"""
        return [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]

    def get_exfiltration_stats(self) -> Dict[str, Any]:
        """获取外泄统计信息"""
        return self.exfiltration_stats.copy()

    def reset_stats(self):
        """重置统计信息"""
        self.exfiltration_stats = {
            "total_data_collected": 0,
            "data_exfiltrated": 0,
            "methods_used": [],
            "failed_attempts": 0
        }
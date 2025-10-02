#!/usr/bin/env python3
"""
Gophish钓鱼平台集成模块
Gophish Phishing Platform Integration Module

该模块负责与Gophish钓鱼平台的集成，实现自动化钓鱼活动管理
"""

import requests
import json
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

class GophishIntegration:
    """
    Gophish钓鱼平台集成类
    """

    def __init__(self, config_path: str = "automation_frameworks/gophish_config.json"):
        """
        初始化Gophish集成

        Args:
            config_path: Gophish配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.api_key = ""
        self.api_url = ""
        self.logger = logging.getLogger(__name__)

        self._load_config()
        self._setup_logging()

    def _load_config(self):
        """加载Gophish配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            self.api_key = self.config.get("api_key", "")
            self.api_url = self.config.get("api_url", "http://localhost:3333/api")
            self.logger.info("Gophish配置加载成功")

        except Exception as e:
            self.logger.error(f"Gophish配置加载失败: {e}")
            raise

    def _setup_logging(self):
        """设置日志"""
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """
        发送API请求

        Args:
            method: HTTP方法
            endpoint: API端点
            data: 请求数据

        Returns:
            API响应
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {e}")
            return {}

    def create_smtp_profile(self, smtp_config: Dict) -> Optional[int]:
        """
        创建SMTP配置

        Args:
            smtp_config: SMTP配置字典

        Returns:
            SMTP配置ID
        """
        self.logger.info("创建SMTP配置")

        response = self._make_request("POST", "smtp", smtp_config)
        if response:
            smtp_id = response.get("id")
            self.logger.info(f"SMTP配置创建成功，ID: {smtp_id}")
            return smtp_id

        self.logger.error("SMTP配置创建失败")
        return None

    def create_email_template(self, template_config: Dict) -> Optional[int]:
        """
        创建邮件模板

        Args:
            template_config: 邮件模板配置

        Returns:
            模板ID
        """
        self.logger.info("创建邮件模板")

        response = self._make_request("POST", "templates", template_config)
        if response:
            template_id = response.get("id")
            self.logger.info(f"邮件模板创建成功，ID: {template_id}")
            return template_id

        self.logger.error("邮件模板创建失败")
        return None

    def create_landing_page(self, page_config: Dict) -> Optional[int]:
        """
        创建着陆页

        Args:
            page_config: 着陆页配置

        Returns:
            着陆页ID
        """
        self.logger.info("创建着陆页")

        response = self._make_request("POST", "pages", page_config)
        if response:
            page_id = response.get("id")
            self.logger.info(f"着陆页创建成功，ID: {page_id}")
            return page_id

        self.logger.error("着陆页创建失败")
        return None

    def create_user_group(self, group_config: Dict) -> Optional[int]:
        """
        创建用户组

        Args:
            group_config: 用户组配置

        Returns:
            用户组ID
        """
        self.logger.info("创建用户组")

        response = self._make_request("POST", "groups", group_config)
        if response:
            group_id = response.get("id")
            self.logger.info(f"用户组创建成功，ID: {group_id}")
            return group_id

        self.logger.error("用户组创建失败")
        return None

    def create_phishing_campaign(self, campaign_config: Dict) -> Optional[int]:
        """
        创建钓鱼活动

        Args:
            campaign_config: 钓鱼活动配置

        Returns:
            活动ID
        """
        self.logger.info("创建钓鱼活动")

        response = self._make_request("POST", "campaigns", campaign_config)
        if response:
            campaign_id = response.get("id")
            self.logger.info(f"钓鱼活动创建成功，ID: {campaign_id}")
            return campaign_id

        self.logger.error("钓鱼活动创建失败")
        return None

    def launch_campaign(self, campaign_id: int) -> bool:
        """
        启动钓鱼活动

        Args:
            campaign_id: 活动ID

        Returns:
            是否启动成功
        """
        self.logger.info(f"启动钓鱼活动: {campaign_id}")

        # 获取活动详情
        campaign = self._make_request("GET", f"campaigns/{campaign_id}")
        if not campaign:
            self.logger.error("获取活动详情失败")
            return False

        # 更新活动状态为启动
        campaign["status"] = "In progress"
        campaign["launch_date"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        response = self._make_request("PUT", f"campaigns/{campaign_id}", campaign)
        if response:
            self.logger.info("钓鱼活动启动成功")
            return True

        self.logger.error("钓鱼活动启动失败")
        return False

    def get_campaign_results(self, campaign_id: int) -> Dict:
        """
        获取钓鱼活动结果

        Args:
            campaign_id: 活动ID

        Returns:
            活动结果
        """
        self.logger.info(f"获取钓鱼活动结果: {campaign_id}")

        results = self._make_request("GET", f"campaigns/{campaign_id}/results")
        if results:
            self.logger.info(f"成功获取活动结果: {len(results)} 条记录")
            return results

        self.logger.error("获取活动结果失败")
        return {}

    def setup_phishing_infrastructure(self) -> Dict[str, Any]:
        """
        设置完整的钓鱼基础设施

        Returns:
            基础设施配置信息
        """
        self.logger.info("开始设置钓鱼基础设施")

        infrastructure = {}

        # 1. 创建SMTP配置
        smtp_config = {
            "name": "SEED Mail Server",
            "host": "mail-qq-tencent",
            "from_address": "security@chrome-update.com",
            "username": "admin",
            "password": "password",
            "port": 25,
            "encryption": "none"
        }

        smtp_id = self.create_smtp_profile(smtp_config)
        if smtp_id:
            infrastructure["smtp_id"] = smtp_id

        # 2. 创建邮件模板
        template_config = {
            "name": "Chrome 浏览器更新通知",
            "subject": "您的 Chrome 浏览器需要立即更新",
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #4285f4, #34a853); padding: 20px; text-align: center; border-radius: 10px 10px 0 0;">
                    <img src="https://www.google.com/chrome/static/images/chrome-logo.svg" alt="Chrome Logo" style="width: 60px; height: 60px;">
                    <h1 style="color: white; margin: 10px 0; font-size: 24px;">Chrome 浏览器安全更新</h1>
                </div>
                <div style="background: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="color: #202124; margin-bottom: 20px;">重要安全更新通知</h2>
                    <p style="color: #5f6368; line-height: 1.6; margin-bottom: 20px;">
                        尊敬的用户，
                    </p>
                    <p style="color: #5f6368; line-height: 1.6; margin-bottom: 20px;">
                        我们检测到您的 Chrome 浏览器版本过低，存在严重安全漏洞。为保障您的账户和数据安全，请立即更新到最新版本。
                    </p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{.URL}}" style="background: linear-gradient(45deg, #4285f4, #34a853); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block; box-shadow: 0 4px 15px rgba(66, 133, 244, 0.3);">立即更新 Chrome 浏览器</a>
                    </div>
                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 15px; margin: 20px 0;">
                        <strong style="color: #856404;">安全提醒：</strong>
                        此次更新修复了多个高危安全漏洞，包括可能导致远程代码执行的 CVE-2023-4863 漏洞。
                    </div>
                    <p style="color: #5f6368; line-height: 1.6; margin-bottom: 20px;">
                        更新过程只需几分钟，不会影响您的正常使用。
                    </p>
                    <p style="color: #5f6368; line-height: 1.6;">
                        感谢您的配合！<br>
                        <strong>Chrome 安全团队</strong>
                    </p>
                </div>
            </body>
            </html>
            """,
            "text": """Chrome 浏览器安全更新通知

尊敬的用户，

我们检测到您的 Chrome 浏览器版本过低，存在严重安全漏洞。为保障您的账户和数据安全，请立即更新到最新版本。

请点击以下链接下载最新版 Chrome 浏览器：
{{.URL}}

此次更新修复了多个高危安全漏洞，包括可能导致远程代码执行的 CVE-2023-4863 漏洞。

更新过程只需几分钟，不会影响您的正常使用。

感谢您的配合！
Chrome 安全团队"""
        }

        template_id = self.create_email_template(template_config)
        if template_id:
            infrastructure["template_id"] = template_id

        # 3. 创建着陆页
        page_config = {
            "name": "Chrome 下载页面",
            "html": """
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Chrome 浏览器 - 官方下载</title>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        padding: 20px;
                    }
                    .container {
                        background: white;
                        border-radius: 15px;
                        box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                        padding: 40px;
                        text-align: center;
                        max-width: 500px;
                        width: 100%;
                    }
                    .logo { width: 80px; margin-bottom: 20px; }
                    .title { font-size: 28px; font-weight: 600; color: #202124; margin-bottom: 10px; }
                    .subtitle { color: #5f6368; font-size: 16px; margin-bottom: 30px; line-height: 1.5; }
                    .download-section { background: #f8f9fa; border-radius: 10px; padding: 30px; margin: 30px 0; }
                    .version-info { color: #5f6368; font-size: 14px; margin-bottom: 20px; }
                    .download-btn {
                        display: inline-block;
                        background: linear-gradient(45deg, #4285f4, #34a853);
                        color: white;
                        text-decoration: none;
                        padding: 16px 32px;
                        border-radius: 8px;
                        font-weight: 600;
                        font-size: 16px;
                        transition: all 0.3s ease;
                        box-shadow: 0 4px 15px rgba(66, 133, 244, 0.3);
                        margin-bottom: 20px;
                    }
                    .download-btn:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(66, 133, 244, 0.4); }
                    .progress-bar { width: 100%; height: 4px; background: #e9ecef; border-radius: 2px; margin: 20px 0; overflow: hidden; display: none; }
                    .progress-fill { height: 100%; background: linear-gradient(90deg, #4285f4, #34a853); width: 0%; transition: width 0.3s ease; }
                    .status-text { color: #5f6368; font-size: 14px; margin-top: 10px; display: none; }
                    .security-notice { background: #e8f5e8; border: 1px solid #c3e6c3; border-radius: 6px; padding: 15px; margin-top: 20px; font-size: 14px; color: #2d5a2d; }
                    .security-notice strong { color: #1b4d1b; }
                    .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; color: #5f6368; font-size: 12px; }
                    .footer a { color: #4285f4; text-decoration: none; }
                    .footer a:hover { text-decoration: underline; }
                    @keyframes download { 0% { width: 0%; } 100% { width: 100%; } }
                </style>
            </head>
            <body>
                <div class="container">
                    <img src="https://www.google.com/chrome/static/images/chrome-logo.svg" alt="Chrome Logo" class="logo">
                    <h1 class="title">Chrome 浏览器</h1>
                    <p class="subtitle">下载最新版本，享受更安全、更快速的浏览体验</p>
                    <div class="download-section">
                        <div class="version-info">版本: 118.0.5993.117 | 文件大小: 64.8 MB</div>
                        <a href="{{.URL}}" class="download-btn" id="downloadBtn"><span id="btnText">🚀 开始下载</span></a>
                        <div class="progress-bar" id="progressBar"><div class="progress-fill" id="progressFill"></div></div>
                        <div class="status-text" id="statusText">正在准备下载...</div>
                    </div>
                    <div class="security-notice">
                        <strong>🔒 安全下载：</strong>此文件来自 Google 官方服务器，已通过安全验证。下载完成后，请按照安装向导完成更新。
                    </div>
                    <div class="footer">
                        <p>需要帮助？访问 <a href="https://support.google.com/chrome" target="_blank">Chrome 帮助中心</a><br>© 2023 Google LLC. All rights reserved.</p>
                    </div>
                </div>
                <script>
                    document.getElementById('downloadBtn').addEventListener('click', function(e) {
                        e.preventDefault();
                        const btn = document.getElementById('downloadBtn');
                        const btnText = document.getElementById('btnText');
                        const progressBar = document.getElementById('progressBar');
                        const progressFill = document.getElementById('progressFill');
                        const statusText = document.getElementById('statusText');
                        progressBar.style.display = 'block';
                        statusText.style.display = 'block';
                        let progress = 0;
                        const interval = setInterval(() => {
                            progress += Math.random() * 15;
                            if (progress > 100) progress = 100;
                            progressFill.style.width = progress + '%';
                            if (progress < 30) statusText.textContent = '正在连接服务器...';
                            else if (progress < 70) statusText.textContent = '正在下载文件...';
                            else if (progress < 90) statusText.textContent = '正在验证文件...';
                            else statusText.textContent = '下载完成！';
                            if (progress >= 100) {
                                clearInterval(interval);
                                btnText.textContent = '✅ 下载完成';
                                btn.style.background = 'linear-gradient(45deg, #34a853, #4285f4)';
                                setTimeout(() => {
                                    statusText.textContent = '正在启动安装程序...';
                                    setTimeout(() => { window.location.href = '{{.URL}}'; }, 1000);
                                }, 3000);
                            }
                        }, 200);
                    });
                </script>
            </body>
            </html>
            """,
            "redirect_url": "https://www.google.cn/chrome/"
        }

        page_id = self.create_landing_page(page_config)
        if page_id:
            infrastructure["page_id"] = page_id

        # 4. 创建用户组
        group_config = {
            "name": "目标用户组",
            "targets": [
                {"first_name": "张", "last_name": "三", "email": "zhangsan@163.com", "position": "财务部经理"},
                {"first_name": "李", "last_name": "四", "email": "lisi@qq.com", "position": "IT管理员"},
                {"first_name": "王", "last_name": "五", "email": "wangwu@gmail.com", "position": "人力资源总监"},
                {"first_name": "赵", "last_name": "六", "email": "zhaoliu@company.cn", "position": "市场部主管"},
                {"first_name": "钱", "last_name": "七", "email": "qianqi@outlook.com", "position": "销售总监"}
            ]
        }

        group_id = self.create_user_group(group_config)
        if group_id:
            infrastructure["group_id"] = group_id

        self.logger.info("钓鱼基础设施设置完成")
        return infrastructure

    def run_phishing_campaign(self, infrastructure: Dict[str, Any]) -> Dict[str, Any]:
        """
        运行钓鱼活动

        Args:
            infrastructure: 基础设施配置

        Returns:
            活动结果
        """
        self.logger.info("开始运行钓鱼活动")

        # 创建钓鱼活动配置
        campaign_config = {
            "name": "Chrome 浏览器更新钓鱼活动",
            "template": infrastructure["template_id"],
            "url": "http://localhost:8080/chrome-update",
            "page": infrastructure["page_id"],
            "smtp": infrastructure["smtp_id"],
            "groups": [infrastructure["group_id"]],
            "launch_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        # 创建活动
        campaign_id = self.create_phishing_campaign(campaign_config)
        if not campaign_id:
            return {"success": False, "error": "活动创建失败"}

        # 启动活动
        if not self.launch_campaign(campaign_id):
            return {"success": False, "error": "活动启动失败"}

        # 等待一段时间让活动运行
        self.logger.info("等待钓鱼活动执行...")
        time.sleep(10)  # 实际环境中可能需要更长时间

        # 获取结果
        results = self.get_campaign_results(campaign_id)

        return {
            "success": True,
            "campaign_id": campaign_id,
            "results": results
        }


if __name__ == "__main__":
    # 测试Gophish集成
    gophish = GophishIntegration()

    # 设置基础设施
    infrastructure = gophish.setup_phishing_infrastructure()
    print(f"基础设施设置完成: {infrastructure}")

    # 运行钓鱼活动
    if infrastructure:
        results = gophish.run_phishing_campaign(infrastructure)
        print(f"钓鱼活动结果: {results}")
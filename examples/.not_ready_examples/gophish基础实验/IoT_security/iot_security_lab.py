#!/usr/bin/env python
"""
IoT安全实验室
物联网设备安全测试和漏洞研究平台
包含智能设备模拟、固件分析、无线安全测试
"""

import os
import json
import time
import random
import sqlite3
import threading
import subprocess
from datetime import datetime
from flask import Flask, request, render_template_string, jsonify, send_file
import hashlib
import struct
import socket

class IoTSecurityLab:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.devices = {}
        self.vulnerabilities = {}
        self.setup_database()
        self.create_virtual_devices()
        
    def setup_database(self):
        """初始化IoT安全数据库"""
        conn = sqlite3.connect('iot_security.db')
        cursor = conn.cursor()
        
        # IoT设备表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iot_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_type TEXT NOT NULL,
                ip_address TEXT,
                mac_address TEXT,
                firmware_version TEXT,
                manufacturer TEXT,
                model TEXT,
                services TEXT,
                vulnerabilities TEXT,
                status TEXT DEFAULT 'active',
                last_seen TEXT,
                security_score INTEGER DEFAULT 50
            )
        ''')
        
        # 固件分析表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS firmware_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id INTEGER,
                firmware_file TEXT,
                file_hash TEXT,
                analysis_time TEXT,
                extracted_files INTEGER DEFAULT 0,
                passwords_found TEXT,
                hardcoded_keys TEXT,
                vulnerabilities_found TEXT,
                security_issues TEXT,
                FOREIGN KEY (device_id) REFERENCES iot_devices (id)
            )
        ''')
        
        # 网络扫描结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_time TEXT NOT NULL,
                target_range TEXT,
                devices_found INTEGER DEFAULT 0,
                open_ports TEXT,
                services_detected TEXT,
                vulnerabilities TEXT,
                scan_type TEXT
            )
        ''')
        
        # 无线安全测试表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wireless_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_time TEXT NOT NULL,
                network_ssid TEXT,
                encryption_type TEXT,
                signal_strength INTEGER,
                test_type TEXT,
                result TEXT,
                vulnerabilities TEXT,
                captured_handshakes INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_virtual_devices(self):
        """创建虚拟IoT设备"""
        devices = [
            {
                "name": "Smart Camera 01",
                "type": "IP Camera",
                "ip": "192.168.1.150",
                "mac": "00:11:22:33:44:55",
                "firmware": "v2.1.4",
                "manufacturer": "HikVision",
                "model": "DS-2CD2043G0",
                "services": "http:80,rtsp:554,telnet:23",
                "vulnerabilities": "CVE-2021-36260,CVE-2020-25227"
            },
            {
                "name": "Smart Doorbell",
                "type": "Doorbell",
                "ip": "192.168.1.151", 
                "mac": "AA:BB:CC:DD:EE:FF",
                "firmware": "v1.8.2",
                "manufacturer": "Ring",
                "model": "Video Doorbell Pro",
                "services": "http:80,https:443",
                "vulnerabilities": "CVE-2019-9948"
            },
            {
                "name": "Smart Thermostat",
                "type": "Thermostat",
                "ip": "192.168.1.152",
                "mac": "11:22:33:44:55:66",
                "firmware": "v3.2.1",
                "manufacturer": "Nest",
                "model": "Learning Thermostat",
                "services": "http:80,coap:5683",
                "vulnerabilities": "Weak Authentication"
            },
            {
                "name": "Smart Router",
                "type": "Router",
                "ip": "192.168.1.1",
                "mac": "FF:EE:DD:CC:BB:AA",
                "firmware": "v1.1.0",
                "manufacturer": "D-Link",
                "model": "DIR-882",
                "services": "http:80,ssh:22,telnet:23",
                "vulnerabilities": "CVE-2022-26258,Default Credentials"
            }
        ]
        
        conn = sqlite3.connect('iot_security.db')
        cursor = conn.cursor()
        
        for device in devices:
            cursor.execute('''
                INSERT OR REPLACE INTO iot_devices 
                (device_name, device_type, ip_address, mac_address, firmware_version, 
                 manufacturer, model, services, vulnerabilities, last_seen, security_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (device["name"], device["type"], device["ip"], device["mac"],
                  device["firmware"], device["manufacturer"], device["model"],
                  device["services"], device["vulnerabilities"],
                  datetime.now().isoformat(), random.randint(20, 80)))
        
        conn.commit()
        conn.close()

app = Flask(__name__)
iot_lab = IoTSecurityLab()

# IoT安全实验室页面模板
IOT_LAB_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>IoT安全实验室</title>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
        .header { background: linear-gradient(135deg, #16213e, #0f3460); color: #e94560; padding: 20px; margin: -20px -20px 20px -20px; text-align: center; }
        .container { max-width: 1400px; margin: 0 auto; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
        .panel { background: #16213e; padding: 20px; border-radius: 10px; border: 1px solid #0f3460; }
        .device-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
        .device-card { background: #0f3460; padding: 15px; border-radius: 8px; border-left: 4px solid #e94560; transition: all 0.3s; }
        .device-card:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(233, 69, 96, 0.3); }
        .device-secure { border-left-color: #4caf50; }
        .device-warning { border-left-color: #ff9800; }
        .device-critical { border-left-color: #f44336; }
        .btn { background: #e94560; color: white; padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; margin: 3px; font-size: 12px; }
        .btn:hover { background: #d63554; }
        .btn-scan { background: #2196f3; }
        .btn-analyze { background: #ff9800; }
        .btn-exploit { background: #f44336; }
        .scan-results { background: #0f1419; padding: 15px; border-radius: 5px; font-family: monospace; font-size: 12px; margin: 10px 0; max-height: 300px; overflow-y: auto; }
        .vuln-item { background: #2d1b69; padding: 8px; margin: 5px 0; border-radius: 3px; border-left: 3px solid #e94560; }
        .vuln-critical { border-left-color: #f44336; background: #3d1a16; }
        .vuln-high { border-left-color: #ff9800; background: #3d2817; }
        .vuln-medium { border-left-color: #ffeb3b; background: #3d3617; }
        .vuln-low { border-left-color: #4caf50; background: #1e3d17; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }
        .stat-card { background: #0f3460; padding: 15px; border-radius: 5px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
        .stat-label { font-size: 12px; opacity: 0.8; }
        .firmware-analysis { background: #1a1a2e; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .wireless-network { background: #2d1b69; padding: 10px; border-radius: 5px; margin: 5px 0; }
        .signal-strength { display: inline-block; width: 100px; height: 10px; background: #333; border-radius: 5px; overflow: hidden; }
        .signal-fill { height: 100%; background: linear-gradient(90deg, #4caf50, #ffeb3b, #f44336); }
        .exploit-demo { background: #3d1a16; padding: 15px; border-radius: 5px; border: 1px solid #f44336; margin: 10px 0; }
        .code-block { background: #0f1419; padding: 10px; border-radius: 3px; font-family: monospace; font-size: 11px; margin: 5px 0; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 IoT安全实验室</h1>
            <p>物联网设备安全测试 • 固件分析 • 无线安全评估</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value" style="color: #e94560;">{{ stats.total_devices }}</div>
                <div class="stat-label">发现设备</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #f44336;">{{ stats.vulnerable_devices }}</div>
                <div class="stat-label">存在漏洞</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #ff9800;">{{ stats.firmware_analyzed }}</div>
                <div class="stat-label">固件分析</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #4caf50;">{{ stats.security_patches }}</div>
                <div class="stat-label">安全补丁</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="panel">
                <h3>🔍 网络扫描</h3>
                <div>
                    <button class="btn btn-scan" onclick="startNetworkScan()">🌐 网络发现</button>
                    <button class="btn btn-scan" onclick="portScan()">🔌 端口扫描</button>
                    <button class="btn btn-scan" onclick="serviceScan()">⚙️ 服务识别</button>
                    <button class="btn btn-scan" onclick="vulnScan()">🚨 漏洞扫描</button>
                </div>
                
                <div class="scan-results" id="scanResults">
                    <div>正在初始化网络扫描模块...</div>
                    <div>扫描目标: 192.168.1.0/24</div>
                    <div>准备就绪，等待用户指令</div>
                </div>
            </div>
            
            <div class="panel">
                <h3>📡 无线安全测试</h3>
                <div>
                    <button class="btn btn-scan" onclick="wifiScan()">📶 WiFi扫描</button>
                    <button class="btn btn-analyze" onclick="analyzeEncryption()">🔐 加密分析</button>
                    <button class="btn btn-exploit" onclick="wifiAttack()">⚡ WiFi攻击</button>
                    <button class="btn" onclick="captureHandshake()">🤝 握手包捕获</button>
                </div>
                
                <div id="wirelessNetworks">
                    {% for network in wireless_networks %}
                    <div class="wireless-network">
                        <strong>{{ network.ssid }}</strong>
                        <span style="float: right;">{{ network.encryption }}</span>
                        <br>
                        <div class="signal-strength">
                            <div class="signal-fill" style="width: {{ network.signal }}%"></div>
                        </div>
                        <small>信号强度: {{ network.signal }}% | 频道: {{ network.channel }}</small>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h3>🏠 发现的IoT设备</h3>
            <div class="device-grid">
                {% for device in devices %}
                <div class="device-card device-{{ device.risk_level }}">
                    <strong>{{ device.name }}</strong>
                    <span style="float: right; color: #e94560;">{{ device.type }}</span>
                    <br><small>{{ device.manufacturer }} {{ device.model }}</small>
                    <br><small>IP: {{ device.ip }} | MAC: {{ device.mac }}</small>
                    <br><small>固件: {{ device.firmware }}</small>
                    <div style="margin-top: 8px;">
                        <button class="btn btn-analyze" onclick="analyzeFirmware({{ device.id }})">🔬 固件分析</button>
                        <button class="btn btn-exploit" onclick="exploitDevice({{ device.id }})">💥 漏洞利用</button>
                        <button class="btn" onclick="deviceInfo({{ device.id }})">ℹ️ 详情</button>
                    </div>
                    <div style="margin-top: 5px; font-size: 11px;">
                        安全评分: <strong style="color: {{ 'red' if device.security_score < 40 else 'orange' if device.security_score < 70 else 'green' }};">{{ device.security_score }}/100</strong>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        
        <div class="grid">
            <div class="panel">
                <h3>🛠️ 固件分析结果</h3>
                <div class="firmware-analysis">
                    <h4>📁 提取的文件系统</h4>
                    <div class="code-block">
                        /bin/busybox (SUID)<br>
                        /etc/passwd (默认密码)<br>
                        /etc/shadow (弱哈希)<br>
                        /root/.ssh/id_rsa (硬编码私钥)<br>
                        /usr/bin/telnetd (后门服务)<br>
                        /var/log/system.log (敏感信息)
                    </div>
                    
                    <h4>🔑 发现的凭证</h4>
                    <div class="vuln-item vuln-critical">
                        用户名: admin | 密码: 123456 (硬编码)
                    </div>
                    <div class="vuln-item vuln-high">
                        用户名: root | 密码: password (默认凭证)
                    </div>
                    <div class="vuln-item vuln-medium">
                        API密钥: AIzaSyB3KDXK... (泄露在配置文件中)
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h3>🚨 漏洞评估报告</h3>
                <div id="vulnerabilityReport">
                    {% for vuln in vulnerabilities %}
                    <div class="vuln-item vuln-{{ vuln.severity }}">
                        <strong>{{ vuln.cve_id }}</strong> - {{ vuln.title }}
                        <br><small>{{ vuln.description }}</small>
                        <br><span style="color: #ff9800;">CVSS: {{ vuln.cvss_score }}</span>
                        <button class="btn btn-exploit" onclick="exploitVuln('{{ vuln.cve_id }}')">利用</button>
                    </div>
                    {% endfor %}
                </div>
                
                <h4>🎯 攻击场景演示</h4>
                <div class="exploit-demo">
                    <strong>场景1: 智能摄像头未授权访问</strong>
                    <div class="code-block">
                        curl http://192.168.1.150/cgi-bin/hi3510/snap.cgi?&-usr=admin&-pwd=
                        # 成功获取实时截图，无需认证
                    </div>
                </div>
                
                <div class="exploit-demo">
                    <strong>场景2: 路由器命令注入</strong>
                    <div class="code-block">
                        POST /cgi-bin/mainfunction.cgi
                        command=ping;cat /etc/passwd
                        # 执行任意系统命令
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function startNetworkScan() {
            addScanResult('开始网络发现扫描...');
            
            setTimeout(() => {
                addScanResult('发现设备: 192.168.1.150 (Smart Camera)');
                addScanResult('发现设备: 192.168.1.151 (Smart Doorbell)');
                addScanResult('发现设备: 192.168.1.152 (Smart Thermostat)');
                addScanResult('发现设备: 192.168.1.1 (Smart Router)');
                addScanResult('网络扫描完成，发现4个IoT设备');
            }, 2000);
        }
        
        function portScan() {
            addScanResult('开始端口扫描...');
            
            setTimeout(() => {
                addScanResult('192.168.1.150: 端口80(HTTP), 554(RTSP), 23(Telnet) 开放');
                addScanResult('192.168.1.151: 端口80(HTTP), 443(HTTPS) 开放');
                addScanResult('192.168.1.152: 端口80(HTTP), 5683(CoAP) 开放');
                addScanResult('192.168.1.1: 端口80(HTTP), 22(SSH), 23(Telnet) 开放');
            }, 1500);
        }
        
        function serviceScan() {
            addScanResult('开始服务识别...');
            
            setTimeout(() => {
                addScanResult('192.168.1.150: Hikvision IP Camera Web Service 2.1.4');
                addScanResult('192.168.1.151: Ring Video Doorbell API v1.8.2');
                addScanResult('192.168.1.152: Nest Thermostat Control Interface');
                addScanResult('192.168.1.1: D-Link Router Web Management');
            }, 2000);
        }
        
        function vulnScan() {
            addScanResult('开始漏洞扫描...');
            
            setTimeout(() => {
                addScanResult('⚠️ 192.168.1.150: CVE-2021-36260 (认证绕过)');
                addScanResult('⚠️ 192.168.1.151: CVE-2019-9948 (权限提升)');
                addScanResult('⚠️ 192.168.1.152: 弱认证机制');
                addScanResult('🚨 192.168.1.1: CVE-2022-26258 (远程代码执行)');
                addScanResult('漏洞扫描完成，发现4个安全问题');
            }, 3000);
        }
        
        function wifiScan() {
            alert('WiFi扫描完成，发现5个无线网络');
        }
        
        function analyzeEncryption() {
            alert('加密分析：发现1个WEP网络，2个WPA2网络存在弱密码');
        }
        
        function wifiAttack() {
            alert('WiFi攻击演示：成功破解WEP密钥，获得网络访问权限');
        }
        
        function captureHandshake() {
            alert('握手包捕获：成功捕获WPA2四次握手，可用于离线破解');
        }
        
        function analyzeFirmware(deviceId) {
            alert('固件分析开始，预计需要5分钟...');
        }
        
        function exploitDevice(deviceId) {
            alert('漏洞利用成功！获得设备控制权限');
        }
        
        function deviceInfo(deviceId) {
            alert('显示设备详细信息和安全状态');
        }
        
        function exploitVuln(cveId) {
            alert('利用漏洞 ' + cveId + ' 成功！');
        }
        
        function addScanResult(message) {
            const resultsContainer = document.getElementById('scanResults');
            const result = document.createElement('div');
            result.textContent = '[' + new Date().toLocaleTimeString() + '] ' + message;
            resultsContainer.appendChild(result);
            resultsContainer.scrollTop = resultsContainer.scrollHeight;
        }
        
        // 模拟实时更新
        setInterval(() => {
            fetch('/api/iot_status')
                .then(response => response.json())
                .then(data => {
                    // 更新设备状态
                });
        }, 10000);
    </script>
</body>
</html>
"""

@app.route('/')
def iot_dashboard():
    """IoT安全实验室主界面"""
    conn = sqlite3.connect('iot_security.db')
    cursor = conn.cursor()
    
    # 获取设备列表
    cursor.execute('SELECT * FROM iot_devices')
    device_rows = cursor.fetchall()
    
    devices = []
    for row in device_rows:
        risk_level = 'critical' if row[12] < 40 else 'warning' if row[12] < 70 else 'secure'
        devices.append({
            'id': row[0],
            'name': row[1],
            'type': row[2],
            'ip': row[3],
            'mac': row[4][:8] + '...',
            'firmware': row[5],
            'manufacturer': row[6],
            'model': row[7],
            'security_score': row[12],
            'risk_level': risk_level
        })
    
    # 模拟无线网络
    wireless_networks = [
        {'ssid': 'SmartHome_5G', 'encryption': 'WPA2', 'signal': 85, 'channel': 36},
        {'ssid': 'IoT_Devices', 'encryption': 'WEP', 'signal': 62, 'channel': 6},
        {'ssid': 'NETGEAR_Guest', 'encryption': 'Open', 'signal': 45, 'channel': 11},
        {'ssid': 'Ring_Network', 'encryption': 'WPA2', 'signal': 78, 'channel': 1},
        {'ssid': 'Nest_Secure', 'encryption': 'WPA3', 'signal': 92, 'channel': 149}
    ]
    
    # 模拟漏洞数据
    vulnerabilities = [
        {
            'cve_id': 'CVE-2021-36260',
            'title': 'Hikvision Camera Authentication Bypass',
            'description': '海康威视摄像头认证绕过漏洞',
            'severity': 'critical',
            'cvss_score': 9.8
        },
        {
            'cve_id': 'CVE-2022-26258',
            'title': 'D-Link Router Remote Code Execution',
            'description': 'D-Link路由器远程代码执行漏洞',
            'severity': 'critical',
            'cvss_score': 9.0
        },
        {
            'cve_id': 'CVE-2019-9948',
            'title': 'Ring Doorbell Privilege Escalation',
            'description': 'Ring门铃设备权限提升漏洞',
            'severity': 'high',
            'cvss_score': 7.5
        }
    ]
    
    # 统计数据
    stats = {
        'total_devices': len(devices),
        'vulnerable_devices': len([d for d in devices if d['security_score'] < 70]),
        'firmware_analyzed': random.randint(8, 15),
        'security_patches': random.randint(3, 8)
    }
    
    conn.close()
    
    return render_template_string(IOT_LAB_TEMPLATE,
                                 devices=devices,
                                 wireless_networks=wireless_networks,
                                 vulnerabilities=vulnerabilities,
                                 stats=stats)

@app.route('/api/iot_status')
def get_iot_status():
    """获取IoT状态"""
    return jsonify({
        "status": "running",
        "devices_online": random.randint(3, 6),
        "new_vulnerabilities": random.randint(0, 2)
    })

@app.route('/api/network_scan', methods=['POST'])
def network_scan():
    """网络扫描"""
    data = request.json
    scan_type = data.get('type', 'discovery')
    
    # 模拟扫描结果
    results = {
        'discovery': [
            '192.168.1.150 - Smart Camera (Hikvision)',
            '192.168.1.151 - Smart Doorbell (Ring)',
            '192.168.1.152 - Smart Thermostat (Nest)',
            '192.168.1.1 - Smart Router (D-Link)'
        ],
        'port': [
            '192.168.1.150: 80/HTTP, 554/RTSP, 23/Telnet',
            '192.168.1.151: 80/HTTP, 443/HTTPS',
            '192.168.1.152: 80/HTTP, 5683/CoAP',
            '192.168.1.1: 80/HTTP, 22/SSH, 23/Telnet'
        ],
        'vulnerability': [
            'CVE-2021-36260: Hikvision Camera Auth Bypass',
            'CVE-2022-26258: D-Link Router RCE',
            'CVE-2019-9948: Ring Doorbell Privilege Escalation',
            'Default Credentials: Multiple devices'
        ]
    }
    
    return jsonify({
        "success": True,
        "results": results.get(scan_type, [])
    })

@app.route('/api/firmware_analysis', methods=['POST'])
def firmware_analysis():
    """固件分析"""
    data = request.json
    device_id = data.get('device_id')
    
    # 模拟固件分析结果
    analysis_result = {
        "extracted_files": 156,
        "passwords_found": ["admin:123456", "root:password", "user:user"],
        "hardcoded_keys": ["AIzaSyB3KDXK...", "sk_test_123..."],
        "vulnerabilities": [
            "Buffer Overflow in HTTP server",
            "Command Injection in web interface",
            "Weak cryptographic implementation"
        ],
        "security_score": random.randint(20, 60)
    }
    
    return jsonify({
        "success": True,
        "analysis": analysis_result
    })

@app.route('/api/exploit_device', methods=['POST'])
def exploit_device():
    """设备漏洞利用"""
    data = request.json
    device_id = data.get('device_id')
    
    # 模拟漏洞利用
    exploit_results = [
        "成功绕过认证，获得管理员权限",
        "执行任意命令，控制设备功能",
        "访问敏感文件，获取配置信息",
        "建立后门连接，维持持久访问"
    ]
    
    return jsonify({
        "success": True,
        "result": random.choice(exploit_results),
        "evidence": "截图已保存，日志已记录"
    })

if __name__ == '__main__':
    print("🏠 启动IoT安全实验室...")
    print("访问 http://localhost:5007 开始IoT安全测试")
    print("")
    print("🔧 实验功能:")
    print("  - IoT设备发现和识别")
    print("  - 网络和端口扫描")
    print("  - 固件安全分析")
    print("  - 无线网络安全测试")
    print("  - 漏洞利用演示")
    print("  - 安全评估报告")
    
    app.run(host='0.0.0.0', port=5007, debug=True)

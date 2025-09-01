#!/usr/bin/env python3
"""
30项目Flask测试脚本
"""

from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return "30项目Flask测试成功！端口5002正常运行。"

@app.route('/status')
def status():
    return "30项目状态: 网络基础设施运行中，AI服务待配置。"

if __name__ == '__main__':
    print("🎣 启动30项目Flask测试服务器...")
    print("🌐 访问地址: http://localhost:5002")
    print("📊 状态页面: http://localhost:5002/status")
    app.run(host='0.0.0.0', port=5002, debug=False)

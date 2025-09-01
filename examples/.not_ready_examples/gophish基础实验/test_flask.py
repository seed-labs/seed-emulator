#!/usr/bin/env python
"""
简单的Flask测试
"""
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>🎯 Flask测试成功！</h1><p>网络安全实验室准备就绪</p>'

if __name__ == '__main__':
    print("🚀 Flask测试服务器启动在端口 5999")
    print("访问 http://localhost:5999 查看测试页面")
    app.run(host='0.0.0.0', port=5999, debug=False)

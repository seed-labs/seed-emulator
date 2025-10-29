import os
from werkzeug.routing import BaseConverter
from flask import jsonify, send_from_directory, current_app

from ..config import Config


def serve_vue_app(path=None):
    """服务 Vue 应用的主入口"""
    try:
        # 首先尝试直接返回请求的文件
        if path and path != 'index.html':
            # 检查文件是否存在
            file_path = os.path.join(Config.FRONTEND_DIST_DIR, path)
            if os.path.isfile(file_path):
                return send_from_directory(Config.FRONTEND_DIST_DIR, path)

        # 对于前端路由，返回 Vue 的 index.html
        return send_from_directory(Config.FRONTEND_DIST_DIR, 'index.html')
    except Exception as e:
        current_app.logger.error(f"Error serving Vue app: {e}")
        return jsonify({"error": "Frontend application not available"}), 500


class RegexConverter(BaseConverter):
    """在路由中使用正则表达式的转换器"""

    def __init__(self, url_map, regex):
        super().__init__(url_map)
        self.regex = regex  # 正则表达式字符串


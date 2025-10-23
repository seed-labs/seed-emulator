import os
from flask import Blueprint, send_from_directory, redirect
from config import Config
from blueprint import serve_vue_app

base = Blueprint('base', __name__)


# 静态资源路由
@base.route('/assets/<path:filename>')
def serve_assets(filename):
    """处理 Vue 应用的静态资源"""
    return send_from_directory(os.path.join(Config.FRONTEND_DIST_DIR, 'assets'), filename)


# 其他静态文件路由（如 favicon, manifest 等）
@base.route('/<string:filename>')
def serve_root_files(filename):
    """处理根目录下的静态文件"""
    if '.' in filename:
        return send_from_directory(Config.FRONTEND_DIST_DIR, filename)
    return serve_vue_app()


@base.route('/frontend/', defaults={'path': ''})
@base.route('/frontend/<path:path>')
def serve_vue_static_path(path):
    """处理 /frontend/ 下的路径"""
    return serve_vue_app(path)


# 捕获所有未匹配路由（必须放在最后）
@base.route('/<regex(".*"):path>', defaults={'path': ''})
def catch_all(path):
    print(f'未匹配的路径: /{path}', 404)
    # return serve_vue_app(path)
    return redirect('/frontend')

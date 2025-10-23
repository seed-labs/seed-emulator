# run.py
from server import create_app

app = create_app()  # 或者直接传入配置对象
if __name__ == '__main__':
    # 开启 Flask 自带的调试器
    app.run(debug=True, host='127.0.0.1', port=3000, use_reloader=True)

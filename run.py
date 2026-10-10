"""入口脚本：启动 Flask 服务，监听 0.0.0.0:12321。"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=False)

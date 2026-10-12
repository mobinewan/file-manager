"""应用配置。从环境变量读取部署相关参数，便于 Docker 注入。"""
import os

__version__ = "v0.26.10.12"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "instance", "app.db"))
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads")
    )

    LICENSE_SUBDIR = "licenses"
    THIRD_PARTY_SUBDIR = "third_party"
    FACTORY_SUBDIR = "factory"
    EXPORTS_SUBDIR = "exports"

    ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "gif", "bmp", "webp", "doc", "docx"}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

    DEFAULT_THRESHOLD_DAYS = int(os.environ.get("DEFAULT_THRESHOLD_DAYS", 30))
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    PORT = int(os.environ.get("PORT", 12321))

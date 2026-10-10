"""文件保存与路径生成。所有相对路径基于 uploads/ 目录。"""
import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import current_app


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower().lstrip(".")
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


def save_upload(file_storage, subdir_key):
    """保存上传文件，返回相对 uploads 的路径与原始文件名。

    subdir_key 取值：LICENSE_SUBDIR / THIRD_PARTY_SUBDIR / FACTORY_SUBDIR / EXPORTS_SUBDIR
    """
    if not file_storage or not file_storage.filename:
        return None, None
    if not allowed_file(file_storage.filename):
        return None, None

    subdir = current_app.config[subdir_key]
    upload_root = current_app.config["UPLOAD_FOLDER"]
    target_dir = os.path.join(upload_root, subdir)
    os.makedirs(target_dir, exist_ok=True)

    # 始终从原始文件名提取扩展名（lowercase）。
    # 不能用 safe_name，因为 secure_filename 会清除中文等非 ASCII 字符，
    # 例如 "海天营业执照.pdf" 会被处理成 ".pdf"，此时 os.path.splitext 把它
    # 当作以点开头的隐藏文件名而非扩展名，结果返回空字符串，导致存储文件无扩展名。
    original_name = file_storage.filename
    ext = os.path.splitext(original_name)[1].lower()
    if not ext:
        ext = "." + original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""

    stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    abs_path = os.path.join(target_dir, stored_name)
    file_storage.save(abs_path)

    rel_path = os.path.join(subdir, stored_name)
    # 返回原始文件名（保留中文显示），而非 safe_name（已被清洗）
    return rel_path, original_name


def absolute_path(rel_path):
    return os.path.join(current_app.config["UPLOAD_FOLDER"], rel_path)

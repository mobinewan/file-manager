"""用户表 + 角色枚举 + 细粒度权限。"""
from datetime import datetime
from flask_login import UserMixin
from ..extensions import db


# 权限键 → 中文显示名（供用户管理界面渲染勾选框）
PERMISSIONS = [
    ("can_manage_manufacturer", "厂家管理（增/改/删）"),
    ("can_manage_product", "商品管理（增/改/删）"),
    ("can_upload_certificate", "证件上传"),
    ("can_edit_certificate", "证件信息编辑"),
    ("can_delete_certificate", "证件删除"),
]


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(16), nullable=False, default="user")  # admin / user
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # 细粒度权限（仅对普通用户生效，管理员自动拥有全部权限）
    can_manage_manufacturer = db.Column(db.Boolean, default=False, nullable=False)
    can_manage_product = db.Column(db.Boolean, default=False, nullable=False)
    can_upload_certificate = db.Column(db.Boolean, default=False, nullable=False)
    can_edit_certificate = db.Column(db.Boolean, default=False, nullable=False)
    can_delete_certificate = db.Column(db.Boolean, default=False, nullable=False)

    def set_password(self, raw):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == "admin"

    def has_perm(self, perm_name):
        """管理员默认拥有全部权限；普通用户按勾选项决定。"""
        if self.role == "admin":
            return True
        return bool(getattr(self, perm_name, False))

    def permission_map(self):
        """返回 {perm_name: bool} 字典，供 UI 渲染。"""
        return {name: (self.is_admin or bool(getattr(self, name, False))) for name, _ in PERMISSIONS}

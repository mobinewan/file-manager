"""操作日志表。记录资质上传、下载、变更等关键数据操作。"""
from datetime import datetime
from ..extensions import db


class LogEntry(db.Model):
    __tablename__ = "log_entries"

    id = db.Column(db.Integer, primary_key=True)

    # 操作信息
    action = db.Column(db.String(64), nullable=False, index=True)  # UPLOAD, DOWNLOAD, EDIT, DELETE, CREATE, UPDATE
    action_type = db.Column(db.String(32), nullable=False, index=True)  # CERTIFICATE, PRODUCT, MANUFACTURER, USER

    # 操作对象
    target_type = db.Column(db.String(64), nullable=False)  # BusinessLicense, ThirdPartyReport, Product...
    target_id = db.Column(db.Integer, nullable=True, index=True)
    target_desc = db.Column(db.Text, nullable=True)  # 便于阅读的简要描述

    # 操作人
    user_id = db.Column(db.Integer, nullable=True, index=True)
    username = db.Column(db.String(64), nullable=True)

    # 客户端信息
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    device_type = db.Column(db.String(32), nullable=True)  # Desktop, Mobile, Tablet

    # 操作结果
    status = db.Column(db.String(16), nullable=False, default="success")  # success, failed
    error_message = db.Column(db.Text, nullable=True)

    # 额外数据（JSON 格式）
    extra_data = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "action": self.action,
            "action_type": self.action_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_desc": self.target_desc,
            "user_id": self.user_id,
            "username": self.username,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "device_type": self.device_type,
            "status": self.status,
            "error_message": self.error_message,
            "extra_data": json.loads(self.extra_data) if self.extra_data else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

"""系统设置表（阈值等）。"""
from datetime import datetime
from ..extensions import db


class Setting(db.Model):
    __tablename__ = "settings"

    id = db.Column(db.Integer, primary_key=True)
    default_threshold_days = db.Column(db.Integer, default=30, nullable=False)
    enable_alert = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

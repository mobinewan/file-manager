"""厂家级证件：营业执照 + 食品经营许可证（一对一厂家）。"""
from datetime import datetime
from ..extensions import db


class BusinessLicense(db.Model):
    """营业执照。"""
    __tablename__ = "business_licenses"

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_id = db.Column(
        db.Integer, db.ForeignKey("manufacturers.id"), unique=True, nullable=False
    )
    license_no = db.Column(db.String(64))  # 执照编号
    legal_person = db.Column(db.String(64))  # 法定代表人
    issue_date = db.Column(db.Date)
    valid_until = db.Column(db.Date)  # null 视为长期有效
    file_path = db.Column(db.String(256), nullable=False)  # 相对 uploads/licenses 的路径
    file_name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class FoodLicense(db.Model):
    """食品经营许可证。"""
    __tablename__ = "food_licenses"

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_id = db.Column(
        db.Integer, db.ForeignKey("manufacturers.id"), unique=True, nullable=False
    )
    license_no = db.Column(db.String(64))
    scope = db.Column(db.String(256))  # 经营范围
    issuer = db.Column(db.String(128))  # 发证机关
    issue_date = db.Column(db.Date)
    valid_until = db.Column(db.Date)
    file_path = db.Column(db.String(256), nullable=False)
    file_name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

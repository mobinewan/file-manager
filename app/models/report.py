"""单品级报告：第三方检验报告（一段时期有效）+ 出厂检验报告（当天有效）。"""
from datetime import datetime, date
from ..extensions import db


class ThirdPartyReport(db.Model):
    """第三方检验报告。"""
    __tablename__ = "third_party_reports"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    manufacturer_id = db.Column(
        db.Integer, db.ForeignKey("manufacturers.id"), nullable=False, index=True
    )  # 冗余字段加速厂家维度查询
    report_no = db.Column(db.String(64))
    testing_org = db.Column(db.String(128))  # 检验机构
    test_date = db.Column(db.Date)
    valid_from = db.Column(db.Date)
    valid_until = db.Column(db.Date, nullable=False)  # 必填，用于到期判断
    file_path = db.Column(db.String(256), nullable=False)
    file_name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)


class FactoryReport(db.Model):
    """出厂检验报告。有效期 = 生产日期 + 产品保质期 - 1 天。

    例如：生产日期 2026-09-21，保质期 365 天 → 有效期至 2027-09-20。
    在产品过期之前，报告不会过期。
    """
    __tablename__ = "factory_reports"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    manufacturer_id = db.Column(
        db.Integer, db.ForeignKey("manufacturers.id"), nullable=False, index=True
    )
    batch_no = db.Column(db.String(64))  # 批次号
    production_date = db.Column(db.Date)  # 生产日期
    test_date = db.Column(db.Date, nullable=False)  # 检验日期
    valid_until = db.Column(db.Date, nullable=False)  # = 生产日期 + 保质期 - 1 天
    file_path = db.Column(db.String(256), nullable=False)
    file_name = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

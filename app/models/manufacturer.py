"""厂家表。"""
from datetime import datetime
from ..extensions import db


class Manufacturer(db.Model):
    __tablename__ = "manufacturers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False, index=True)
    unified_credit_code = db.Column(db.String(64))  # 统一社会信用代码
    contact_person = db.Column(db.String(64))
    contact_phone = db.Column(db.String(32))
    address = db.Column(db.String(256))
    remark = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    products = db.relationship("Product", backref="manufacturer", cascade="all, delete-orphan")
    business_license = db.relationship(
        "BusinessLicense", backref="manufacturer", uselist=False, cascade="all, delete-orphan"
    )
    food_license = db.relationship(
        "FoodLicense", backref="manufacturer", uselist=False, cascade="all, delete-orphan"
    )
    third_party_reports = db.relationship(
        "ThirdPartyReport", backref="manufacturer", cascade="all, delete-orphan"
    )
    factory_reports = db.relationship(
        "FactoryReport", backref="manufacturer", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Manufacturer {self.name}>"

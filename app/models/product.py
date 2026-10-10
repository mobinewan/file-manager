"""商品表。"""
from datetime import datetime
from ..extensions import db


class Product(db.Model):
    __tablename__ = "products"
    __table_args__ = (
        db.UniqueConstraint("manufacturer_id", "name", "spec", name="uq_product_manufacturer_name_spec"),
    )

    id = db.Column(db.Integer, primary_key=True)
    manufacturer_id = db.Column(db.Integer, db.ForeignKey("manufacturers.id"), nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False, index=True)
    category = db.Column(db.String(64), index=True)  # 商品类别
    spec = db.Column(db.String(128))  # 规格
    shelf_life_days = db.Column(db.Integer)  # 保质期（天），用于厂检有效期计算
    remark = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    third_party_reports = db.relationship(
        "ThirdPartyReport", backref="product", cascade="all, delete-orphan"
    )
    factory_reports = db.relationship(
        "FactoryReport", backref="product", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.name} {self.spec}>"

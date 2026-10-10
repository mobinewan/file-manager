"""按商品品类浏览：品类为顶级，品类下展示该品类各商品的四类证件状态。

数据模型不变（厂家→BL/FL/产品→报告）。同一厂家的 BL/FL 自然覆盖其下多个品类
与多个商品。这里仅提供一个以品类为入口的浏览视图。
"""
from flask import Blueprint, render_template, request, abort
from flask_login import login_required
from sqlalchemy import func, or_

from ..extensions import db
from ..models import (
    Product, Manufacturer,
    BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport,
)
from ..utils.date_utils import status_of, status_label, status_badge
from ..search.services import product_certificate_summary, _threshold_days

category_bp = Blueprint("category", __name__, url_prefix="/categories")


@category_bp.route("/")
@login_required
def list_categories():
    """列出所有商品品类及每个品类的商品数量。"""
    rows = (
        db.session.query(
            Product.category,
            func.count(Product.id),
        )
        .filter(Product.category.isnot(None))
        .filter(Product.category != "")
        .group_by(Product.category)
        .order_by(Product.category)
        .all()
    )
    categories = [{"name": c, "product_count": n} for c, n in rows if c]
    return render_template("category/list.html", categories=categories)


@category_bp.route("/<path:category_name>")
@login_required
def detail(category_name):
    """品类详情：展示该品类下所有商品及其四类证件状态，支持关键字模糊搜索。

    搜索范围：商品名/规格、厂家名、营业执照编号、食品证编号、
             第三方报告编号/检验机构、厂检批次号/生产日期。
    """
    category_name = category_name.strip()
    if not category_name:
        abort(404)
    q = request.args.get("q", "").strip()

    # 先取品类下全部商品
    products_q = Product.query.filter(Product.category == category_name)

    if q:
        like = f"%{q}%"
        # 命中报告/证件的商品
        hit_product_ids = set()

        # 商品名/规格命中
        hit = (
            db.session.query(Product.id)
            .filter(Product.category == category_name)
            .filter(or_(Product.name.like(like), Product.spec.like(like)))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        # 厂家名命中
        hit = (
            db.session.query(Product.id)
            .join(Manufacturer, Product.manufacturer_id == Manufacturer.id)
            .filter(Product.category == category_name)
            .filter(Manufacturer.name.like(like))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        # BL 编号命中
        hit = (
            db.session.query(Product.id)
            .join(Manufacturer, Product.manufacturer_id == Manufacturer.id)
            .join(BusinessLicense, Manufacturer.id == BusinessLicense.manufacturer_id)
            .filter(Product.category == category_name)
            .filter(BusinessLicense.license_no.like(like))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        # FL 编号命中
        hit = (
            db.session.query(Product.id)
            .join(Manufacturer, Product.manufacturer_id == Manufacturer.id)
            .join(FoodLicense, Manufacturer.id == FoodLicense.manufacturer_id)
            .filter(Product.category == category_name)
            .filter(FoodLicense.license_no.like(like))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        # 第三方报告编号/机构命中
        hit = (
            db.session.query(Product.id)
            .join(ThirdPartyReport, ThirdPartyReport.product_id == Product.id)
            .filter(Product.category == category_name)
            .filter(or_(ThirdPartyReport.report_no.like(like), ThirdPartyReport.testing_org.like(like)))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        # 厂检批次号/生产日期命中
        hit = (
            db.session.query(Product.id)
            .join(FactoryReport, FactoryReport.product_id == Product.id)
            .filter(Product.category == category_name)
            .filter(or_(FactoryReport.batch_no.like(like), FactoryReport.production_date.cast(db.String).like(like)))
            .distinct()
            .all()
        )
        hit_product_ids.update(i for (i,) in hit)

        if hit_product_ids:
            products_q = Product.query.filter(Product.id.in_(hit_product_ids)).order_by(Product.name)
        else:
            products = []
            threshold = _threshold_days()
            return render_template(
                "category/detail.html",
                category=category_name,
                products=products,
                manufacturers=[],
                threshold=threshold,
                q=q,
                status_of=status_of,
                status_label=status_label,
                status_badge=status_badge,
            )

    products = products_q.order_by(Product.name).all()
    threshold = _threshold_days()
    for p in products:
        p._cert_summary = product_certificate_summary(p, threshold)
    # 同品类下出现的厂家（用于说明 BL/FL 跨品类覆盖）
    manufacturer_ids = {p.manufacturer_id for p in products}
    manufacturers = (
        Manufacturer.query.filter(Manufacturer.id.in_(manufacturer_ids))
        .order_by(Manufacturer.name)
        .all()
        if manufacturer_ids
        else []
    )
    return render_template(
        "category/detail.html",
        category=category_name,
        products=products,
        manufacturers=manufacturers,
        threshold=threshold,
        q=q,
        status_of=status_of,
        status_label=status_label,
        status_badge=status_badge,
    )

"""四级钻取聚合搜索：商品名 → 厂家 → 规格 → 证件徽章。"""
from sqlalchemy import func
from ..extensions import db
from ..models import Manufacturer, Product, BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport
from ..utils.date_utils import status_of, status_label, status_badge


def _threshold_days():
    from ..models import Setting
    s = Setting.query.first()
    return (s.default_threshold_days if s else 30) or 30


def search_manufacturers_by_query(q):
    """按厂家名/商品名/类别/规格模糊匹配，返回去重后的厂家列表。

    匹配规则：
    - 厂家名直接含关键词 → 命中（返回该厂家全部商品）
    - 厂家下有商品名/类别/规格含关键词 → 命中（仅返回符合的商品）
    """
    if not q:
        return []
    like = f"%{q}%"
    # 1) 厂家名直接匹配
    manufacturers_by_name = (
        Manufacturer.query.filter(Manufacturer.name.like(like))
        .order_by(Manufacturer.name)
        .all()
    )
    # 2) 含符合关键词商品的厂家
    manufacturer_ids = (
        db.session.query(Product.manufacturer_id)
        .filter(
            db.or_(
                Product.name.like(like),
                Product.category.like(like),
                Product.spec.like(like),
            )
        )
        .distinct()
        .all()
    )
    ids = [i for (i,) in manufacturer_ids]
    # 合并去重，保持按名称排序
    seen = {m.id for m in manufacturers_by_name}
    extra = Manufacturer.query.filter(Manufacturer.id.in_(ids)).all() if ids else []
    for m in extra:
        if m.id not in seen:
            seen.add(m.id)
            manufacturers_by_name.append(m)
    manufacturers_by_name.sort(key=lambda x: x.name or "")
    return manufacturers_by_name


def products_for_manufacturer_by_query(manufacturer_id, q):
    """某厂家下符合搜索词的商品列表。

    若厂家名直接匹配关键词（含关键词子串），返回该厂家全部商品；
    否则只返回 name/category/spec 含关键词的商品。
    """
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        return []
    if not q:
        return Product.query.filter_by(manufacturer_id=manufacturer_id).order_by(Product.name).all()
    # 厂家名直接匹配 → 返回全部商品
    if m.name and q in m.name:
        return Product.query.filter_by(manufacturer_id=manufacturer_id).order_by(Product.name).all()
    like = f"%{q}%"
    return (
        Product.query.filter(
            Product.manufacturer_id == manufacturer_id,
            db.or_(
                Product.name.like(like),
                Product.category.like(like),
                Product.spec.like(like),
            ),
        )
        .order_by(Product.name)
        .all()
    )


def product_certificate_summary(product, threshold_days):
    """汇总某商品的各类证件状态，返回 dict。"""
    # 厂家级证件（从厂家关系获取）
    m = product.manufacturer
    bl_status = (
        status_of(m.business_license.valid_until, threshold_days)
        if m.business_license and m.business_license.valid_until is not None
        else ("long_term" if m.business_license else "missing")
    )
    fl_status = (
        status_of(m.food_license.valid_until, threshold_days)
        if m.food_license and m.food_license.valid_until is not None
        else ("long_term" if m.food_license else "missing")
    )
    # 最新第三方报告
    latest_tp = (
        ThirdPartyReport.query.filter_by(product_id=product.id)
        .order_by(ThirdPartyReport.test_date.desc())
        .first()
    )
    tp_status = (
        status_of(latest_tp.valid_until, threshold_days)
        if latest_tp
        else "missing"
    )
    # 最新厂检（按检验日期降序）；厂检已取消到期日概念，存在即视为正常
    latest_fc = (
        FactoryReport.query.filter_by(product_id=product.id)
        .order_by(FactoryReport.test_date.desc())
        .first()
    )
    fc_status = "normal" if latest_fc else "missing"
    return {
        "business_license": bl_status,
        "food_license": fl_status,
        "third_party": tp_status,
        "factory": fc_status,
    }


def search_suggestions(q):
    """前端 AJAX 联想：返回商品名 + 厂家名前若干条。"""
    if not q:
        return {"products": [], "manufacturers": []}
    like = f"%{q}%"
    products = (
        db.session.query(Product.name)
        .filter(Product.name.like(like))
        .distinct()
        .limit(10)
        .all()
    )
    manufacturers = (
        db.session.query(Manufacturer.name)
        .filter(Manufacturer.name.like(like))
        .distinct()
        .limit(10)
        .all()
    )
    return {
        "products": [p for (p,) in products],
        "manufacturers": [m for (m,) in manufacturers],
    }

"""商品 CRUD + 详情聚合报告 + 报告上传。"""
from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from flask_login import login_required

from ..extensions import db
from ..models import Product, Manufacturer, ThirdPartyReport, FactoryReport
from ..utils.file_storage import save_upload
from ..utils.date_utils import parse_date, status_of, status_label, status_badge
from ..auth.decorators import permission_required

product_bp = Blueprint("product", __name__, url_prefix="/products")


def _threshold_days():
    from ..models import Setting
    s = Setting.query.first()
    return (s.default_threshold_days if s else 30) or 30


@product_bp.route("/")
@login_required
def list_products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Product.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Product.name.like(like),
                Product.spec.like(like),
            )
        )
    if category:
        query = query.filter(Product.category == category)
    products = query.order_by(Product.category, Product.name).all()
    categories = [c for c, in db.session.query(Product.category).distinct().all() if c]
    return render_template(
        "product/list.html",
        products=products,
        q=q,
        category=category,
        categories=sorted(categories),
    )


@product_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("can_manage_product")
def create():
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    if request.method == "POST":
        manufacturer_id = request.form.get("manufacturer_id", type=int)
        name = request.form.get("name", "").strip()
        spec = request.form.get("spec", "").strip()
        category = request.form.get("category", "").strip()
        if not manufacturer_id or not name:
            flash("厂家和商品名称必填", "danger")
            return render_template("product/form.html", p=None, manufacturers=manufacturers)
        existing = Product.query.filter_by(
            manufacturer_id=manufacturer_id, name=name, spec=spec
        ).first()
        if existing:
            flash("该厂家下已存在相同名称和规格的商品", "danger")
            return render_template("product/form.html", p=None, manufacturers=manufacturers)
        p = Product(
            manufacturer_id=manufacturer_id,
            name=name,
            spec=spec or None,
            category=category or None,
            shelf_life_days=request.form.get("shelf_life_days", type=int),
            remark=request.form.get("remark", "").strip() or None,
        )
        db.session.add(p)
        db.session.commit()
        flash(f"已创建商品 {p.name}", "success")
        return redirect(url_for("product.detail", product_id=p.id))
    return render_template("product/form.html", p=None, manufacturers=manufacturers)


@product_bp.route("/<int:product_id>")
@login_required
def detail(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    threshold = _threshold_days()
    # 最新第三方报告
    latest_tp = (
        ThirdPartyReport.query.filter_by(product_id=p.id)
        .order_by(ThirdPartyReport.test_date.desc())
        .first()
    )
    # 最新厂检（按有效期降序）
    latest_fc = (
        FactoryReport.query.filter_by(product_id=p.id)
        .order_by(FactoryReport.valid_until.desc())
        .first()
    )
    return render_template(
        "product/detail.html",
        p=p,
        threshold=threshold,
        latest_tp=latest_tp,
        latest_fc=latest_fc,
        today_date_iso=date.today().isoformat(),
        today_plus_365_iso=(date.today() + timedelta(days=365)).isoformat(),
        status_of=status_of,
        status_label=status_label,
        status_badge=status_badge,
    )


@product_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("can_manage_product")
def edit(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    if request.method == "POST":
        manufacturer_id = request.form.get("manufacturer_id", type=int)
        name = request.form.get("name", "").strip()
        spec = request.form.get("spec", "").strip()
        category = request.form.get("category", "").strip()
        if not manufacturer_id or not name:
            flash("厂家和商品名称必填", "danger")
            return render_template("product/form.html", p=p, manufacturers=manufacturers)
        existing = Product.query.filter_by(
            manufacturer_id=manufacturer_id, name=name, spec=spec
        ).first()
        if existing and existing.id != p.id:
            flash("该厂家下已存在相同名称和规格的商品", "danger")
            return render_template("product/form.html", p=p, manufacturers=manufacturers)
        p.manufacturer_id = manufacturer_id
        p.name = name
        p.spec = spec or None
        p.category = category or None
        p.shelf_life_days = request.form.get("shelf_life_days", type=int)
        p.remark = request.form.get("remark", "").strip() or None
        db.session.commit()
        flash("已更新商品信息", "success")
        return redirect(url_for("product.detail", product_id=p.id))
    return render_template("product/form.html", p=p, manufacturers=manufacturers)


@product_bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
@permission_required("can_manage_product")
def delete(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    manufacturer_id = p.manufacturer_id
    db.session.delete(p)
    db.session.commit()
    flash("已删除商品", "success")
    return redirect(url_for("manufacturer.detail", manufacturer_id=manufacturer_id))


@product_bp.route("/<int:product_id>/third-party-reports", methods=["POST"])
@login_required
@permission_required("can_upload_certificate")
def upload_third_party(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    file = request.files.get("file")
    rel, original = save_upload(file, "THIRD_PARTY_SUBDIR")
    if not rel:
        flash("文件上传失败，请检查文件类型", "danger")
        return redirect(url_for("product.detail", product_id=p.id))
    test_date = parse_date(request.form.get("test_date"))
    valid_until = parse_date(request.form.get("valid_until"))
    if not valid_until:
        flash("第三方检验报告必须填写有效期至", "danger")
        return redirect(url_for("product.detail", product_id=p.id))
    r = ThirdPartyReport(
        product_id=p.id,
        manufacturer_id=p.manufacturer_id,
        report_no=request.form.get("report_no", "").strip() or None,
        testing_org=request.form.get("testing_org", "").strip() or None,
        test_date=test_date,
        valid_from=parse_date(request.form.get("valid_from")),
        valid_until=valid_until,
        file_path=rel,
        file_name=original,
    )
    db.session.add(r)
    db.session.commit()
    flash("第三方检验报告已上传", "success")
    return redirect(url_for("product.detail", product_id=p.id))


@product_bp.route("/<int:product_id>/factory-reports", methods=["POST"])
@login_required
@permission_required("can_upload_certificate")
def upload_factory(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        abort(404)
    file = request.files.get("file")
    rel, original = save_upload(file, "FACTORY_SUBDIR")
    if not rel:
        flash("文件上传失败，请检查文件类型", "danger")
        return redirect(url_for("product.detail", product_id=p.id))
    production_date = parse_date(request.form.get("production_date"))
    if not production_date:
        flash("出厂检验报告必须填写生产日期", "danger")
        return redirect(url_for("product.detail", product_id=p.id))
    # 检验日期默认 = 生产日期，可由表单覆盖
    test_date = parse_date(request.form.get("test_date")) or production_date
    # 厂检不再有保质期/到期日概念；valid_until 列保留为生产日期作为兼容值（reminder 已跳过厂检）
    r = FactoryReport(
        product_id=p.id,
        manufacturer_id=p.manufacturer_id,
        batch_no=request.form.get("batch_no", "").strip() or None,
        production_date=production_date,
        test_date=test_date,
        valid_until=production_date,
        file_path=rel,
        file_name=original,
    )
    db.session.add(r)
    db.session.commit()
    flash("出厂检验报告已上传", "success")
    return redirect(url_for("product.detail", product_id=p.id))

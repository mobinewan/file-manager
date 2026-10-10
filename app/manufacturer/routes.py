"""厂家 CRUD + 详情聚合 + 厂家级证件上传。"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from flask_login import login_required

from ..extensions import db
from ..models import Manufacturer, Product, BusinessLicense, FoodLicense
from ..utils.file_storage import save_upload
from ..utils.date_utils import parse_date, status_of, status_label, status_badge
from ..auth.decorators import permission_required

manufacturer_bp = Blueprint("manufacturer", __name__, url_prefix="/manufacturers")


def _threshold_days():
    from ..models import Setting
    s = Setting.query.first()
    return (s.default_threshold_days if s else 30) or 30


@manufacturer_bp.route("/")
@login_required
def list_manufacturers():
    q = request.args.get("q", "").strip()
    query = Manufacturer.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(
                Manufacturer.name.like(like),
                Manufacturer.unified_credit_code.like(like),
                Manufacturer.contact_person.like(like),
            )
        )
    manufacturers = query.order_by(Manufacturer.name).all()
    return render_template(
        "manufacturer/list.html",
        manufacturers=manufacturers,
        q=q,
        threshold=_threshold_days(),
        status_of=status_of,
        status_label=status_label,
        status_badge=status_badge,
    )


@manufacturer_bp.route("/create", methods=["GET", "POST"])
@login_required
@permission_required("can_manage_manufacturer")
def create():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("厂家名称必填", "danger")
            return render_template("manufacturer/form.html", m=None)
        if Manufacturer.query.filter_by(name=name).first():
            flash("厂家名称已存在", "danger")
            return render_template("manufacturer/form.html", m=None)
        m = Manufacturer(
            name=name,
            unified_credit_code=request.form.get("unified_credit_code", "").strip() or None,
            contact_person=request.form.get("contact_person", "").strip() or None,
            contact_phone=request.form.get("contact_phone", "").strip() or None,
            address=request.form.get("address", "").strip() or None,
            remark=request.form.get("remark", "").strip() or None,
        )
        db.session.add(m)
        db.session.commit()
        flash(f"已创建厂家 {m.name}", "success")
        return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))
    return render_template("manufacturer/form.html", m=None)


@manufacturer_bp.route("/<int:manufacturer_id>")
@login_required
def detail(manufacturer_id):
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        abort(404)
    q = request.args.get("q", "").strip()
    products = m.products
    if q:
        like = f"%{q}%"
        products = [p for p in products if q in (p.name or "") or q in (p.spec or "") or q in (p.category or "")]
    # 厂家级证件状态
    threshold = _threshold_days()
    bl_status = status_of(m.business_license.valid_until if m.business_license else None, threshold) if m.business_license else "missing"
    fl_status = status_of(m.food_license.valid_until if m.food_license else None, threshold) if m.food_license else "missing"
    # 为每个商品预聚合证书状态
    from ..search.services import product_certificate_summary
    for p in products:
        p._cert_summary = product_certificate_summary(p, threshold)
    return render_template(
        "manufacturer/detail.html",
        m=m,
        products=products,
        q=q,
        threshold=threshold,
        bl_status=bl_status,
        fl_status=fl_status,
        status_of=status_of,
        status_label=status_label,
        status_badge=status_badge,
    )


@manufacturer_bp.route("/<int:manufacturer_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("can_manage_manufacturer")
def edit(manufacturer_id):
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("厂家名称必填", "danger")
            return render_template("manufacturer/form.html", m=m)
        existing = Manufacturer.query.filter_by(name=name).first()
        if existing and existing.id != m.id:
            flash("厂家名称已存在", "danger")
            return render_template("manufacturer/form.html", m=m)
        m.name = name
        m.unified_credit_code = request.form.get("unified_credit_code", "").strip() or None
        m.contact_person = request.form.get("contact_person", "").strip() or None
        m.contact_phone = request.form.get("contact_phone", "").strip() or None
        m.address = request.form.get("address", "").strip() or None
        m.remark = request.form.get("remark", "").strip() or None
        db.session.commit()
        flash("已更新厂家信息", "success")
        return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))
    return render_template("manufacturer/form.html", m=m)


@manufacturer_bp.route("/<int:manufacturer_id>/delete", methods=["POST"])
@login_required
@permission_required("can_manage_manufacturer")
def delete(manufacturer_id):
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        abort(404)
    name = m.name
    db.session.delete(m)
    db.session.commit()
    flash(f"已删除厂家 {name}", "success")
    return redirect(url_for("manufacturer.list_manufacturers"))


@manufacturer_bp.route("/<int:manufacturer_id>/business-license", methods=["POST"])
@login_required
@permission_required("can_upload_certificate")
def upload_business_license(manufacturer_id):
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        abort(404)
    file = request.files.get("file")
    rel, original = save_upload(file, "LICENSE_SUBDIR")
    if not rel:
        flash("文件上传失败，请检查文件类型（PDF/JPG/PNG 等）", "danger")
        return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))
    if m.business_license:
        m.business_license.file_path = rel
        m.business_license.file_name = original
    else:
        m.business_license = BusinessLicense(file_path=rel, file_name=original)
    # 表单字段
    if m.business_license:
        m.business_license.license_no = request.form.get("license_no", "").strip() or None
        m.business_license.legal_person = request.form.get("legal_person", "").strip() or None
        m.business_license.issue_date = parse_date(request.form.get("issue_date"))
        m.business_license.valid_until = parse_date(request.form.get("valid_until"))
    db.session.commit()
    flash("营业执照已上传", "success")
    return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))


@manufacturer_bp.route("/<int:manufacturer_id>/food-license", methods=["POST"])
@login_required
@permission_required("can_upload_certificate")
def upload_food_license(manufacturer_id):
    m = db.session.get(Manufacturer, manufacturer_id)
    if not m:
        abort(404)
    file = request.files.get("file")
    rel, original = save_upload(file, "LICENSE_SUBDIR")
    if not rel:
        flash("文件上传失败，请检查文件类型", "danger")
        return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))
    if m.food_license:
        m.food_license.file_path = rel
        m.food_license.file_name = original
    else:
        m.food_license = FoodLicense(file_path=rel, file_name=original)
    if m.food_license:
        m.food_license.license_no = request.form.get("license_no", "").strip() or None
        m.food_license.scope = request.form.get("scope", "").strip() or None
        m.food_license.issuer = request.form.get("issuer", "").strip() or None
        m.food_license.issue_date = parse_date(request.form.get("issue_date"))
        m.food_license.valid_until = parse_date(request.form.get("valid_until"))
    db.session.commit()
    flash("食品经营许可证已上传", "success")
    return redirect(url_for("manufacturer.detail", manufacturer_id=m.id))

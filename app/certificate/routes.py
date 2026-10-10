"""证件下载、预览、删除、编辑路由。"""
import os
import mimetypes
from flask import (
    Blueprint, send_from_directory, abort, redirect, url_for, flash,
    send_file, current_app, render_template, request,
)
from flask_login import login_required

from ..extensions import db
from ..models import BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport
from ..utils.date_utils import parse_date, status_of, status_label, status_badge
from ..auth.decorators import permission_required

certificate_bp = Blueprint("certificate", __name__, url_prefix="/certificates")

MODEL_MAP = {
    "business_license": BusinessLicense,
    "food_license": FoodLicense,
    "third_party": ThirdPartyReport,
    "factory": FactoryReport,
}

CERT_LABELS = {
    "business_license": "营业执照",
    "food_license": "食品经营许可证",
    "third_party": "第三方检验报告",
    "factory": "出厂检验报告",
}


def _get_model(cert_type):
    return MODEL_MAP.get(cert_type)


def _guess_mimetype(filename):
    """从文件名猜测 MIME 类型，兜底 application/octet-stream。

    处理 Python mimetypes 对以点开头的文件名（如 ".pdf"）无法识别的问题：
    当文件名以点开头时，先去掉前导点再猜测。
    """
    if not filename:
        return "application/octet-stream"
    mime, _ = mimetypes.guess_type(filename)
    if mime:
        return mime
    # 处理 ".pdf" 这类以点开头的情况（旧数据 secure_filename 清洗中文后残留）
    stripped = filename.lstrip(".")
    if stripped and stripped != filename:
        mime, _ = mimetypes.guess_type(stripped)
        if mime:
            return mime
    # 最终兜底：手动按扩展名映射
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    manual = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "webp": "image/webp",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return manual.get(ext, "application/octet-stream")


def _build_download_name(file_name, cert_type):
    """构造合适的下载文件名，处理旧数据 file_name 仅为 .pdf 的情况。"""
    if file_name and not file_name.lstrip("."):
        # file_name 全是点，无效
        return f"{cert_type}.file"
    if file_name and not file_name.startswith("."):
        # 正常文件名
        return file_name
    # file_name 以点开头，如 ".pdf"（旧数据）
    ext = file_name or ""
    base = CERT_LABELS.get(cert_type, cert_type)
    return base + ext


def _back_url_for(obj, cert_type):
    """删除/编辑后跳回的页面。"""
    if cert_type in ("business_license", "food_license"):
        return url_for("manufacturer.detail", manufacturer_id=obj.manufacturer_id)
    if cert_type in ("third_party", "factory"):
        return url_for("product.detail", product_id=obj.product_id)
    return url_for("index")


@certificate_bp.route("/<cert_type>/<int:cert_id>/download")
@login_required
def download(cert_type, cert_id):
    model = _get_model(cert_type)
    if not model:
        abort(404)
    obj = db.session.get(model, cert_id)
    if not obj:
        abort(404)
    upload_root = current_app.config["UPLOAD_FOLDER"]
    dl_name = _build_download_name(obj.file_name, cert_type)
    return send_from_directory(
        upload_root, obj.file_path,
        as_attachment=True,
        download_name=dl_name,
        mimetype=_guess_mimetype(obj.file_name),
    )


@certificate_bp.route("/<cert_type>/<int:cert_id>/preview")
@login_required
def preview(cert_type, cert_id):
    model = _get_model(cert_type)
    if not model:
        abort(404)
    obj = db.session.get(model, cert_id)
    if not obj:
        abort(404)
    upload_root = current_app.config["UPLOAD_FOLDER"]
    abs_path = os.path.join(upload_root, obj.file_path)
    dl_name = _build_download_name(obj.file_name, cert_type)
    # as_attachment=False 表示内联显示（inline），浏览器可直接渲染 PDF/图片
    return send_file(
        abs_path,
        as_attachment=False,
        download_name=dl_name,
        mimetype=_guess_mimetype(obj.file_name),
    )


@certificate_bp.route("/<cert_type>/<int:cert_id>/delete", methods=["POST"])
@login_required
@permission_required("can_delete_certificate")
def delete(cert_type, cert_id):
    model = _get_model(cert_type)
    if not model:
        abort(404)
    obj = db.session.get(model, cert_id)
    if not obj:
        abort(404)
    # 删除关联文件
    try:
        abs_path = os.path.join(current_app.config["UPLOAD_FOLDER"], obj.file_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError:
        pass
    redirect_url = _back_url_for(obj, cert_type)
    db.session.delete(obj)
    db.session.commit()
    flash("已删除证件记录", "success")
    return redirect(redirect_url)


@certificate_bp.route("/<cert_type>/<int:cert_id>/edit", methods=["GET", "POST"])
@login_required
@permission_required("can_edit_certificate")
def edit(cert_type, cert_id):
    """证件信息编辑：可修改有效期、保质期等元数据，无需重新上传文件。"""
    model = _get_model(cert_type)
    if not model:
        abort(404)
    obj = db.session.get(model, cert_id)
    if not obj:
        abort(404)

    if request.method == "POST":
        if cert_type == "business_license":
            obj.license_no = request.form.get("license_no", "").strip() or None
            obj.legal_person = request.form.get("legal_person", "").strip() or None
            obj.issue_date = parse_date(request.form.get("issue_date"))
            obj.valid_until = parse_date(request.form.get("valid_until"))
        elif cert_type == "food_license":
            obj.license_no = request.form.get("license_no", "").strip() or None
            obj.scope = request.form.get("scope", "").strip() or None
            obj.issuer = request.form.get("issuer", "").strip() or None
            obj.issue_date = parse_date(request.form.get("issue_date"))
            obj.valid_until = parse_date(request.form.get("valid_until"))
        elif cert_type == "third_party":
            obj.report_no = request.form.get("report_no", "").strip() or None
            obj.testing_org = request.form.get("testing_org", "").strip() or None
            obj.test_date = parse_date(request.form.get("test_date"))
            obj.valid_from = parse_date(request.form.get("valid_from"))
            obj.valid_until = parse_date(request.form.get("valid_until"))
        elif cert_type == "factory":
            # 厂检：仅修改批次号、生产日期、检验日期；不再有保质期/到期日概念
            obj.batch_no = request.form.get("batch_no", "").strip() or None
            obj.production_date = parse_date(request.form.get("production_date"))
            obj.test_date = parse_date(request.form.get("test_date")) or obj.production_date
            # valid_until 列保留为生产日期作为兼容值（reminder 已跳过厂检）
            if obj.production_date:
                obj.valid_until = obj.production_date
        db.session.commit()
        flash("已更新证件信息", "success")
        return redirect(_back_url_for(obj, cert_type))

    return render_template(
        "certificate/edit.html",
        obj=obj,
        cert_type=cert_type,
        cert_label=CERT_LABELS.get(cert_type, cert_type),
    )

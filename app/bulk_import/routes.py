"""批量上传路由：ZIP 压缩包 或 多文件。"""
import json
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required

from ..extensions import db
from ..models import Manufacturer, Product, BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport
from .services import process_zip, process_files

bulk_bp = Blueprint("bulk", __name__, url_prefix="/bulk")

# 存储上传过程中的临时记录 {upload_id: result_data}
_upload_queue = {}
_upload_counter = 0


@bulk_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    global _upload_counter
    
    if request.method == "POST":
        # 优先处理单个 ZIP
        zip_file = request.files.get("zip_file")
        results = []
        if zip_file and zip_file.filename:
            if not zip_file.filename.lower().endswith(".zip"):
                flash("压缩包必须为 .zip 格式", "danger")
                return redirect(url_for("bulk.upload"))
            results = process_zip(zip_file)
        else:
            # 处理多文件
            files = request.files.getlist("files")
            files = [f for f in files if f and f.filename]
            if not files:
                flash("请选择 ZIP 压缩包或多个证件文件", "danger")
                return redirect(url_for("bulk.upload"))
            results = process_files(files)

        # 提交所有成功的更改
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f"数据库保存失败：{e}", "danger")
            return redirect(url_for("bulk.upload"))

        # 为失败的结果分配 ID 以便手动修正
        for r in results:
            if r["status"] == "error" and r.get("uploaded_id"):
                _upload_counter += 1
                r["upload_id"] = _upload_counter
                _upload_queue[_upload_counter] = r

        success = sum(1 for r in results if r["status"] == "success")
        errors = sum(1 for r in results if r["status"] == "error")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        flash(f"处理完成：成功 {success}，失败 {errors}，跳过 {skipped}", "info")

        return render_template("bulk/result.html", results=results)

    return render_template("bulk/upload.html")


@bulk_bp.route("/edit/<int:upload_id>", methods=["POST"])
@login_required
def edit(upload_id):
    """手动修正上传失败的证件信息"""
    if upload_id not in _upload_queue:
        return jsonify({"success": False, "message": "未找到对应的上传记录"})
    
    data = request.get_json()
    cert_type = data.get("cert_type")
    manufacturer_name = data.get("manufacturer_name", "").strip()
    product_name = data.get("product_name", "").strip() or None
    
    if not cert_type or not manufacturer_name:
        return jsonify({"success": False, "message": "证件类型和厂家名称不能为空"})
    
    try:
        from ..utils.date_utils import parse_date
        
        # 获取或创建厂家
        m = Manufacturer.query.filter_by(name=manufacturer_name).first()
        if not m:
            m = Manufacturer(name=manufacturer_name)
            db.session.add(m)
            db.session.flush()
        
        # 如果是单品级证件，获取或创建商品
        product = None
        if cert_type in ("third_party", "factory") and product_name:
            product = Product.query.filter_by(
                manufacturer_id=m.id, name=product_name
            ).first()
            if not product:
                product = Product(manufacturer_id=m.id, name=product_name)
                db.session.add(product)
                db.session.flush()
        
        # 根据证件类型更新信息
        if cert_type == "business_license":
            obj = BusinessLicense.query.filter_by(manufacturer_id=m.id).first()
            if not obj:
                obj = BusinessLicense(manufacturer_id=m.id)
                db.session.add(obj)
            if data.get("issue_date"):
                obj.issue_date = parse_date(data.get("issue_date"))
            if data.get("valid_until"):
                obj.valid_until = parse_date(data.get("valid_until"))
        
        elif cert_type == "food_license":
            obj = FoodLicense.query.filter_by(manufacturer_id=m.id).first()
            if not obj:
                obj = FoodLicense(manufacturer_id=m.id)
                db.session.add(obj)
            if data.get("issue_date"):
                obj.issue_date = parse_date(data.get("issue_date"))
            if data.get("valid_until"):
                obj.valid_until = parse_date(data.get("valid_until"))
        
        elif cert_type == "third_party":
            if not product:
                return jsonify({"success": False, "message": "商品不存在，请先创建商品"})
            obj = ThirdPartyReport(
                product_id=product.id,
                manufacturer_id=m.id,
                test_date=parse_date(data.get("test_date")) if data.get("test_date") else None,
                valid_until=parse_date(data.get("valid_until")) if data.get("valid_until") else None,
            )
            db.session.add(obj)
        
        elif cert_type == "factory":
            if not product:
                return jsonify({"success": False, "message": "商品不存在，请先创建商品"})
            obj = FactoryReport(
                product_id=product.id,
                manufacturer_id=m.id,
                production_date=parse_date(data.get("production_date")) if data.get("production_date") else None,
                test_date=parse_date(data.get("production_date")) if data.get("production_date") else None,
                valid_until=parse_date(data.get("production_date")) if data.get("production_date") else None,
            )
            db.session.add(obj)
        
        db.session.commit()
        
        # 从队列中移除
        del _upload_queue[upload_id]
        
        return jsonify({"success": True, "message": "修正成功"})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"修正失败：{str(e)}"})

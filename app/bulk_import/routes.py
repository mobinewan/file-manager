"""批量上传路由：ZIP 压缩包 或 多文件。"""
import io
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required
from werkzeug.datastructures import FileStorage

from ..extensions import db
from ..models import Manufacturer, Product, BusinessLicense, FoodLicense, ThirdPartyReport, FactoryReport
from .services import process_zip, process_files, process_single_file

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
            if r["status"] == "error":
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

        # 获取原始文件内容
        original_data = _upload_queue[upload_id]
        file_content = original_data.get("file_content")
        original_filename = original_data.get("filename", "unknown.pdf")

        if not file_content:
            return jsonify({"success": False, "message": "原始文件内容已丢失，请重新上传"})

        # 创建新的 FileStorage 对象
        new_file_storage = FileStorage(
            stream=io.BytesIO(file_content),
            filename=original_filename,
        )

        # 构造新的文件名（使用用户填写的信息）
        new_filename = _build_filename(cert_type, manufacturer_name, product_name, data)

        # 重新调用处理逻辑
        result = process_single_file(new_file_storage, new_filename, file_content=file_content)

        # 提交更改
        db.session.commit()

        # 从队列中移除
        del _upload_queue[upload_id]

        if result["status"] == "success":
            return jsonify({"success": True, "message": "修正成功"})
        else:
            return jsonify({"success": False, "message": result["message"]})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"修正失败：{str(e)}"})


def _build_filename(cert_type, manufacturer_name, product_name, data):
    """根据编辑后的信息构建新的文件名。"""
    parts = [manufacturer_name]

    if cert_type in ("third_party", "factory") and product_name:
        parts.append(product_name)

    # 添加证件类型关键字
    if cert_type == "business_license":
        parts.append("营业执照")
    elif cert_type == "food_license":
        parts.append("食品经营许可证")
    elif cert_type == "third_party":
        parts.append("第三方检验报告")
    elif cert_type == "factory":
        parts.append("出厂检验报告")

    # 添加日期
    date_str = None
    if cert_type in ("business_license", "food_license"):
        date_str = data.get("valid_until") or data.get("issue_date")
    elif cert_type == "third_party":
        date_str = data.get("valid_until") or data.get("test_date")
    elif cert_type == "factory":
        date_str = data.get("production_date") or data.get("test_date")

    if date_str:
        parts.append(date_str)

    return "-".join(parts) + ".pdf"

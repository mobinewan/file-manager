"""批量上传路由：ZIP 压缩包 或 多文件。"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required

from ..extensions import db
from .services import process_zip, process_files

bulk_bp = Blueprint("bulk", __name__, url_prefix="/bulk")


@bulk_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
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

        success = sum(1 for r in results if r["status"] == "success")
        errors = sum(1 for r in results if r["status"] == "error")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        flash(f"处理完成：成功 {success}，失败 {errors}，跳过 {skipped}", "info")
        return render_template("bulk/result.html", results=results)

    return render_template("bulk/upload.html")

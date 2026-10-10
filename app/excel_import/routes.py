"""Excel 上传/结果/导出 路由。"""
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, request, flash,
    current_app, send_from_directory, session,
)
from flask_login import login_required

from .services import parse_excel, compare_rows, export_results
from ..utils.date_utils import status_label, status_badge

excel_bp = Blueprint("excel", __name__, url_prefix="/excel")


@excel_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("请选择 Excel 文件", "danger")
            return redirect(url_for("excel.upload"))
        if not file.filename.lower().endswith((".xlsx", ".xls")):
            flash("仅支持 .xlsx/.xls 格式", "danger")
            return redirect(url_for("excel.upload"))
        try:
            rows = parse_excel(file)
        except Exception as e:
            flash(f"解析失败：{e}", "danger")
            return redirect(url_for("excel.upload"))
        if not rows:
            flash("文件中没有可识别的数据行", "warning")
            return redirect(url_for("excel.upload"))
        results = compare_rows(rows)
        task_id = uuid.uuid4().hex[:12]
        session[f"excel_result_{task_id}"] = results
        try:
            rel_path = export_results(results, task_id)
            session[f"excel_path_{task_id}"] = rel_path
        except Exception as e:
            flash(f"导出失败：{e}", "warning")
        return redirect(url_for("excel.result", task_id=task_id))
    return render_template("excel/upload.html")


@excel_bp.route("/result/<task_id>")
@login_required
def result(task_id):
    results = session.get(f"excel_result_{task_id}")
    if results is None:
        flash("结果不存在或会话已过期，请重新上传", "warning")
        return redirect(url_for("excel.upload"))
    has_export = f"excel_path_{task_id}" in session
    return render_template(
        "excel/result.html",
        results=results,
        task_id=task_id,
        has_export=has_export,
        status_label=status_label,
        status_badge=status_badge,
    )


@excel_bp.route("/result/<task_id>/export")
@login_required
def export(task_id):
    rel_path = session.get(f"excel_path_{task_id}")
    if not rel_path:
        flash("导出文件不存在，请重新上传", "warning")
        return redirect(url_for("excel.upload"))
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"], rel_path, as_attachment=True
    )

"""到期看板 + 阈值配置 路由。"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Setting
from ..auth.decorators import admin_required
from .services import list_all_grouped, _threshold_days, summarize_expiry

reminder_bp = Blueprint("reminder", __name__, url_prefix="/reminder")


@reminder_bp.route("/dashboard")
@login_required
def dashboard():
    grouped = list_all_grouped()
    return render_template(
        "reminder/dashboard.html",
        grouped=grouped,
        summary=summarize_expiry(),
    )


@reminder_bp.route("/config", methods=["GET", "POST"])
@login_required
@admin_required
def config():
    s = Setting.query.first()
    if not s:
        s = Setting(default_threshold_days=30, enable_alert=True)
        db.session.add(s)
        db.session.commit()
    if request.method == "POST":
        days = request.form.get("default_threshold_days", type=int)
        enable = request.form.get("enable_alert") == "on"
        if days is None or days < 0:
            flash("阈值必须为非负整数", "danger")
            return redirect(url_for("reminder.config"))
        s.default_threshold_days = days
        s.enable_alert = enable
        db.session.commit()
        flash("已更新提醒配置", "success")
        return redirect(url_for("reminder.config"))
    return render_template("reminder/config.html", setting=s)

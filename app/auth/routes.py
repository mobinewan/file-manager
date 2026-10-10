"""登录/登出/用户管理路由。"""
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required

from ..extensions import db
from ..models import User
from ..models.user import PERMISSIONS
from .decorators import admin_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.is_active and user.check_password(password):
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))
        flash("用户名或密码错误", "danger")
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/users")
@login_required
@admin_required
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template(
        "auth/users.html",
        users=users_list,
        permissions=PERMISSIONS,
    )


@auth_bp.route("/users/create", methods=["POST"])
@login_required
@admin_required
def create_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "user")
    if role not in ("admin", "user"):
        role = "user"
    if not username or not password:
        flash("用户名和密码必填", "danger")
        return redirect(url_for("auth.users"))
    if User.query.filter_by(username=username).first():
        flash("用户名已存在", "danger")
        return redirect(url_for("auth.users"))
    user = User(username=username, role=role, is_active=True)
    user.set_password(password)
    # 普通用户：根据勾选项设置权限
    if role == "user":
        for perm_name, _ in PERMISSIONS:
            setattr(user, perm_name, request.form.get(perm_name) == "on")
    db.session.add(user)
    db.session.commit()
    flash(f"已创建用户 {username}", "success")
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/password", methods=["POST"])
@login_required
@admin_required
def reset_password(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("用户不存在", "danger")
        return redirect(url_for("auth.users"))
    new_password = request.form.get("new_password", "")
    if len(new_password) < 6:
        flash("密码至少 6 位", "danger")
        return redirect(url_for("auth.users"))
    user.set_password(new_password)
    db.session.commit()
    flash(f"已重置 {user.username} 的密码", "success")
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_active(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("用户不存在", "danger")
        return redirect(url_for("auth.users"))
    if user.id == current_user.id:
        flash("不能停用当前登录用户", "warning")
        return redirect(url_for("auth.users"))
    user.is_active = not user.is_active
    db.session.commit()
    flash(f"已{'启用' if user.is_active else '停用'} {user.username}", "success")
    return redirect(url_for("auth.users"))


@auth_bp.route("/users/<int:user_id>/permissions", methods=["POST"])
@login_required
@admin_required
def update_permissions(user_id):
    """管理员勾选/取消勾选普通用户的细粒度权限。"""
    user = db.session.get(User, user_id)
    if not user:
        flash("用户不存在", "danger")
        return redirect(url_for("auth.users"))
    if user.role == "admin":
        flash("管理员默认拥有全部权限，无需勾选", "info")
        return redirect(url_for("auth.users"))
    for perm_name, _ in PERMISSIONS:
        setattr(user, perm_name, request.form.get(perm_name) == "on")
    db.session.commit()
    flash(f"已更新 {user.username} 的权限", "success")
    return redirect(url_for("auth.users"))

"""权限装饰器。"""
from functools import wraps
from flask import abort, flash, redirect, url_for, request
from flask_login import current_user


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return wrapper


def permission_required(perm_name):
    """细粒度权限校验：管理员直接通过；普通用户按勾选项决定。"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login", next=request.path))
            if not current_user.has_perm(perm_name):
                flash("您没有执行该操作的权限，请联系管理员", "danger")
                return redirect(request.referrer or url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

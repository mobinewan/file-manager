"""Flask 应用工厂 + 首次启动初始化。"""
import os
from flask import Flask
from werkzeug.security import generate_password_hash

from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(app.config["DB_PATH"]), exist_ok=True)
    for sub in ["licenses", "third_party", "factory", "exports"]:
        os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], sub), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from .models import User, Setting  # noqa: F401  确保模型注册

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 注册蓝图
    from .auth.routes import auth_bp
    from .manufacturer.routes import manufacturer_bp
    from .product.routes import product_bp
    from .certificate.routes import certificate_bp
    from .search.routes import search_bp
    from .excel_import.routes import excel_bp
    from .reminder.routes import reminder_bp
    from .bulk_import.routes import bulk_bp
    from .category.routes import category_bp
    from .bundle_download.routes import bundle_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(manufacturer_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(certificate_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(excel_bp)
    app.register_blueprint(reminder_bp)
    app.register_blueprint(bulk_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(bundle_bp)

    # 首页路由
    from flask import redirect, url_for, render_template
    from flask_login import current_user
    from .reminder.services import summarize_expiry

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return render_template("index.html", summary=summarize_expiry())

    with app.app_context():
        _ensure_initialized(app)

    return app


def _ensure_initialized(app):
    """首次启动时建表并注入默认 admin 与设置。"""
    db.create_all()
    _run_migrations()

    from .models import User, Setting
    if not User.query.filter_by(role="admin").first():
        admin = User(
            username=app.config["ADMIN_USERNAME"],
            password_hash=generate_password_hash(app.config["ADMIN_PASSWORD"]),
            role="admin",
            is_active=True,
        )
        db.session.add(admin)

    if not Setting.query.first():
        db.session.add(Setting(
            default_threshold_days=app.config["DEFAULT_THRESHOLD_DAYS"],
            enable_alert=True,
        ))

    db.session.commit()


def _run_migrations():
    """轻量级迁移：为已有表补充新增列（SQLite ALTER TABLE）。"""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)

    # products 表补 shelf_life_days 列
    if "products" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("products")}
        if "shelf_life_days" not in cols:
            with db.engine.connect() as conn:
                conn.execute(text(
                    "ALTER TABLE products ADD COLUMN shelf_life_days INTEGER"
                ))
                conn.commit()

    # users 表补细粒度权限列
    if "users" in inspector.get_table_names():
        cols = {c["name"] for c in inspector.get_columns("users")}
        added = False
        for col in (
            "can_manage_manufacturer",
            "can_manage_product",
            "can_upload_certificate",
            "can_edit_certificate",
            "can_delete_certificate",
        ):
            if col not in cols:
                with db.engine.connect() as conn:
                    conn.execute(text(
                        f"ALTER TABLE users ADD COLUMN {col} BOOLEAN NOT NULL DEFAULT 0"
                    ))
                    conn.commit()
                added = True
        _ = added

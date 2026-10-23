import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "请先登录后再访问该页面。"
login_manager.login_message_category = "warning"

BASE_DIR = Path(__file__).resolve().parent.parent


def _database_uri() -> str:
    """优先使用云平台提供的 DATABASE_URL（PostgreSQL），否则用本地 SQLite。"""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return f"sqlite:///{BASE_DIR / 'data.db'}"
    # Heroku / Render 等有时给出 postgres://，SQLAlchemy 需要 postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def create_app() -> Flask:
    load_dotenv(BASE_DIR / ".env")

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = _database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "admin123")

    # 部署在 HTTPS 反向代理后时，正确识别协议与客户端 IP
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    if os.getenv("FORCE_HTTPS", "").lower() in {"1", "true", "yes"}:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["REMEMBER_COOKIE_SECURE"] = True

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.errorhandler(403)
    def forbidden(_error):
        from flask import render_template

        return render_template("403.html"), 403

    with app.app_context():
        db.create_all()
        _ensure_admin(app)
        _seed_sample_questions()

    return app


def _ensure_admin(app: Flask) -> None:
    """仅在系统中尚无管理员时，用环境变量预置一个；之后以数据库为准，避免覆盖用户自行修改的账号密码。"""
    from app.models import User

    if User.query.filter_by(role="admin").first() is not None:
        return

    username = app.config["ADMIN_USERNAME"]
    password = app.config["ADMIN_PASSWORD"]
    existing = User.query.filter_by(username=username).first()
    if existing is None:
        admin = User(username=username, role="admin")
        admin.set_password(password)
        db.session.add(admin)
    else:
        existing.role = "admin"
        existing.set_password(password)
    db.session.commit()


def _seed_sample_questions() -> None:
    from app.models import Question

    if Question.query.count() > 0:
        return

    samples = [
        Question(
            title="解方程：2x + 6 = 18",
            subject="数学",
            difficulty="简单",
            content="求 x 的值：2x + 6 = 18。请写出主要步骤。",
            answer="x = 6",
            analysis="两边同时减去 6，得到 2x = 12；再两边同时除以 2，得到 x = 6。",
        ),
        Question(
            title="阅读理解：主旨概括",
            subject="英语",
            difficulty="中等",
            content="短文大意：A student prepares for an exam by making a study plan and reviewing notes daily.\n问：这段文字主要说明了什么？",
            answer="制定学习计划并每天复习，有助于备考。",
            analysis="抓住关键词 study plan、reviewing notes，归纳作者强调的学习方法即可。",
        ),
    ]
    db.session.add_all(samples)
    db.session.commit()

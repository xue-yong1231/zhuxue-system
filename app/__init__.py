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

DEFAULT_SUBJECTS = [
    ("语文", "chinese"),
    ("数学", "math"),
    ("英文", "english"),
    ("物理", "physics"),
    ("化学", "chemistry"),
    ("生物", "biology"),
    ("电脑", "computer"),
    ("地理", "geography"),
    ("历史", "history"),
]


def _database_uri() -> str:
    """优先使用云平台提供的 DATABASE_URL（PostgreSQL），否则用本地 SQLite。"""
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return f"sqlite:///{BASE_DIR / 'data.db'}"
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
        _ensure_schema()
        _ensure_admin(app)
        _seed_subjects()
        _ensure_chinese_categories()
        _seed_demo_content()
        from app.content_sync import sync_content_files

        sync_content_files()

    return app


def _ensure_schema() -> None:
    """为已有 SQLite 库补齐新列（create_all 不会改旧表结构）。"""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "practice_questions" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("practice_questions")}
    if "category_id" not in cols:
        db.session.execute(
            text("ALTER TABLE practice_questions ADD COLUMN category_id INTEGER")
        )
        db.session.commit()


def _ensure_admin(app: Flask) -> None:
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


def _seed_subjects() -> None:
    from app.models import Subject

    for index, (name, slug) in enumerate(DEFAULT_SUBJECTS):
        subject = Subject.query.filter_by(slug=slug).first()
        if subject is None:
            db.session.add(Subject(name=name, slug=slug, sort_order=index))
        else:
            subject.name = name
            subject.sort_order = index
    db.session.commit()


def _ensure_chinese_categories() -> None:
    """保证语文下始终有：名句、文学常识、成语。"""
    from app.models import LearnCategory, Subject

    chinese = Subject.query.filter_by(slug="chinese").first()
    if chinese is None:
        return
    defaults = [("名句", 0), ("文学常识", 1), ("成语", 2)]
    for name, order in defaults:
        exists = LearnCategory.query.filter_by(
            subject_id=chinese.id, name=name
        ).first()
        if exists is None:
            db.session.add(
                LearnCategory(subject_id=chinese.id, name=name, sort_order=order)
            )
        else:
            exists.sort_order = order
    db.session.commit()


def _seed_demo_content() -> None:
    """首次启动时给语文放一点示例，方便立刻体验流程。"""
    from app.models import LearnCategory, LearnItem, PracticeQuestion, Subject

    chinese = Subject.query.filter_by(slug="chinese").first()
    if chinese is None:
        return
    if LearnItem.query.join(LearnCategory).filter(
        LearnCategory.subject_id == chinese.id
    ).count() > 0:
        return

    _ensure_chinese_categories()
    mingju = LearnCategory.query.filter_by(subject_id=chinese.id, name="名句").first()
    changshi = LearnCategory.query.filter_by(
        subject_id=chinese.id, name="文学常识"
    ).first()
    chengyu = LearnCategory.query.filter_by(subject_id=chinese.id, name="成语").first()

    db.session.add_all(
        [
            LearnItem(
                category_id=mingju.id,
                content="学而时习之，不亦说乎？",
                translation="学过的知识按时温习，不也是很愉快的吗？",
                explanation="出自《论语·学而》。强调复习与实践的重要性。",
                sort_order=0,
            ),
            LearnItem(
                category_id=mingju.id,
                content="三人行，必有我师焉。",
                translation="几个人一起走路，其中一定有可以做我老师的人。",
                explanation="出自《论语·述而》。提醒我们虚心向他人学习。",
                sort_order=1,
            ),
            LearnItem(
                category_id=changshi.id,
                content="《红楼梦》的作者是谁？",
                translation="曹雪芹（前八十回），高鹗续写后四十回（通行说法）。",
                explanation="中国古典四大名著之一，清代长篇小说。",
                sort_order=0,
            ),
            LearnItem(
                category_id=chengyu.id,
                content="守株待兔",
                translation="比喻不主动努力，而存万一的侥幸心理，希望得到意外的收获。",
                explanation="出自《韩非子》。株：树桩。",
                sort_order=0,
            ),
        ]
    )

    if PracticeQuestion.query.filter_by(subject_id=chinese.id).count() == 0:
        db.session.add_all(
            [
                PracticeQuestion(
                    subject_id=chinese.id,
                    category_id=mingju.id,
                    stem="“学而时习之，不亦说乎？”出自哪部著作？",
                    option_a="《孟子》",
                    option_b="《论语》",
                    option_c="《大学》",
                    option_d="《中庸》",
                    correct="B",
                    explanation="这是《论语·学而》中的名句。",
                ),
                PracticeQuestion(
                    subject_id=chinese.id,
                    category_id=chengyu.id,
                    stem="“守株待兔”常用来比喻什么？",
                    option_a="勤劳致富",
                    option_b="不劳而获、心存侥幸",
                    option_c="团结合作",
                    option_d="刻苦读书",
                    correct="B",
                    explanation="成语比喻不主动努力而希望意外收获。",
                ),
            ]
        )

    db.session.commit()

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


def utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="visitor")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(40), unique=True, nullable=False)
    slug = db.Column(db.String(40), unique=True, nullable=False, index=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    categories = db.relationship(
        "LearnCategory",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="LearnCategory.sort_order",
    )
    practices = db.relationship(
        "PracticeQuestion",
        back_populates="subject",
        cascade="all, delete-orphan",
        order_by="PracticeQuestion.id",
    )


class LearnCategory(db.Model):
    __tablename__ = "learn_categories"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    subject = db.relationship("Subject", back_populates="categories")
    items = db.relationship(
        "LearnItem",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="LearnItem.sort_order",
    )
    practices = db.relationship(
        "PracticeQuestion",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="PracticeQuestion.id",
    )


class LearnItem(db.Model):
    """学习内容：一页一条（如名句 + 翻译 + 解释）。"""

    __tablename__ = "learn_items"

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(
        db.Integer, db.ForeignKey("learn_categories.id"), nullable=False
    )
    content = db.Column(db.Text, nullable=False)
    translation = db.Column(db.Text, nullable=False, default="")
    explanation = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    category = db.relationship("LearnCategory", back_populates="items")


class PracticeQuestion(db.Model):
    """练习：四选一选择题（按学习分类，如名句/成语）。"""

    __tablename__ = "practice_questions"

    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    category_id = db.Column(
        db.Integer, db.ForeignKey("learn_categories.id"), nullable=True
    )
    stem = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct = db.Column(db.String(1), nullable=False, default="A")  # A/B/C/D
    explanation = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    subject = db.relationship("Subject", back_populates="practices")
    category = db.relationship("LearnCategory", back_populates="practices")

    def options(self) -> list[tuple[str, str]]:
        return [
            ("A", self.option_a),
            ("B", self.option_b),
            ("C", self.option_c),
            ("D", self.option_d),
        ]

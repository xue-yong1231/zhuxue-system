from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.models import Question

admin_bp = Blueprint("admin", __name__)


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@admin_bp.route("/")
@admin_required
def dashboard():
    questions = Question.query.order_by(Question.updated_at.desc()).all()
    return render_template("admin/dashboard.html", questions=questions)


@admin_bp.route("/questions/new", methods=["GET", "POST"])
@admin_required
def question_create():
    if request.method == "POST":
        question = _build_question_from_form()
        if question is None:
            return render_template("admin/question_form.html", question=None, mode="create")
        db.session.add(question)
        db.session.commit()
        flash("题目已创建。", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/question_form.html", question=None, mode="create")


@admin_bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def question_edit(question_id: int):
    question = Question.query.get_or_404(question_id)
    if request.method == "POST":
        updated = _build_question_from_form(question)
        if updated is None:
            return render_template(
                "admin/question_form.html", question=question, mode="edit"
            )
        db.session.commit()
        flash("题目已更新。", "success")
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/question_form.html", question=question, mode="edit")


@admin_bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@admin_required
def question_delete(question_id: int):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("题目已删除。", "info")
    return redirect(url_for("admin.dashboard"))


def _build_question_from_form(question: Question | None = None) -> Question | None:
    title = (request.form.get("title") or "").strip()
    subject = (request.form.get("subject") or "").strip() or "综合"
    difficulty = (request.form.get("difficulty") or "").strip() or "中等"
    content = (request.form.get("content") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    analysis = (request.form.get("analysis") or "").strip()

    if not title or not content:
        flash("标题和题干不能为空。", "danger")
        return None

    if question is None:
        question = Question()

    question.title = title
    question.subject = subject
    question.difficulty = difficulty
    question.content = content
    question.answer = answer
    question.analysis = analysis
    return question

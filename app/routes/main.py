from flask import Blueprint, render_template, request

from app.models import Question

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    keyword = (request.args.get("q") or "").strip()
    subject = (request.args.get("subject") or "").strip()
    query = Question.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (Question.title.like(like))
            | (Question.content.like(like))
            | (Question.subject.like(like))
        )
    if subject:
        query = query.filter(Question.subject == subject)
    questions = query.order_by(Question.updated_at.desc()).all()
    subjects = [
        row[0]
        for row in Question.query.with_entities(Question.subject)
        .distinct()
        .order_by(Question.subject)
        .all()
    ]
    return render_template(
        "index.html",
        questions=questions,
        subjects=subjects,
        keyword=keyword,
        subject=subject,
    )


@main_bp.route("/questions/<int:question_id>")
def question_detail(question_id: int):
    question = Question.query.get_or_404(question_id)
    return render_template("question_detail.html", question=question)

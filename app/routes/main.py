from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.models import LearnCategory, LearnItem, PracticeQuestion, Subject

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    subjects = Subject.query.order_by(Subject.sort_order, Subject.id).all()
    return render_template("index.html", subjects=subjects)


@main_bp.route("/subjects/<slug>")
def subject_home(slug: str):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    return render_template("subject_home.html", subject=subject)


@main_bp.route("/subjects/<slug>/learn")
def learn_categories(slug: str):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    categories = (
        LearnCategory.query.filter_by(subject_id=subject.id)
        .order_by(LearnCategory.sort_order, LearnCategory.id)
        .all()
    )
    return render_template(
        "learn_categories.html", subject=subject, categories=categories
    )


@main_bp.route("/subjects/<slug>/learn/<int:category_id>")
def learn_view(slug: str, category_id: int):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    category = LearnCategory.query.filter_by(
        id=category_id, subject_id=subject.id
    ).first_or_404()
    items = (
        LearnItem.query.filter_by(category_id=category.id)
        .order_by(LearnItem.sort_order, LearnItem.id)
        .all()
    )
    if not items:
        return render_template(
            "learn_view.html",
            subject=subject,
            category=category,
            item=None,
            page=1,
            total=0,
            has_prev=False,
            has_next=False,
        )

    page = request.args.get("page", 1, type=int) or 1
    page = max(1, min(page, len(items)))
    item = items[page - 1]
    return render_template(
        "learn_view.html",
        subject=subject,
        category=category,
        item=item,
        page=page,
        total=len(items),
        has_prev=page > 1,
        has_next=page < len(items),
    )


@main_bp.route("/subjects/<slug>/practice")
def practice_home(slug: str):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    total = PracticeQuestion.query.filter_by(subject_id=subject.id).count()
    return render_template("practice_home.html", subject=subject, total=total)


@main_bp.route("/subjects/<slug>/practice/<int:question_id>", methods=["GET", "POST"])
def practice_question(slug: str, question_id: int):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    questions = (
        PracticeQuestion.query.filter_by(subject_id=subject.id)
        .order_by(PracticeQuestion.id)
        .all()
    )
    if not questions:
        flash("暂无练习题。", "info")
        return redirect(url_for("main.practice_home", slug=slug))

    ids = [q.id for q in questions]
    if question_id not in ids:
        return redirect(
            url_for("main.practice_question", slug=slug, question_id=ids[0])
        )

    question = next(q for q in questions if q.id == question_id)
    index = ids.index(question_id)
    result = None
    chosen = None

    if request.method == "POST":
        chosen = (request.form.get("answer") or "").upper().strip()
        if chosen not in {"A", "B", "C", "D"}:
            flash("请选择一个选项。", "warning")
        else:
            result = chosen == question.correct.upper()

    next_id = ids[index + 1] if index + 1 < len(ids) else None
    prev_id = ids[index - 1] if index > 0 else None

    return render_template(
        "practice_question.html",
        subject=subject,
        question=question,
        index=index + 1,
        total=len(questions),
        result=result,
        chosen=chosen,
        next_id=next_id,
        prev_id=prev_id,
    )


@main_bp.route("/subjects/<slug>/practice/start")
def practice_start(slug: str):
    subject = Subject.query.filter_by(slug=slug).first_or_404()
    first = (
        PracticeQuestion.query.filter_by(subject_id=subject.id)
        .order_by(PracticeQuestion.id)
        .first()
    )
    if first is None:
        flash("暂无练习题，请等待房主出题。", "info")
        return redirect(url_for("main.practice_home", slug=slug))
    return redirect(
        url_for("main.practice_question", slug=slug, question_id=first.id)
    )

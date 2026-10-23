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
from app.bulk_import import parse_learn_items
from app.models import LearnCategory, LearnItem, PracticeQuestion, Subject

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
    subjects = Subject.query.order_by(Subject.sort_order, Subject.id).all()
    return render_template("admin/dashboard.html", subjects=subjects)


@admin_bp.route("/subjects/<int:subject_id>")
@admin_required
def subject_manage(subject_id: int):
    subject = Subject.query.get_or_404(subject_id)
    categories = (
        LearnCategory.query.filter_by(subject_id=subject.id)
        .order_by(LearnCategory.sort_order, LearnCategory.id)
        .all()
    )
    practices = (
        PracticeQuestion.query.filter_by(subject_id=subject.id)
        .order_by(PracticeQuestion.id)
        .all()
    )
    return render_template(
        "admin/subject_manage.html",
        subject=subject,
        categories=categories,
        practices=practices,
    )


# ---------- 学习分类 ----------
@admin_bp.route("/subjects/<int:subject_id>/categories/new", methods=["GET", "POST"])
@admin_required
def category_create(subject_id: int):
    subject = Subject.query.get_or_404(subject_id)
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("分类名称不能为空。", "danger")
        else:
            sort_order = request.form.get("sort_order", type=int) or 0
            db.session.add(
                LearnCategory(subject_id=subject.id, name=name, sort_order=sort_order)
            )
            db.session.commit()
            flash("学习分类已创建。", "success")
            return redirect(url_for("admin.subject_manage", subject_id=subject.id))
    return render_template(
        "admin/category_form.html", subject=subject, category=None, mode="create"
    )


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def category_edit(category_id: int):
    category = LearnCategory.query.get_or_404(category_id)
    subject = category.subject
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("分类名称不能为空。", "danger")
        else:
            category.name = name
            category.sort_order = request.form.get("sort_order", type=int) or 0
            db.session.commit()
            flash("分类已更新。", "success")
            return redirect(url_for("admin.subject_manage", subject_id=subject.id))
    return render_template(
        "admin/category_form.html", subject=subject, category=category, mode="edit"
    )


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def category_delete(category_id: int):
    category = LearnCategory.query.get_or_404(category_id)
    subject_id = category.subject_id
    db.session.delete(category)
    db.session.commit()
    flash("分类及其学习内容已删除。", "info")
    return redirect(url_for("admin.subject_manage", subject_id=subject_id))


# ---------- 学习条目 ----------
@admin_bp.route("/categories/<int:category_id>/items")
@admin_required
def item_list(category_id: int):
    category = LearnCategory.query.get_or_404(category_id)
    items = (
        LearnItem.query.filter_by(category_id=category.id)
        .order_by(LearnItem.sort_order, LearnItem.id)
        .all()
    )
    return render_template(
        "admin/item_list.html",
        subject=category.subject,
        category=category,
        items=items,
    )


@admin_bp.route("/categories/<int:category_id>/items/new", methods=["GET", "POST"])
@admin_required
def item_create(category_id: int):
    category = LearnCategory.query.get_or_404(category_id)
    if request.method == "POST":
        item = _build_item_from_form(category_id=category.id)
        if item is None:
            return render_template(
                "admin/item_form.html",
                subject=category.subject,
                category=category,
                item=None,
                mode="create",
            )
        db.session.add(item)
        db.session.commit()
        flash("学习内容已添加。", "success")
        return redirect(url_for("admin.item_list", category_id=category.id))
    return render_template(
        "admin/item_form.html",
        subject=category.subject,
        category=category,
        item=None,
        mode="create",
    )


@admin_bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def item_edit(item_id: int):
    item = LearnItem.query.get_or_404(item_id)
    category = item.category
    if request.method == "POST":
        updated = _build_item_from_form(category_id=category.id, item=item)
        if updated is None:
            return render_template(
                "admin/item_form.html",
                subject=category.subject,
                category=category,
                item=item,
                mode="edit",
            )
        db.session.commit()
        flash("学习内容已更新。", "success")
        return redirect(url_for("admin.item_list", category_id=category.id))
    return render_template(
        "admin/item_form.html",
        subject=category.subject,
        category=category,
        item=item,
        mode="edit",
    )


@admin_bp.route("/items/<int:item_id>/delete", methods=["POST"])
@admin_required
def item_delete(item_id: int):
    item = LearnItem.query.get_or_404(item_id)
    category_id = item.category_id
    db.session.delete(item)
    db.session.commit()
    flash("学习内容已删除。", "info")
    return redirect(url_for("admin.item_list", category_id=category_id))


@admin_bp.route("/categories/<int:category_id>/items/bulk", methods=["GET", "POST"])
@admin_required
def item_bulk_import(category_id: int):
    category = LearnCategory.query.get_or_404(category_id)
    preview = None
    if request.method == "POST":
        raw = request.form.get("raw_text") or ""
        parsed = parse_learn_items(raw)
        action = request.form.get("action") or "preview"
        if not parsed:
            flash("没有解析到有效内容，请检查格式。", "danger")
        elif action == "preview":
            preview = parsed
            flash(f"预览：共解析到 {len(parsed)} 条，确认无误后点「确认导入」。", "info")
        else:
            start = LearnItem.query.filter_by(category_id=category.id).count()
            for i, row in enumerate(parsed):
                db.session.add(
                    LearnItem(
                        category_id=category.id,
                        content=row["content"],
                        translation=row["translation"],
                        explanation=row["explanation"],
                        sort_order=start + i,
                    )
                )
            db.session.commit()
            flash(f"已成功导入 {len(parsed)} 条学习内容。", "success")
            return redirect(url_for("admin.item_list", category_id=category.id))
        return render_template(
            "admin/item_bulk.html",
            subject=category.subject,
            category=category,
            raw_text=raw,
            preview=preview,
        )
    return render_template(
        "admin/item_bulk.html",
        subject=category.subject,
        category=category,
        raw_text="",
        preview=None,
    )


def _build_item_from_form(
    category_id: int, item: LearnItem | None = None
) -> LearnItem | None:
    content = (request.form.get("content") or "").strip()
    translation = (request.form.get("translation") or "").strip()
    explanation = (request.form.get("explanation") or "").strip()
    sort_order = request.form.get("sort_order", type=int) or 0
    if not content:
        flash("正文内容不能为空。", "danger")
        return None
    if item is None:
        item = LearnItem(category_id=category_id)
    item.content = content
    item.translation = translation
    item.explanation = explanation
    item.sort_order = sort_order
    return item


# ---------- 练习题 ----------
@admin_bp.route("/subjects/<int:subject_id>/practice/new", methods=["GET", "POST"])
@admin_required
def practice_create(subject_id: int):
    subject = Subject.query.get_or_404(subject_id)
    categories = (
        LearnCategory.query.filter_by(subject_id=subject.id)
        .order_by(LearnCategory.sort_order, LearnCategory.id)
        .all()
    )
    if request.method == "POST":
        question = _build_practice_from_form(subject_id=subject.id)
        if question is None:
            return render_template(
                "admin/practice_form.html",
                subject=subject,
                categories=categories,
                question=None,
                mode="create",
            )
        db.session.add(question)
        db.session.commit()
        flash("练习题已创建。", "success")
        return redirect(url_for("admin.subject_manage", subject_id=subject.id))
    return render_template(
        "admin/practice_form.html",
        subject=subject,
        categories=categories,
        question=None,
        mode="create",
    )


@admin_bp.route("/practice/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def practice_edit(question_id: int):
    question = PracticeQuestion.query.get_or_404(question_id)
    subject = question.subject
    categories = (
        LearnCategory.query.filter_by(subject_id=subject.id)
        .order_by(LearnCategory.sort_order, LearnCategory.id)
        .all()
    )
    if request.method == "POST":
        updated = _build_practice_from_form(subject_id=subject.id, question=question)
        if updated is None:
            return render_template(
                "admin/practice_form.html",
                subject=subject,
                categories=categories,
                question=question,
                mode="edit",
            )
        db.session.commit()
        flash("练习题已更新。", "success")
        return redirect(url_for("admin.subject_manage", subject_id=subject.id))
    return render_template(
        "admin/practice_form.html",
        subject=subject,
        categories=categories,
        question=question,
        mode="edit",
    )


@admin_bp.route("/practice/<int:question_id>/delete", methods=["POST"])
@admin_required
def practice_delete(question_id: int):
    question = PracticeQuestion.query.get_or_404(question_id)
    subject_id = question.subject_id
    db.session.delete(question)
    db.session.commit()
    flash("练习题已删除。", "info")
    return redirect(url_for("admin.subject_manage", subject_id=subject_id))


def _build_practice_from_form(
    subject_id: int, question: PracticeQuestion | None = None
) -> PracticeQuestion | None:
    stem = (request.form.get("stem") or "").strip()
    option_a = (request.form.get("option_a") or "").strip()
    option_b = (request.form.get("option_b") or "").strip()
    option_c = (request.form.get("option_c") or "").strip()
    option_d = (request.form.get("option_d") or "").strip()
    correct = (request.form.get("correct") or "A").upper().strip()
    explanation = (request.form.get("explanation") or "").strip()
    category_id = request.form.get("category_id", type=int)

    if not category_id:
        flash("请选择所属分类（名句 / 文学常识 / 成语等）。", "danger")
        return None
    category = LearnCategory.query.filter_by(
        id=category_id, subject_id=subject_id
    ).first()
    if category is None:
        flash("分类无效。", "danger")
        return None

    if not stem or not all([option_a, option_b, option_c, option_d]):
        flash("题干与四个选项都不能为空。", "danger")
        return None
    if correct not in {"A", "B", "C", "D"}:
        flash("正确答案必须是 A / B / C / D。", "danger")
        return None

    if question is None:
        question = PracticeQuestion(subject_id=subject_id)

    question.category_id = category.id
    question.stem = stem
    question.option_a = option_a
    question.option_b = option_b
    question.option_c = option_c
    question.option_d = option_d
    question.correct = correct
    question.explanation = explanation
    return question

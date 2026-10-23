from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("登录成功。", "success")
            next_url = request.args.get("next")
            if user.is_admin:
                return redirect(next_url or url_for("admin.dashboard"))
            return redirect(next_url or url_for("main.index"))
        flash("用户名或密码错误。", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录。", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        new_username = (request.form.get("username") or "").strip()
        current_password = request.form.get("current_password") or ""
        new_password = request.form.get("new_password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not current_user.check_password(current_password):
            flash("当前密码不正确。", "danger")
            return render_template("account.html")

        if not new_username:
            flash("用户名不能为空。", "danger")
            return render_template("account.html")

        if len(new_username) > 64:
            flash("用户名过长（最多 64 个字符）。", "danger")
            return render_template("account.html")

        conflict = User.query.filter(
            User.username == new_username, User.id != current_user.id
        ).first()
        if conflict:
            flash("该用户名已被占用，请换一个。", "danger")
            return render_template("account.html")

        if new_password or confirm_password:
            if len(new_password) < 6:
                flash("新密码至少 6 位。", "danger")
                return render_template("account.html")
            if new_password != confirm_password:
                flash("两次输入的新密码不一致。", "danger")
                return render_template("account.html")
            current_user.set_password(new_password)

        current_user.username = new_username
        db.session.commit()
        flash("账号信息已更新。下次请用新用户名/密码登录。", "success")
        return redirect(url_for("auth.account"))

    return render_template("account.html")

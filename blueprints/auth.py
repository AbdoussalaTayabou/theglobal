"""Authentification des lecteurs (signup / login / logout / compte / favoris)."""
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, abort)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from email_validator import validate_email, EmailNotValidError

from models import db, User, Article, Favorite
from extensions import limiter

bp = Blueprint("auth", __name__, url_prefix="/auth")
account_bp = Blueprint("account", __name__, url_prefix="/compte")


# ---------- Signup ----------------------------------------------------------

@bp.route("/inscription", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", methods=["POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        errors = []
        if not (3 <= len(username) <= 80):
            errors.append("Le pseudo doit faire 3 à 80 caractères.")
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            errors.append("Email invalide.")
        if len(password) < 8:
            errors.append("Mot de passe : 8 caractères minimum.")
        if password != password2:
            errors.append("Les mots de passe ne correspondent pas.")
        if User.query.filter(or_(User.username == username, User.email == email)).first():
            errors.append("Pseudo ou email déjà utilisé.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("auth/signup.html", username=username, email=email)

        u = User(username=username, email=email, is_admin=False, is_active_flag=True)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        login_user(u)
        flash("Bienvenue !", "success")
        return redirect(url_for("account.dashboard"))

    return render_template("auth/signup.html")


# ---------- Login -----------------------------------------------------------

@bp.route("/connexion", methods=["GET", "POST"])
@limiter.limit("10 per minute; 50 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("account.dashboard"))

    if request.method == "POST":
        ident = (request.form.get("identifier") or "").strip()
        password = request.form.get("password") or ""
        u = User.query.filter(or_(User.username == ident, User.email == ident.lower())).first()
        if u and u.check_password(password) and u.is_active_flag:
            login_user(u, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next") or url_for("account.dashboard")
            return redirect(next_url)
        flash("Identifiants invalides.", "error")

    return render_template("auth/login.html")


@bp.route("/deconnexion", methods=["POST", "GET"])
@login_required
def logout():
    logout_user()
    flash("À bientôt.", "success")
    return redirect(url_for("index"))


# ---------- Account ---------------------------------------------------------

@account_bp.route("/")
@login_required
def dashboard():
    fav_count = current_user.favorites.count()
    return render_template("account/dashboard.html", fav_count=fav_count)


@account_bp.route("/favoris")
@login_required
def favorites():
    favs = (db.session.query(Article)
            .join(Favorite, Favorite.article_id == Article.id)
            .filter(Favorite.user_id == current_user.id)
            .order_by(Favorite.created_at.desc())
            .all())
    return render_template("account/favorites.html", articles=favs)


@account_bp.route("/favoris/toggle/<int:article_id>", methods=["POST"])
@login_required
def toggle_favorite(article_id):
    art = Article.query.get_or_404(article_id)
    fav = Favorite.query.filter_by(user_id=current_user.id, article_id=art.id).first()
    if fav:
        db.session.delete(fav)
        action = "removed"
    else:
        db.session.add(Favorite(user_id=current_user.id, article_id=art.id))
        action = "added"
    db.session.commit()

    if request.headers.get("X-Requested-With") == "fetch":
        return {"ok": True, "action": action}, 200
    nxt = request.form.get("next") or request.referrer or url_for("index")
    return redirect(nxt)

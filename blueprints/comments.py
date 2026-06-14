"""Commentaires modérés."""
from flask import Blueprint, request, redirect, url_for, flash, abort
from flask_login import current_user
from email_validator import validate_email, EmailNotValidError
import bleach

from models import db, Article, Comment
from extensions import limiter

bp = Blueprint("comments", __name__, url_prefix="/commentaires")

ALLOWED_TAGS = ["b", "i", "em", "strong", "a", "br", "p"]
ALLOWED_ATTRS = {"a": ["href", "title", "rel"]}


@bp.route("/<int:article_id>", methods=["POST"])
@limiter.limit("5 per minute; 30 per hour; 100 per day")
def post(article_id):
    art = Article.query.get_or_404(article_id)
    if not art.is_live():
        abort(404)

    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    content = (request.form.get("content") or "").strip()
    honeypot = request.form.get("website")  # antispam

    if current_user.is_authenticated:
        name = name or current_user.username
        email = email or (current_user.email or "anonymous@example.com")

    errors = []
    if honeypot:
        errors.append("spam")
    if not (2 <= len(name) <= 120):
        errors.append("Nom requis (2–120 caractères).")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        errors.append("Email invalide.")
    if not (5 <= len(content) <= 4000):
        errors.append("Commentaire : 5 à 4000 caractères.")

    if errors:
        for e in errors:
            if e != "spam":
                flash(e, "error")
        return redirect(url_for("article_detail", slug=art.slug) + "#commentaires")

    clean = bleach.clean(content, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

    c = Comment(
        article_id=art.id,
        user_id=current_user.id if current_user.is_authenticated else None,
        author_name=name[:120],
        author_email=email[:255],
        content=clean,
        status="pending",
        ip=(request.headers.get("X-Forwarded-For") or request.remote_addr or "")[:45],
    )
    db.session.add(c)
    db.session.commit()
    flash("Merci ! Votre commentaire sera publié après modération.", "success")
    return redirect(url_for("article_detail", slug=art.slug) + "#commentaires")

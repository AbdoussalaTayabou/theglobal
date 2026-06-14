"""Newsletter avec double opt-in.

L'envoi réel d'email n'est pas branché (à brancher sur SMTP / Brevo / Mailgun).
En l'absence de config SMTP, le lien de confirmation est affiché en flash
(utile en dev) et imprimé dans la console.
"""
import os
from datetime import datetime
from flask import (Blueprint, request, redirect, url_for, flash, abort,
                   render_template, current_app)
from email_validator import validate_email, EmailNotValidError

from models import db, Subscriber
from extensions import limiter

bp = Blueprint("newsletter", __name__, url_prefix="/newsletter")


def _send_confirmation_email(sub: Subscriber, confirm_url: str):
    """Branchement SMTP optionnel via variables d'environnement."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        print(f"[newsletter] Confirmation URL pour {sub.email}: {confirm_url}")
        return False
    try:
        import smtplib
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = "Confirmez votre inscription — The Global Chronicle"
        msg["From"] = os.environ.get("SMTP_FROM", "no-reply@globalchronicle.local")
        msg["To"] = sub.email
        msg.set_content(f"Bonjour,\n\nConfirmez votre inscription : {confirm_url}\n\n— The Global Chronicle")
        with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587"))) as s:
            if os.environ.get("SMTP_TLS", "1") == "1":
                s.starttls()
            user = os.environ.get("SMTP_USER")
            pwd = os.environ.get("SMTP_PASS")
            if user and pwd:
                s.login(user, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        current_app.logger.warning(f"SMTP failed: {e}")
        print(f"[newsletter] Confirmation URL pour {sub.email}: {confirm_url}")
        return False


@bp.route("/inscription", methods=["POST"])
@limiter.limit("3 per minute; 10 per hour; 30 per day")
def subscribe():
    email = (request.form.get("email") or "").strip().lower()
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        flash("Email invalide.", "error")
        return redirect(request.referrer or url_for("index"))

    sub = Subscriber.query.filter_by(email=email).first()
    if not sub:
        sub = Subscriber(email=email)
        db.session.add(sub)
        db.session.commit()
    elif sub.confirmed:
        flash("Vous êtes déjà inscrit·e.", "success")
        return redirect(request.referrer or url_for("index"))

    confirm_url = url_for("newsletter.confirm", token=sub.confirm_token, _external=True)
    _send_confirmation_email(sub, confirm_url)
    flash("Vérifiez votre boîte mail pour confirmer votre inscription.", "success")
    return redirect(request.referrer or url_for("index"))


@bp.route("/confirmer/<token>")
def confirm(token):
    sub = Subscriber.query.filter_by(confirm_token=token).first()
    if not sub:
        abort(404)
    if not sub.confirmed:
        sub.confirmed = True
        sub.confirmed_at = datetime.utcnow()
        db.session.commit()
    return render_template("newsletter/confirmed.html", sub=sub)


@bp.route("/desinscription/<token>")
def unsubscribe(token):
    sub = Subscriber.query.filter_by(unsubscribe_token=token).first()
    if not sub:
        abort(404)
    db.session.delete(sub)
    db.session.commit()
    return render_template("newsletter/unsubscribed.html")

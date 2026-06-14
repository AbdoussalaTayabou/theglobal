"""Pages légales + contact + bandeau cookies.

Routes :
  /mentions-legales
  /confidentialite
  /cgu
  /cookies
  /contact (GET + POST)

Les messages de contact sont enregistrés dans data/contact_messages.jsonl
(simple, pas de migration DB requise). Tu peux les lire ensuite ou brancher
un envoi d'email (Flask-Mail / Brevo / Resend) plus tard.
"""
import os
import json
import re
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app)

bp = Blueprint("legal", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/mentions-legales")
def mentions():
    return render_template("legal/mentions.html")


@bp.route("/confidentialite")
def privacy():
    return render_template("legal/privacy.html")


@bp.route("/cgu")
def cgu():
    return render_template("legal/cgu.html")


@bp.route("/cookies")
def cookies():
    return render_template("legal/cookies.html")


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()[:120]
        email = (request.form.get("email") or "").strip()[:200]
        subject = (request.form.get("subject") or "").strip()[:200]
        message = (request.form.get("message") or "").strip()[:5000]
        # Honeypot anti-spam
        honey = (request.form.get("website") or "").strip()

        errors = []
        if honey:
            # bot — on fait semblant que ça a marché
            flash("Message envoyé. Merci !", "success")
            return redirect(url_for("legal.contact"))
        if len(name) < 2:
            errors.append("Nom requis.")
        if not EMAIL_RE.match(email):
            errors.append("Email invalide.")
        if len(subject) < 3:
            errors.append("Sujet requis.")
        if len(message) < 10:
            errors.append("Message trop court (10 caractères minimum).")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("legal/contact.html",
                                   form={"name": name, "email": email,
                                         "subject": subject, "message": message})

        # Sauvegarde
        try:
            base = current_app.root_path
            data_dir = os.path.join(base, "data")
            os.makedirs(data_dir, exist_ok=True)
            entry = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "ip": request.headers.get("X-Forwarded-For", request.remote_addr or "").split(",")[0].strip(),
                "ua": request.headers.get("User-Agent", "")[:300],
                "name": name, "email": email,
                "subject": subject, "message": message,
            }
            with open(os.path.join(data_dir, "contact_messages.jsonl"), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            current_app.logger.exception("contact save failed: %s", e)
            flash("Erreur interne, réessaie plus tard.", "danger")
            return render_template("legal/contact.html",
                                   form={"name": name, "email": email,
                                         "subject": subject, "message": message})

        flash("Merci, votre message a bien été envoyé. Nous vous répondrons rapidement.", "success")
        return redirect(url_for("legal.contact"))

    return render_template("legal/contact.html", form={})

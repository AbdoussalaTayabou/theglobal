"""Notifications push (Web Push / VAPID).

- /push/vapid-public-key : clé publique pour le SW navigateur
- /push/subscribe        : enregistre une PushSubscription
- /push/unsubscribe      : supprime l'abonnement
- /push/broadcast        : (admin) envoie une notification à tous les abonnés
                          d'un topic (nécessite pywebpush + VAPID_PRIVATE_KEY)

Configuration env :
- VAPID_PUBLIC_KEY  (base64 url-safe, raw P-256 public key, 65 octets)
- VAPID_PRIVATE_KEY (base64 url-safe)
- VAPID_CLAIM_EMAIL (mailto: pour identifier l'expéditeur)

Si les clés ne sont pas fournies, l'abonnement est désactivé côté front
(la route vapid-public-key renvoie 503).
"""
import os
import json
from flask import Blueprint, request, jsonify, abort, current_app
from flask_login import current_user, login_required

from models import db, PushSubscription
from extensions import limiter

bp = Blueprint("push", __name__, url_prefix="/push")


def _vapid_public():
    return os.environ.get("VAPID_PUBLIC_KEY", "").strip()


def _vapid_private():
    return os.environ.get("VAPID_PRIVATE_KEY", "").strip()


def _vapid_email():
    return os.environ.get("VAPID_CLAIM_EMAIL", "mailto:contact@example.com")


@bp.route("/vapid-public-key")
def vapid_public_key():
    key = _vapid_public()
    if not key:
        return jsonify({"error": "push disabled (VAPID_PUBLIC_KEY missing)"}), 503
    return jsonify({"publicKey": key})


@bp.route("/subscribe", methods=["POST"])
@limiter.limit("10 per minute; 60 per hour")
def subscribe():
    """Body JSON: { subscription: PushSubscriptionJSON, topic?: str }"""
    data = request.get_json(silent=True) or {}
    sub = data.get("subscription") or {}
    endpoint = (sub.get("endpoint") or "").strip()
    keys = sub.get("keys") or {}
    p256dh = (keys.get("p256dh") or "").strip()
    auth = (keys.get("auth") or "").strip()
    topic = (data.get("topic") or "all").strip()[:80]

    if not (endpoint and p256dh and auth):
        return jsonify({"error": "invalid subscription"}), 400

    existing = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if existing:
        existing.p256dh = p256dh
        existing.auth = auth
        existing.topic = topic
        if current_user.is_authenticated:
            existing.user_id = current_user.id
    else:
        db.session.add(PushSubscription(
            endpoint=endpoint, p256dh=p256dh, auth=auth, topic=topic,
            user_id=current_user.id if current_user.is_authenticated else None,
        ))
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        return jsonify({"error": "missing endpoint"}), 400
    PushSubscription.query.filter_by(endpoint=endpoint).delete()
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/broadcast", methods=["POST"])
@login_required
@limiter.limit("5 per minute")
def broadcast():
    """Envoie une notification à tous les abonnés d'un topic.
    Réservé aux admins. Body JSON: { title, body, url?, topic? }
    """
    if not getattr(current_user, "is_admin", False):
        abort(403)

    priv = _vapid_private()
    pub = _vapid_public()
    if not (priv and pub):
        return jsonify({"error": "VAPID keys not configured"}), 503

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return jsonify({"error": "pywebpush not installed"}), 500

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()[:120]
    body = (data.get("body") or "").strip()[:300]
    url = (data.get("url") or "/").strip()[:500]
    topic = (data.get("topic") or "all").strip()[:80]
    if not title:
        return jsonify({"error": "title required"}), 400

    payload = json.dumps({"title": title, "body": body, "url": url})
    q = PushSubscription.query
    if topic != "all":
        q = q.filter(PushSubscription.topic.in_([topic, "all"]))

    sent, failed, removed = 0, 0, 0
    for s in q.all():
        try:
            webpush(
                subscription_info={
                    "endpoint": s.endpoint,
                    "keys": {"p256dh": s.p256dh, "auth": s.auth},
                },
                data=payload,
                vapid_private_key=priv,
                vapid_claims={"sub": _vapid_email()},
            )
            sent += 1
        except WebPushException as e:
            # 404 / 410 -> abonnement expiré, on nettoie
            status = getattr(getattr(e, "response", None), "status_code", None)
            if status in (404, 410):
                db.session.delete(s)
                removed += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    db.session.commit()
    return jsonify({"sent": sent, "failed": failed, "removed": removed})

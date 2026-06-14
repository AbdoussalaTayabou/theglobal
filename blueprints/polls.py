"""Sondage / Question du jour — vote anonyme avec anti-double-vote."""
import hashlib
from flask import Blueprint, request, jsonify, abort
from flask_login import current_user

from models import db, Poll, PollOption, PollVote
from extensions import limiter

bp = Blueprint("polls", __name__, url_prefix="/sondage")


def _voter_key():
    """Identifie un votant : user_id si connecté, sinon hash(IP+UA)."""
    if current_user.is_authenticated:
        return f"u:{current_user.id}"
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()
    ua = request.headers.get("User-Agent", "")[:200]
    h = hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:32]
    return f"a:{h}"


@bp.route("/<int:poll_id>/vote/<int:option_id>", methods=["POST"])
@limiter.limit("10 per minute; 30 per hour")
def vote(poll_id, option_id):
    poll = Poll.query.get_or_404(poll_id)
    if not poll.active:
        abort(403)
    opt = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first_or_404()

    key = _voter_key()
    existing = PollVote.query.filter_by(poll_id=poll.id, voter_key=key).first()
    if existing:
        return jsonify(_results(poll, already_voted=True))

    opt.votes = (opt.votes or 0) + 1
    db.session.add(PollVote(poll_id=poll.id, option_id=opt.id, voter_key=key))
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "vote failed"}), 500

    return jsonify(_results(poll))


@bp.route("/<int:poll_id>/results")
def results(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    return jsonify(_results(poll))


def _results(poll, already_voted=False):
    total = poll.total_votes or 0
    return {
        "poll_id": poll.id,
        "question": poll.question,
        "total": total,
        "already_voted": already_voted,
        "options": [
            {
                "id": o.id,
                "label": o.label,
                "votes": o.votes or 0,
                "pct": round((o.votes or 0) * 100 / total, 1) if total else 0,
            }
            for o in poll.options
        ],
    }


def get_active_poll_for(article=None):
    """Renvoie un poll actif à afficher (le plus récent)."""
    return Poll.query.filter_by(active=True).order_by(Poll.created_at.desc()).first()


def has_voted(poll):
    if not poll:
        return False
    key = _voter_key()
    return PollVote.query.filter_by(poll_id=poll.id, voter_key=key).first() is not None

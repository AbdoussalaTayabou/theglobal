"""Entry point — The Global Chronicle (v4).

Ajoute : Auteurs / Tags / Brouillons / Scheduling, SEO complet, RSS,
Newsletter (double opt-in), comptes utilisateurs + favoris, commentaires modérés.
"""
import os
import json
import secrets as _secrets

# Charge .env si présent (DATABASE_URL, SECRET_KEY, etc.)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from datetime import datetime
from flask import (Flask, render_template, abort, request, url_for,
                   redirect, flash)
from flask_wtf.csrf import CSRFProtect
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import limiter, talisman, migrate

csrf = CSRFProtect()
from sqlalchemy import or_

from models import (db, Article, Category, BreakingNews, Tag, Author,
                    Comment, Favorite, init_db)
from admin_panel import init_admin
from blueprints.auth import bp as auth_bp, account_bp
from blueprints.comments import bp as comments_bp
from blueprints.newsletter import bp as newsletter_bp
from blueprints.seo import bp as seo_bp

BASE = os.path.dirname(os.path.abspath(__file__))
PLACEHOLDER_IMG = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200&q=70"


def published_q():
    now = datetime.utcnow()
    return Article.query.filter(
        or_(Article.status == "published", Article.published.is_(True)),
        or_(Article.published_at.is_(None), Article.published_at <= now),
    )


def compute_related(article, limit=4):
    """Articles similaires : score par catégorie partagée + tags en commun."""
    base = published_q().filter(Article.id != article.id)
    candidates = []

    tag_ids = [t.id for t in article.tags]
    if tag_ids:
        cand = (base.filter(Article.tags.any(Tag.id.in_(tag_ids)))
                .order_by(Article.published_at.desc().nullslast(),
                          Article.created_at.desc())
                .limit(20).all())
        candidates.extend(cand)
    if article.category_id:
        cand = (base.filter(Article.category_id == article.category_id)
                .order_by(Article.published_at.desc().nullslast(),
                          Article.created_at.desc())
                .limit(20).all())
        candidates.extend(cand)

    # Scoring : +2 par tag commun, +1 si même catégorie
    seen, scored = set(), []
    for c in candidates:
        if c.id in seen:
            continue
        seen.add(c.id)
        score = 0
        if c.category_id and c.category_id == article.category_id:
            score += 1
        score += 2 * len(set(t.id for t in c.tags) & set(tag_ids))
        scored.append((score, c))
    scored.sort(key=lambda x: (-x[0],
                               -(x[1].published_at or x[1].created_at).timestamp()))
    out = [c for _, c in scored[:limit]]
    # Fallback : compléter avec récents si pas assez
    if len(out) < limit:
        need = limit - len(out)
        extra = (base.filter(~Article.id.in_([o.id for o in out]) if out else True)
                 .order_by(Article.published_at.desc().nullslast(),
                           Article.created_at.desc())
                 .limit(need).all())
        out.extend(extra)
    return out


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    # --- SECRET_KEY (jamais hardcodée) -------------------------------------
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "SECRET_KEY env var is required in production. "
                "Set SECRET_KEY=<long random hex> before starting the app."
            )
        # En dev seulement : générer une clé éphémère (sessions invalidées au redémarrage)
        secret_key = _secrets.token_hex(32)
        print("[WARN] SECRET_KEY non définie : clé éphémère générée pour le dev.")

    # --- Base de données : PostgreSQL en prod, SQLite en dev par défaut ----
    # Définir DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname
    # (Heroku/Render fournissent "postgres://..." → on normalise.)
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://") and "+psycopg2" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if not database_url:
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "DATABASE_URL est requis en production. "
                "Exemple : postgresql+psycopg2://user:pass@host:5432/chronicle"
            )
        database_url = f"sqlite:///{os.path.join(BASE, 'chronicle.db')}"

    engine_options = {}
    if database_url.startswith("postgresql"):
        engine_options = {
            "pool_pre_ping": True,
            "pool_recycle": 280,
            "pool_size": 10,
            "max_overflow": 20,
        }

    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=database_url,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        # Limite stricte uploads (10 Mo). À ajuster si besoin.
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        CKEDITOR_PKG_TYPE="standard",
        CKEDITOR_HEIGHT=420,
        FLASK_ADMIN_SWATCH="flatly",
        SITE_NAME="The Global Chronicle",
        SITE_TAGLINE="The Voice of Global Press",
        # CSRF : durée du token + secure cookies en prod
        WTF_CSRF_TIME_LIMIT=3600,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    )

    # Protection CSRF globale (Flask-WTF)
    csrf.init_app(app)

    # Flask-Admin gère son propre CSRF via `SecureForm` (form_base_class).
    # Le double système (CSRFProtect global + SecureForm) provoque des 400
    # "CSRF token missing" sur les formulaires create/edit/upload/inline
    # de l'admin. On exempte donc l'ensemble du blueprint admin.
    # Handler lisible en cas d'erreur CSRF (au lieu d'une page 400 brute)
    from flask_wtf.csrf import CSRFError
    @app.errorhandler(CSRFError)
    def _csrf_err(e):
        return (f"Session expirée ou jeton CSRF invalide ({e.description}). "
                "Rechargez la page et réessayez.", 400)

    # ProxyFix : nécessaire si l'app tourne derrière Nginx/Cloudflare pour que
    # get_remote_address (Flask-Limiter) et request.remote_addr soient corrects.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # --- Rate limiting (Flask-Limiter) -------------------------------------
    limiter.init_app(app)

    # --- Headers de sécurité (Flask-Talisman) ------------------------------
    is_prod = os.environ.get("FLASK_ENV") == "production"
    # CSP volontairement permissive pour CKEditor + CDNs front (Bootstrap, etc.)
    # À durcir si vous self-hostez toutes les ressources.
    csp = {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:", "blob:", "https:"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https:"],
        "style-src": ["'self'", "'unsafe-inline'", "https:"],
        "font-src": ["'self'", "data:", "https:"],
        "media-src": ["'self'", "data:", "blob:", "https:"],
        "connect-src": ["'self'", "https:"],
        "worker-src": ["'self'"],
        "frame-ancestors": ["'self'"],
    }
    talisman.init_app(
        app,
        force_https=is_prod,
        strict_transport_security=is_prod,
        strict_transport_security_max_age=60 * 60 * 24 * 365,
        session_cookie_secure=is_prod,
        content_security_policy=csp,
        content_security_policy_nonce_in=[],
        frame_options="SAMEORIGIN",
        referrer_policy="strict-origin-when-cross-origin",
    )

    for sub in ("images", "media", "pdfs", "authors"):
        os.makedirs(os.path.join(BASE, "static", "uploads", sub), exist_ok=True)

    db.init_app(app)
    # Flask-Migrate (Alembic) — remplace migrate.py maison.
    migrate.init_app(app, db)
    with app.app_context():
        # Si des migrations Alembic existent, on laisse `flask db upgrade`
        # gérer le schéma. Sinon (dev SQLite sans migrations), bootstrap.
        from sqlalchemy import inspect as _sa_inspect
        migrations_dir = os.path.join(BASE, "migrations", "versions")
        has_migrations = (
            os.path.isdir(migrations_dir)
            and any(f.endswith(".py") for f in os.listdir(migrations_dir))
        )
        insp = _sa_inspect(db.engine)
        existing = set(insp.get_table_names())
        if has_migrations and "alembic_version" not in existing:
            print("[INFO] Migrations Alembic présentes. Lance `flask db upgrade`.")
        if not has_migrations or not existing:
            # Premier démarrage : crée le schéma + seed minimal.
            init_db()

    init_admin(app)

    # Exempte Flask-Admin du CSRFProtect global (SecureForm prend le relais).
    # IMPORTANT : chaque ModelView de Flask-Admin (Article, Category, Tag, ...)
    # enregistre son PROPRE blueprint Flask. Exempter uniquement "admin"
    # laissait tous les POST create/edit/delete/upload bloqués par CSRFProtect
    # (d'où l'impossibilité d'ajouter / modifier / supprimer quoi que ce soit).
    # On exempte donc tous les blueprints rattachés à l'URL /admin.
    for _name, _bp in list(app.blueprints.items()):
        _prefix = _bp.url_prefix or ""
        if _name == "admin" or _prefix.startswith("/admin"):
            try:
                csrf.exempt(_bp)
            except Exception as _e:
                print(f"[WARN] csrf.exempt({_name}) a échoué: {_e}")

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(comments_bp)
    app.register_blueprint(newsletter_bp)
    app.register_blueprint(seo_bp)
    from blueprints.polls import bp as polls_bp
    from blueprints.push import bp as push_bp
    app.register_blueprint(polls_bp)
    app.register_blueprint(push_bp)

    # Service worker servi à la racine pour avoir le scope "/".
    from flask import send_from_directory
    @app.route("/sw.js")
    def _sw():
        resp = send_from_directory(os.path.join(BASE, "static"), "sw.js",
                                   mimetype="application/javascript")
        resp.headers["Service-Worker-Allowed"] = "/"
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    # ----- Jinja helpers ----------------------------------------------------
    @app.template_filter("img")
    def _img(value):
        return value or PLACEHOLDER_IMG

    @app.template_filter("rfc822")
    def _rfc822(dt):
        return (dt or datetime.utcnow()).strftime("%a, %d %b %Y %H:%M:%S +0000")

    @app.context_processor
    def inject_globals():
        try:
            ticker = [b.message for b in BreakingNews.query.filter_by(active=True)
                      .order_by(BreakingNews.position).all()]
        except Exception:
            ticker = []
        try:
            cats = Category.query.order_by(Category.name).all()
        except Exception:
            cats = []
        _MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
                 "août", "septembre", "octobre", "novembre", "décembre"]
        _JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        now = datetime.now()
        today_label = f"{_JOURS[now.weekday()]} {now.day} {_MOIS[now.month - 1]} {now.year}"

        # Favoris de l'utilisateur connecté (set d'IDs pour test rapide)
        fav_ids = set()
        if current_user.is_authenticated:
            fav_ids = {f.article_id for f in current_user.favorites.all()}

        return dict(
            ticker=ticker,
            categories=cats,
            today_label=today_label,
            fav_ids=fav_ids,
            site_name=app.config["SITE_NAME"],
            site_tagline=app.config["SITE_TAGLINE"],
            current_year=now.year,
        )

    # ----- Public routes ----------------------------------------------------
    @app.route("/", endpoint="index")
    def home():
        items = (published_q()
                 .order_by(Article.published_at.desc().nullslast(),
                           Article.created_at.desc())
                 .limit(9).all())
        featured = items[0] if items else None
        sidebar = items[1:5]
        sections = []
        try:
            for c in Category.query.order_by(Category.name).all():
                arts = (published_q().filter(Article.category_id == c.id)
                        .order_by(Article.published_at.desc().nullslast(),
                                  Article.created_at.desc()).limit(4).all())
                if arts:
                    sections.append({"name": c.name, "slug": c.slug, "articles": arts})
                if len(sections) >= 4:
                    break
        except Exception:
            sections = []
        return render_template("index.html",
                               articles=items, featured=featured,
                               sidebar=sidebar, sections=sections)

    @app.route("/article/<slug>", endpoint="article_detail")
    def article(slug):
        a = Article.query.filter_by(slug=slug).first()
        if not a or not a.is_live():
            abort(404)
        # +1 vue
        try:
            a.views = (a.views or 0) + 1
            db.session.commit()
        except Exception:
            db.session.rollback()
        # Articles similaires : même catégorie + tags partagés, puis fallback récents
        related = compute_related(a, limit=4)
        approved_comments = (a.comments.filter_by(status="approved")
                             .order_by(Comment.created_at.desc()).all())
        # Sondage du jour
        from blueprints.polls import get_active_poll_for, has_voted
        poll = get_active_poll_for(a)
        poll_voted = has_voted(poll) if poll else False

        # JSON-LD NewsArticle
        ld = {
            "@context": "https://schema.org",
            "@type": "NewsArticle",
            "headline": a.title,
            "description": a.meta_description or a.excerpt or "",
            "image": [a.og_image or a.image or PLACEHOLDER_IMG],
            "datePublished": (a.published_at or a.created_at).isoformat(),
            "dateModified": (a.updated_at or a.created_at).isoformat(),
            "author": [{
                "@type": "Person",
                "name": (a.author_obj.name if a.author_obj else (a.author or "Rédaction")),
                "url": url_for("author_detail", slug=a.author_obj.slug, _external=True) if a.author_obj else None,
            }],
            "publisher": {
                "@type": "Organization",
                "name": app.config["SITE_NAME"],
                "logo": {
                    "@type": "ImageObject",
                    "url": url_for("static", filename="images/logo.png", _external=True),
                },
            },
            "mainEntityOfPage": {
                "@type": "WebPage",
                "@id": url_for("article_detail", slug=a.slug, _external=True),
            },
            "articleSection": a.category.name if a.category else None,
            "keywords": ", ".join(t.name for t in a.tags),
        }
        return render_template("article.html",
                               article=a, related=related,
                               comments=approved_comments,
                               poll=poll, poll_voted=poll_voted,
                               ld_json=json.dumps(ld, ensure_ascii=False))

    @app.route("/articles", endpoint="articles_list")
    def articles_list():
        cat_slug = request.args.get("category")
        tag_slug = request.args.get("tag")
        author = (request.args.get("author") or "").strip()
        query_text = (request.args.get("q") or "").strip()
        page = max(1, int(request.args.get("page", 1) or 1))
        per_page = 12

        current_category = None
        q = published_q()
        if cat_slug:
            current_category = Category.query.filter_by(slug=cat_slug).first()
            if current_category:
                q = q.filter(Article.category_id == current_category.id)
        if tag_slug:
            tag = Tag.query.filter_by(slug=tag_slug).first()
            if tag:
                q = q.filter(Article.tags.any(Tag.id == tag.id))
        if author:
            q = q.filter(Article.author == author)
        if query_text:
            like = f"%{query_text}%"
            q = q.filter(or_(
                Article.title.ilike(like),
                Article.excerpt.ilike(like),
                Article.content.ilike(like),
            ))

        total = q.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        items = (q.order_by(Article.published_at.desc().nullslast(),
                            Article.created_at.desc())
                 .offset((page - 1) * per_page).limit(per_page).all())

        available_categories = Category.query.order_by(Category.name).all()
        available_authors = [r[0] for r in db.session.query(Article.author)
                             .filter(Article.status == "published",
                                     Article.author.isnot(None))
                             .distinct().order_by(Article.author).all() if r[0]]
        return render_template("articles.html",
                               articles=items,
                               current_category=current_category,
                               available_categories=available_categories,
                               available_authors=available_authors,
                               current_author=author,
                               query_text=query_text,
                               page=page, total_pages=total_pages)

    @app.route("/tag/<slug>", endpoint="tag_detail")
    def tag_detail(slug):
        t = Tag.query.filter_by(slug=slug).first_or_404()
        page = max(1, int(request.args.get("page", 1) or 1))
        per_page = 12
        q = (published_q().filter(Article.tags.any(Tag.id == t.id))
             .order_by(Article.published_at.desc().nullslast(),
                       Article.created_at.desc()))
        total = q.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        items = q.offset((page - 1) * per_page).limit(per_page).all()
        return render_template("tag.html", tag=t, articles=items,
                               total=total, page=page, total_pages=total_pages)

    @app.route("/auteur/<slug>", endpoint="author_detail")
    def author_detail(slug):
        a = Author.query.filter_by(slug=slug).first_or_404()
        page = max(1, int(request.args.get("page", 1) or 1))
        per_page = 12
        q = (published_q().filter(Article.author_id == a.id)
             .order_by(Article.published_at.desc().nullslast(),
                       Article.created_at.desc()))
        total = q.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        items = q.offset((page - 1) * per_page).limit(per_page).all()
        return render_template("author.html", author=a, articles=items,
                               total=total, page=page, total_pages=total_pages)

    @app.errorhandler(404)
    def _404(e):
        return render_template("404.html"), 404

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

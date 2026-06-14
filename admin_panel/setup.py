"""Flask-Admin + Flask-Login + CKEditor wiring (v4).

Ajouts :
- Auteurs (Author)
- Tags
- Statut d'article (draft/scheduled/published) + published_at
- Modération des commentaires
- Abonnés newsletter
"""
import os
import uuid
import bleach
from werkzeug.utils import secure_filename
from flask import (Flask, redirect, url_for, request, flash, render_template)
from flask_admin import Admin, AdminIndexView, expose, helpers as admin_helpers
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField, FileUploadField
from flask_wtf import FlaskForm
from wtforms.validators import Optional as OptionalValidator
from flask_login import (LoginManager, login_user, logout_user,
                         current_user, login_required)
from flask_ckeditor import CKEditor, CKEditorField
from wtforms import PasswordField
from wtforms.validators import ValidationError, DataRequired, Length

from models import (db, User, Author, Category, Tag, Article, Media, Pdf,
                    BreakingNews, Comment, Subscriber, Poll, PollOption,
                    PushSubscription, slugify, STATUS_CHOICES)
from extensions import limiter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def upload_path(*parts):
    """Chemin absolu vers static/uploads, indépendant du dossier de lancement."""
    return os.path.join(BASE_DIR, "static", "uploads", *parts)


def unique_upload_name(obj, file_data):
    """Nom de fichier propre et unique pour éviter les collisions/espaces/accents."""
    original = secure_filename(file_data.filename or "")
    stem, ext = os.path.splitext(original)
    stem = slugify(stem or "upload")[:80] or "upload"
    return f"{stem}-{uuid.uuid4().hex[:12]}{ext.lower()}"


# ---------------------------------------------------------------------------
# Bleach allow-list pour le HTML CKEditor (articles)
# ---------------------------------------------------------------------------
CK_ALLOWED_TAGS = [
    "p", "br", "hr", "h2", "h3", "h4", "h5", "h6",
    "strong", "b", "em", "i", "u", "s", "sub", "sup",
    "blockquote", "code", "pre",
    "ul", "ol", "li",
    "a", "img", "figure", "figcaption",
    "table", "thead", "tbody", "tr", "th", "td",
    "span", "div",
]
CK_ALLOWED_ATTRS = {
    "*": ["class", "id", "style"],
    "a": ["href", "title", "rel", "target"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
}
CK_ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


def sanitize_ck_html(raw: str) -> str:
    """Assainit le HTML produit par CKEditor avant stockage."""
    if not raw:
        return raw
    return bleach.clean(
        raw,
        tags=CK_ALLOWED_TAGS,
        attributes=CK_ALLOWED_ATTRS,
        protocols=CK_ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True,
    )


# ---------------------------------------------------------------------------
# Validation "magic bytes" des uploads
# ---------------------------------------------------------------------------
# Signatures binaires courantes (premiers octets) par type de fichier
_FILE_SIGNATURES = {
    "jpg":  [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png":  [b"\x89PNG\r\n\x1a\n"],
    "gif":  [b"GIF87a", b"GIF89a"],
    "webp": [b"RIFF"],  # complément vérifié plus bas
    "pdf":  [b"%PDF-"],
    "mp4":  [b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x20ftyp"],
    "webm": [b"\x1aE\xdf\xa3"],
    "mov":  [b"\x00\x00\x00\x14ftyp", b"\x00\x00\x00\x20ftypqt"],
}


def _read_head(file_storage, n=32):
    stream = getattr(file_storage, "stream", file_storage)
    try:
        stream.seek(0)
        head = stream.read(n)
    finally:
        try:
            stream.seek(0)
        except Exception:
            pass
    return head or b""


def validate_magic_bytes(form, field):
    """Vérifie que le contenu réel correspond bien à l'extension annoncée."""
    data = getattr(field, "data", None)
    if not data or not getattr(data, "filename", ""):
        return  # champ vide => OK
    ext = data.filename.rsplit(".", 1)[-1].lower() if "." in data.filename else ""
    if not ext:
        raise ValidationError("Fichier sans extension refusé.")
    head = _read_head(data, 32)

    # WebP : "RIFF....WEBP"
    if ext == "webp":
        if not (head[:4] == b"RIFF" and head[8:12] == b"WEBP"):
            raise ValidationError("Le fichier n'est pas un WebP valide.")
        return

    # Images : vérification par signature magique (imghdr est supprimé en Py 3.13)
    if ext in ("jpg", "jpeg"):
        # Tous les JPEG commencent par FF D8 FF (suivi de E0/E1/E2/DB/EE...)
        if not (len(head) >= 3 and head[0] == 0xFF and head[1] == 0xD8 and head[2] == 0xFF):
            raise ValidationError("Le contenu ne correspond pas à un fichier JPG.")
        return
    if ext == "png":
        if not head.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValidationError("Le contenu ne correspond pas à un fichier PNG.")
        return
    if ext == "gif":
        if not (head.startswith(b"GIF87a") or head.startswith(b"GIF89a")):
            raise ValidationError("Le contenu ne correspond pas à un fichier GIF.")
        return

    sigs = _FILE_SIGNATURES.get(ext)
    if not sigs:
        raise ValidationError(f"Type de fichier non autorisé : .{ext}")
    if not any(head.startswith(sig) for sig in sigs):
        raise ValidationError(
            f"Signature binaire invalide pour .{ext} (fichier corrompu ou usurpé)."
        )


login_manager = LoginManager()
login_manager.login_view = "auth.login"
ckeditor = CKEditor()


@login_manager.user_loader
def load_user(uid):
    return User.query.get(int(uid))


# ----- Secured views --------------------------------------------------------

class SecureMixin:
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, "is_admin", False)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("admin.login", next=request.url))


class AdminCsrfForm(FlaskForm):
    """FlaskForm + compatibilité Flask-Admin.

    Flask-Admin attend ``form._obj`` (défini par son BaseForm) pour que le
    validateur Unique exclue la ligne en cours d'édition. Sans ça, toute
    édition échoue avec "Already exists." sur les champs uniques.
    """
    def __init__(self, formdata=None, obj=None, prefix="", **kwargs):
        self._obj = obj
        super().__init__(formdata=formdata, obj=obj, prefix=prefix, **kwargs)


class SecureModelView(SecureMixin, ModelView):
    # Utilise FlaskForm (Flask-WTF) plutôt que SecureForm de Flask-Admin :
    # SecureForm + WTForms 3.x présente un bug où le csrf_token est marqué
    # "missing" même quand le token est correctement transmis. FlaskForm
    # s'intègre proprement avec CSRFProtect global tout en générant son
    # propre champ csrf_token (les blueprints admin sont exemptés du
    # before_request CSRF check, c'est donc le form qui valide).
    form_base_class = AdminCsrfForm
    page_size = 25
    can_export = True

    # Rendre "slug" optionnel partout : on_model_change le génère depuis
    # le name/title si laissé vide. Sans ça, le NOT NULL en base déclenche
    # "This field is required." et bloque toute création.
    form_args = {
        "slug": {"validators": [OptionalValidator()]},
    }


# ----- Articles -------------------------------------------------------------

class ArticleView(SecureModelView):
    form_overrides = {
        "content": CKEditorField,
    }
    form_choices = {
        "status": [(s, s.capitalize()) for s in STATUS_CHOICES],
    }
    form_extra_fields = {
        "cover_upload": ImageUploadField(
            "Cover (upload)",
            base_path=upload_path("images"),
            url_relative_path="uploads/images/",
            namegen=unique_upload_name,
            allowed_extensions=("jpg", "jpeg", "png", "webp", "gif"),
            validators=[validate_magic_bytes],
        ),
    }
    column_list = ("title", "category", "author_obj", "status",
                   "published_at", "views", "updated_at")
    column_searchable_list = ("title", "excerpt", "author")
    column_filters = ("status", "published", "category", "author_obj", "tags")
    column_editable_list = ("status",)
    form_columns = (
        "title", "slug", "category", "tags",
        "excerpt", "content",
        "cover_upload", "image", "image_caption", "image_credit",
        "author_obj", "author", "author_role", "read_time", "date_label",
        "meta_description", "og_image",
        "status", "published_at", "published",
    )
    create_template = "admin_ck/edit.html"
    edit_template = "admin_ck/edit.html"

    def on_model_change(self, form, model, is_created):
        from datetime import datetime
        if not model.slug and model.title:
            model.slug = slugify(model.title)
        # Assainissement du HTML CKEditor avant stockage (anti-XSS)
        if model.content:
            model.content = sanitize_ck_html(model.content)
        up = getattr(form, "cover_upload", None)
        if up and up.data and hasattr(up.data, "filename") and up.data.filename:
            model.image = f"/static/uploads/images/{up.data.filename}"
        # Réconcilie status <-> published : si l'un OU l'autre indique publié,
        # on aligne les deux. Évite l'article fantôme (case cochée mais
        # status resté à "draft" et inversement).
        if model.status == "published" or model.published:
            model.status = "published"
            model.published = True
            if not model.published_at:
                model.published_at = datetime.utcnow()
        else:
            model.published = False
        # Auteur libre auto-rempli si auteur lié
        if model.author_obj and not model.author:
            model.author = model.author_obj.name
            if not model.author_role and model.author_obj.role:
                model.author_role = model.author_obj.role


class AuthorView(SecureModelView):
    column_list = ("name", "slug", "role", "email")
    form_columns = ("name", "slug", "role", "bio", "photo_upload",
                    "photo", "twitter", "linkedin", "email")
    form_extra_fields = {
        "photo_upload": ImageUploadField(
            "Photo (upload)",
            base_path=upload_path("authors"),
            url_relative_path="uploads/authors/",
            namegen=unique_upload_name,
            allowed_extensions=("jpg", "jpeg", "png", "webp"),
            validators=[validate_magic_bytes],
        ),
    }

    def on_model_change(self, form, model, is_created):
        if not model.slug and model.name:
            model.slug = slugify(model.name)
        up = getattr(form, "photo_upload", None)
        if up and up.data and hasattr(up.data, "filename") and up.data.filename:
            model.photo = f"/static/uploads/authors/{up.data.filename}"


class CategoryView(SecureModelView):
    column_list = ("name", "slug", "color")
    form_columns = ("name", "slug", "color", "description")

    def on_model_change(self, form, model, is_created):
        if not model.slug and model.name:
            model.slug = slugify(model.name)


class TagView(SecureModelView):
    column_list = ("name", "slug")
    form_columns = ("name", "slug")

    def on_model_change(self, form, model, is_created):
        if not model.slug and model.name:
            model.slug = slugify(model.name)


class MediaView(SecureModelView):
    column_list = ("article", "kind", "url", "caption", "position")
    form_columns = ("article", "kind", "media_upload", "url", "caption", "position")
    column_filters = ("kind", "article")
    form_extra_fields = {
        "media_upload": FileUploadField(
            "Fichier (image ou vidéo, optionnel)",
            base_path=upload_path("media"),
            namegen=unique_upload_name,
            allowed_extensions=("jpg", "jpeg", "png", "webp", "gif",
                                "mp4", "webm", "mov"),
            validators=[validate_magic_bytes],
        ),
    }

    def on_model_change(self, form, model, is_created):
        up = getattr(form, "media_upload", None)
        if up and up.data and hasattr(up.data, "filename") and up.data.filename:
            model.url = f"/static/uploads/media/{up.data.filename}"
            ext = up.data.filename.rsplit(".", 1)[-1].lower()
            model.kind = "video" if ext in ("mp4", "webm", "mov") else "image"
        elif model.url and any(d in model.url for d in
                               ("youtube.com", "youtu.be", "vimeo.com")):
            model.kind = "embed"


class PdfView(SecureModelView):
    column_list = ("article", "title", "url")
    form_columns = ("article", "title", "pdf_upload", "url")
    form_extra_fields = {
        "pdf_upload": FileUploadField(
            "PDF (upload)",
            base_path=upload_path("pdfs"),
            namegen=unique_upload_name,
            allowed_extensions=("pdf",),
            validators=[validate_magic_bytes],
        ),
    }

    def on_model_change(self, form, model, is_created):
        up = getattr(form, "pdf_upload", None)
        if up and up.data and hasattr(up.data, "filename") and up.data.filename:
            model.url = f"/static/uploads/pdfs/{up.data.filename}"


class BreakingNewsView(SecureModelView):
    column_list = ("message", "active", "position", "created_at")
    column_editable_list = ("active", "position")
    form_columns = ("message", "active", "position")


class CommentView(SecureModelView):
    """Modération des commentaires."""
    column_list = ("article", "author_name", "author_email",
                   "status", "created_at", "ip")
    column_searchable_list = ("author_name", "author_email", "content")
    column_filters = ("status", "article")
    column_editable_list = ("status",)
    form_columns = ("article", "user", "author_name", "author_email",
                    "content", "status")
    form_choices = {
        "status": [(s, s.capitalize()) for s in
                   ("pending", "approved", "rejected", "spam")],
    }

    @expose("/approve/<int:cid>")
    def approve(self, cid):
        c = Comment.query.get_or_404(cid)
        c.status = "approved"
        db.session.commit()
        flash("Commentaire approuvé.", "success")
        return redirect(request.referrer or url_for(".index_view"))

    @expose("/reject/<int:cid>")
    def reject(self, cid):
        c = Comment.query.get_or_404(cid)
        c.status = "rejected"
        db.session.commit()
        flash("Commentaire rejeté.", "success")
        return redirect(request.referrer or url_for(".index_view"))


class SubscriberView(SecureModelView):
    column_list = ("email", "confirmed", "created_at", "confirmed_at")
    column_filters = ("confirmed",)
    column_searchable_list = ("email",)
    can_create = False
    form_columns = ("email", "confirmed")


class PollOptionInlineView(ModelView):
    form_columns = ("label", "position", "votes")


class PollView(SecureModelView):
    column_list = ("question", "active", "total_votes", "created_at")
    column_filters = ("active",)
    form_columns = ("question", "active")
    inline_models = [(PollOption, dict(form_columns=("id", "label", "position", "votes")))]


class PollOptionView(SecureModelView):
    column_list = ("poll", "label", "votes", "position")
    form_columns = ("poll", "label", "votes", "position")


class PushSubscriptionView(SecureModelView):
    column_list = ("topic", "user_id", "endpoint", "created_at")
    column_filters = ("topic",)
    can_create = False
    can_edit = False


class UserView(SecureModelView):
    column_list = ("username", "email", "is_admin", "is_active_flag", "created_at")
    column_filters = ("is_admin", "is_active_flag")
    form_columns = ("username", "email", "is_admin", "is_active_flag", "new_password")
    form_extra_fields = {
        # À la création : mot de passe OBLIGATOIRE (min 8 caractères).
        # À l'édition : champ facultatif (laisser vide = ne pas changer).
        "new_password": PasswordField(
            "Mot de passe",
            validators=[Length(min=0, max=128)],
            description="Min. 8 caractères. Obligatoire à la création.",
        ),
    }

    def on_model_change(self, form, model, is_created):
        pw = (form.new_password.data or "").strip()
        if is_created:
            # Création : on EXIGE un mot de passe choisi par l'admin.
            # Plus aucun mot de passe par défaut ("changeme") n'est défini.
            if len(pw) < 8:
                raise ValidationError(
                    "Un mot de passe d'au moins 8 caractères est obligatoire "
                    "à la création d'un utilisateur."
                )
            model.set_password(pw)
        else:
            # Édition : ne rien faire si le champ est vide.
            if pw:
                if len(pw) < 8:
                    raise ValidationError(
                        "Le nouveau mot de passe doit faire au moins 8 caractères."
                    )
                model.set_password(pw)


# ----- Custom AdminIndex with /login route ---------------------------------

class MyAdminIndex(AdminIndexView):
    @expose("/")
    def index(self):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            return redirect(url_for(".login"))
        # Mini-dashboard
        stats = {
            "articles": Article.query.count(),
            "published": Article.query.filter_by(status="published").count(),
            "drafts": Article.query.filter_by(status="draft").count(),
            "scheduled": Article.query.filter_by(status="scheduled").count(),
            "pending_comments": Comment.query.filter_by(status="pending").count(),
            "subscribers": Subscriber.query.filter_by(confirmed=True).count(),
            "users": User.query.count(),
        }
        return self.render("admin_ck/dashboard.html", stats=stats)

    @expose("/login", methods=("GET", "POST"))
    @limiter.limit("10 per minute; 50 per hour", methods=["POST"])
    def login(self):
        if request.method == "POST":
            u = request.form.get("username", "").strip()
            p = request.form.get("password", "")
            user = User.query.filter_by(username=u).first()
            if user and user.check_password(p) and user.is_admin:
                login_user(user)
                return redirect(url_for(".index"))
            flash("Identifiants invalides", "error")
        return render_template("admin_ck/login.html")

    @expose("/logout")
    def logout(self):
        logout_user()
        return redirect(url_for(".login"))


def init_admin(app: Flask) -> Admin:
    ckeditor.init_app(app)
    login_manager.init_app(app)

    admin = Admin(
        app,
        name="Global Chronicle — Back-office",
        index_view=MyAdminIndex(url="/admin"),
    )
    admin.add_view(ArticleView(Article, db.session, name="Articles", category="Contenu"))
    admin.add_view(CategoryView(Category, db.session, name="Catégories", category="Contenu"))
    admin.add_view(TagView(Tag, db.session, name="Tags", category="Contenu"))
    admin.add_view(AuthorView(Author, db.session, name="Auteurs", category="Contenu"))
    admin.add_view(MediaView(Media, db.session, name="Médias", category="Contenu"))
    admin.add_view(PdfView(Pdf, db.session, name="PDFs", category="Contenu"))
    admin.add_view(CommentView(Comment, db.session, name="Commentaires", category="Modération"))
    admin.add_view(BreakingNewsView(BreakingNews, db.session, name="Bandeau urgent", category="Modération"))
    admin.add_view(SubscriberView(Subscriber, db.session, name="Abonnés newsletter", category="Système"))
    admin.add_view(UserView(User, db.session, name="Utilisateurs", category="Système"))
    admin.add_view(PollView(Poll, db.session, name="Sondages", category="Interaction"))
    admin.add_view(PushSubscriptionView(PushSubscription, db.session,
                                        name="Abonnés push", category="Interaction"))

    @app.context_processor
    def inject_admin_ctx():
        return dict(admin_helpers=admin_helpers)

    return admin

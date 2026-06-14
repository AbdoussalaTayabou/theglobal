"""SQLAlchemy models for The Global Chronicle (v4).

Ajouts:
- Tags (many-to-many)
- Auteurs (table dédiée Author + champ author_obj sur Article)
- Statuts d'article (draft / scheduled / published) + published_at
- Commentaires modérés
- Abonnés newsletter (double opt-in)
- Favoris (utilisateurs <-> articles)
"""
import secrets as _secrets
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

try:
    from slugify import slugify as _slugify
except Exception:
    _slugify = None


db = SQLAlchemy()


def slugify(text: str) -> str:
    if _slugify:
        try:
            return _slugify(text)
        except Exception:
            pass
    import re
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "article"


def _token() -> str:
    return _secrets.token_urlsafe(32)


# ----- Association tables ---------------------------------------------------

article_tags = db.Table(
    "article_tags",
    db.Column("article_id", db.Integer, db.ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# ----- Users (admin + lecteurs) --------------------------------------------

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active_flag = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    favorites = db.relationship("Favorite", back_populates="user",
                                cascade="all, delete-orphan", lazy="dynamic")
    comments = db.relationship("Comment", back_populates="user", lazy="dynamic")

    def set_password(self, pw): self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)

    @property
    def is_active(self):  # Flask-Login
        return bool(self.is_active_flag)

    def __str__(self):
        return self.username


# ----- Author ---------------------------------------------------------------

class Author(db.Model):
    __tablename__ = "authors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False)
    role = db.Column(db.String(160), default="Journaliste")
    bio = db.Column(db.Text, default="")
    photo = db.Column(db.String(500), default="")
    twitter = db.Column(db.String(120), default="")
    linkedin = db.Column(db.String(200), default="")
    email = db.Column(db.String(200), default="")

    articles = db.relationship("Article", back_populates="author_obj", lazy="dynamic")

    def __str__(self):
        return self.name


# ----- Category / Tag -------------------------------------------------------

class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    color = db.Column(db.String(20), default="#1a2238")
    description = db.Column(db.String(255), default="")

    articles = db.relationship("Article", back_populates="category", lazy="dynamic")

    def __str__(self):
        return self.name


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)

    articles = db.relationship("Article", secondary=article_tags, back_populates="tags")

    def __str__(self):
        return self.name


# ----- Article --------------------------------------------------------------

STATUS_CHOICES = ("draft", "scheduled", "published", "archived")


class Article(db.Model):
    __tablename__ = "articles"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    excerpt = db.Column(db.Text)
    content = db.Column(db.Text)  # HTML CKEditor

    image = db.Column(db.String(500))      # cover
    image_caption = db.Column(db.String(255), default="")
    image_credit = db.Column(db.String(160), default="")

    # Auteur: champ libre (rétro-compat) + relation optionnelle
    author = db.Column(db.String(120), default="Rédaction")
    author_role = db.Column(db.String(120), default="")
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=True)
    author_obj = db.relationship("Author", back_populates="articles")

    read_time = db.Column(db.String(20), default="5 min")
    date_label = db.Column(db.String(80), default="")

    # SEO
    meta_description = db.Column(db.String(255), default="")
    og_image = db.Column(db.String(500), default="")

    # Workflow
    status = db.Column(db.String(20), default="draft", index=True)  # draft|scheduled|published|archived
    published = db.Column(db.Boolean, default=False, index=True)    # gardé pour compat
    published_at = db.Column(db.DateTime, default=None, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Métriques simples
    views = db.Column(db.Integer, default=0)

    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"))
    category = db.relationship("Category", back_populates="articles")

    tags = db.relationship("Tag", secondary=article_tags, back_populates="articles")

    media = db.relationship("Media", back_populates="article",
                            cascade="all, delete-orphan", lazy="select")
    pdfs = db.relationship("Pdf", back_populates="article",
                           cascade="all, delete-orphan", lazy="select")
    comments = db.relationship("Comment", back_populates="article",
                               cascade="all, delete-orphan", lazy="dynamic")

    def is_live(self, now=None):
        """Visible publiquement ?"""
        now = now or datetime.utcnow()
        if self.status == "published" or self.published:
            return self.published_at is None or self.published_at <= now
        return False

    def __str__(self):
        return self.title


class Media(db.Model):
    __tablename__ = "article_media"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    kind = db.Column(db.String(20), default="image")  # image | video | embed
    url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(255), default="")
    position = db.Column(db.Integer, default=0)
    article = db.relationship("Article", back_populates="media")


class Pdf(db.Model):
    __tablename__ = "article_pdfs"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False)
    title = db.Column(db.String(200), default="Document PDF")
    url = db.Column(db.String(500), nullable=False)
    article = db.relationship("Article", back_populates="pdfs")


class BreakingNews(db.Model):
    __tablename__ = "breaking_news"
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    active = db.Column(db.Boolean, default=True)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __str__(self):
        return self.message[:60]


# ----- Comments -------------------------------------------------------------

COMMENT_STATUS = ("pending", "approved", "rejected", "spam")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    author_name = db.Column(db.String(120), nullable=False)
    author_email = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="pending", index=True)
    ip = db.Column(db.String(45), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    article = db.relationship("Article", back_populates="comments")
    user = db.relationship("User", back_populates="comments")

    def __str__(self):
        return f"{self.author_name}: {self.content[:40]}"


# ----- Favorites ------------------------------------------------------------

class Favorite(db.Model):
    __tablename__ = "favorites"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    article_id = db.Column(db.Integer, db.ForeignKey("articles.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="favorites")
    article = db.relationship("Article")

    __table_args__ = (
        db.UniqueConstraint("user_id", "article_id", name="uq_user_article_fav"),
    )


# ----- Newsletter subscribers ----------------------------------------------

class Subscriber(db.Model):
    __tablename__ = "subscribers"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    confirmed = db.Column(db.Boolean, default=False, index=True)
    confirm_token = db.Column(db.String(80), default=_token, unique=True)
    unsubscribe_token = db.Column(db.String(80), default=_token, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    def __str__(self):
        return self.email


# ----- Poll (Sondage du jour) ----------------------------------------------

class Poll(db.Model):
    __tablename__ = "polls"
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    options = db.relationship("PollOption", back_populates="poll",
                              cascade="all, delete-orphan",
                              order_by="PollOption.position")

    @property
    def total_votes(self):
        return sum(o.votes or 0 for o in self.options)

    def __str__(self):
        return self.question


class PollOption(db.Model):
    __tablename__ = "poll_options"
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    label = db.Column(db.String(160), nullable=False)
    votes = db.Column(db.Integer, default=0)
    position = db.Column(db.Integer, default=0)

    poll = db.relationship("Poll", back_populates="options")

    def __str__(self):
        return self.label


class PollVote(db.Model):
    """Trace anti-double-vote (clé = user_id ou hash IP+UA)."""
    __tablename__ = "poll_votes"
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id", ondelete="CASCADE"),
                          nullable=False)
    voter_key = db.Column(db.String(120), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("poll_id", "voter_key", name="uq_poll_voter"),
    )


# ----- Push notifications subscriptions ------------------------------------

class PushSubscription(db.Model):
    __tablename__ = "push_subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    topic = db.Column(db.String(80), default="all", index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __str__(self):
        return f"{self.topic}:{self.endpoint[:40]}"


# ----- Init / Seed ----------------------------------------------------------

def init_db():
    db.create_all()
    seed_if_empty()


def seed_if_empty():
    from sqlalchemy import inspect
    # Admin par défaut
    if not User.query.filter_by(is_admin=True).first():
        u = User(username="admin", email="admin@example.com", is_admin=True)
        u.set_password("admin123")
        db.session.add(u)

    if not Category.query.first():
        defaults = [
            ("Politique", "#1a2238"),
            ("Économie", "#0c6e4d"),
            ("Climat", "#2f7a3a"),
            ("Tech", "#1f4e8c"),
            ("International", "#7a1f2b"),
            ("Culture", "#7a5a1f"),
        ]
        for name, color in defaults:
            db.session.add(Category(name=name, slug=slugify(name), color=color))

    if not Tag.query.first():
        for t in ("Analyse", "Reportage", "Enquête", "Tribune", "Interview"):
            db.session.add(Tag(name=t, slug=slugify(t)))

    if not Poll.query.first():
        p = Poll(question="Quel sujet doit-on couvrir cette semaine ?", active=True)
        db.session.add(p)
        db.session.flush()
        for i, label in enumerate(["Climat", "Économie", "Géopolitique", "Tech & IA"]):
            db.session.add(PollOption(poll_id=p.id, label=label, position=i))

    db.session.commit()

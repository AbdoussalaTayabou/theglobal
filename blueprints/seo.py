"""SEO: sitemap.xml, robots.txt, et flux RSS."""
from datetime import datetime
from flask import Blueprint, Response, url_for, request, abort
from xml.sax.saxutils import escape

from models import db, Article, Category, Author, Tag

bp = Blueprint("seo", __name__)


def _published_q():
    now = datetime.utcnow()
    return Article.query.filter(
        Article.status == "published",
        db.or_(Article.published_at.is_(None), Article.published_at <= now),
    )


# ---------- sitemap.xml -----------------------------------------------------

@bp.route("/sitemap.xml")
def sitemap():
    urls = [
        (url_for("index", _external=True), datetime.utcnow(), "daily", "1.0"),
        (url_for("articles_list", _external=True), datetime.utcnow(), "daily", "0.9"),
    ]
    for c in Category.query.all():
        urls.append((url_for("articles_list", category=c.slug, _external=True),
                     datetime.utcnow(), "daily", "0.8"))
    for t in Tag.query.all():
        urls.append((url_for("tag_detail", slug=t.slug, _external=True),
                     datetime.utcnow(), "weekly", "0.6"))
    for a in Author.query.all():
        urls.append((url_for("author_detail", slug=a.slug, _external=True),
                     datetime.utcnow(), "weekly", "0.6"))
    for a in _published_q().order_by(Article.updated_at.desc()).limit(5000).all():
        urls.append((url_for("article_detail", slug=a.slug, _external=True),
                     a.updated_at or a.created_at, "weekly", "0.7"))

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, lastmod, cf, prio in urls:
        parts.append(
            f"  <url><loc>{escape(loc)}</loc>"
            f"<lastmod>{lastmod.strftime('%Y-%m-%d')}</lastmod>"
            f"<changefreq>{cf}</changefreq><priority>{prio}</priority></url>"
        )
    parts.append("</urlset>")
    return Response("\n".join(parts), mimetype="application/xml")


# ---------- robots.txt ------------------------------------------------------

@bp.route("/robots.txt")
def robots():
    sm = url_for("seo.sitemap", _external=True)
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /auth\n"
        "Disallow: /compte\n"
        f"Sitemap: {sm}\n"
    )
    return Response(body, mimetype="text/plain")


# ---------- RSS -------------------------------------------------------------

def _rss(items, title, link, description):
    def _item(a):
        url = url_for("article_detail", slug=a.slug, _external=True)
        pub = (a.published_at or a.created_at or datetime.utcnow())
        return (
            "    <item>\n"
            f"      <title>{escape(a.title)}</title>\n"
            f"      <link>{escape(url)}</link>\n"
            f"      <guid isPermaLink=\"true\">{escape(url)}</guid>\n"
            f"      <pubDate>{pub.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>\n"
            f"      <description>{escape(a.excerpt or '')}</description>\n"
            f"      {('<category>' + escape(a.category.name) + '</category>') if a.category else ''}\n"
            "    </item>"
        )
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"  <title>{escape(title)}</title>",
        f"  <link>{escape(link)}</link>",
        f"  <description>{escape(description)}</description>",
        f"  <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</lastBuildDate>",
        "  <language>fr-FR</language>",
    ]
    xml += [_item(a) for a in items]
    xml.append("</channel></rss>")
    return Response("\n".join(xml), mimetype="application/rss+xml")


@bp.route("/rss.xml")
def rss():
    items = _published_q().order_by(Article.published_at.desc().nullslast(),
                                    Article.created_at.desc()).limit(50).all()
    return _rss(items,
                "The Global Chronicle — Tous les articles",
                url_for("index", _external=True),
                "Journalisme indépendant et actualité internationale.")


@bp.route("/rss/<slug>.xml")
def rss_category(slug):
    c = Category.query.filter_by(slug=slug).first_or_404()
    items = (_published_q().filter(Article.category_id == c.id)
             .order_by(Article.published_at.desc().nullslast(),
                       Article.created_at.desc()).limit(50).all())
    return _rss(items,
                f"The Global Chronicle — {c.name}",
                url_for("articles_list", category=c.slug, _external=True),
                f"Actualité {c.name}.")

"""Shared Flask extensions (limiter, talisman, migrate) initialisés dans app.py."""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from flask_migrate import Migrate

# Limiter global (clé = IP client, ProxyFix géré dans app.py).
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri="memory://",
    strategy="fixed-window",
)

# Talisman = headers de sécurité (CSP, HSTS, X-Frame-Options, etc.)
talisman = Talisman()

# Flask-Migrate (Alembic) : remplace migrate.py maison.
# Usage :
#   flask db init        # 1ère fois seulement (crée le dossier migrations/)
#   flask db migrate -m "msg"
#   flask db upgrade
migrate = Migrate()

<p align="center">
  <img src="static/images/logo.png" alt="The Global Chronicle logo" width="180">
</p>

<h1 align="center">The Global Chronicle</h1>
<p align="center"><em>The Voice of Global Press</em></p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Flask-3.0+-000000?logo=flask&logoColor=white" alt="Flask"></a>
  <a href="#"><img src="https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"></a>
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python"></a>
  <a href="#"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
</p>

---

## Table des matières

- [Présentation](#présentation)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Lancement](#lancement)
- [Back-office administrateur](#back-office-administrateur)
- [Déploiement](#déploiement)
- [Scripts utiles](#scripts-utiles)
- [Licence](#licence)

---

## Présentation

**The Global Chronicle** est une plateforme de presse en ligne complète construite avec **Flask** (Python). Elle propose un site public moderne avec un back-office d'administration sécurisé basé sur **Flask-Admin** et un éditeur **CKEditor** pour la rédaction d'articles.

Le projet intègre un écosystème complet autour de la publication de contenu : gestion d'articles, catégories, tags, auteurs, médias et PDF ; système de commentaires modérés ; newsletter avec double opt-in ; sondages ; notifications push web ; SEO avancé (JSON-LD, meta tags, sitemap, RSS) ; et gestion des comptes utilisateurs avec favoris.

---

## Fonctionnalités

### Côté public

| Fonctionnalité | Description |
|----------------|-------------|
| **Page d'accueil** | Mise en avant du dernier article, sidebar, sections par catégorie, fil d'actualité en temps réel (breaking news) |
| **Liste des articles** | Grille paginée avec **barre de recherche** et filtres par **catégorie**, **tag** et **auteur** |
| **Page article** | Affichage riche avec contenu HTML (CKEditor), articles similaires (score catégorie + tags), commentaires approuvés, sondage du jour |
| **Fiches auteur** | Profil public de chaque auteur avec ses articles |
| **Tags** | Navigation par mots-clés |
| **Comptes utilisateurs** | Inscription, connexion, tableau de bord personnel, articles favoris |
| **Commentaires** | Ajout de commentaires avec modération préalable |
| **Newsletter** | Inscription avec confirmation par e-mail (double opt-in), désinscription |
| **SEO** | Balises Open Graph, Twitter Cards, JSON-LD `NewsArticle`, sitemap XML, flux RSS |
| **PWA** | Service Worker pour une expérience proche des applications mobiles |
| **Sécurité** | CSRF, rate limiting, headers de sécurité (CSP configurable), cookies sécurisés en production |

### Côté administration

| Fonctionnalité | Description |
|----------------|-------------|
| **Flask-Admin** | Interface d'administration complète accessible sur `/admin` |
| **CKEditor** | Éditeur WYSIWYG intégré pour la rédaction des articles |
| **Uploads** | Gestion des images d'articles, médias et PDFs directement depuis l'admin |
| **Articles** | Création, édition, suppression ; gestion du statut (brouillon / publié) et du scheduling |
| **Catégories & Tags** | Taxonomie complète du contenu |
| **Auteurs** | Profils d'auteurs avec photo et biographie |
| **Breaking News** | Gestion du bandeau d'actualité en temps réel |
| **Commentaires** | Modération (approuver / rejeter / supprimer) |
| **Sondages** | Création et gestion des sondages du jour |
| **Flask-Migrate** | Migrations de base de données avec Alembic |

---

## Architecture

```
the-global-chronicle/
├── app.py                 # Point d'entrée principal (application factory)
├── wsgi.py                # Point d'entrée WSGI (production)
├── extensions.py          # Initialisation des extensions Flask
├── requirements.txt       # Dépendances Python
├── .env.example           # Modèle de variables d'environnement
│
├── admin_panel/           # Configuration Flask-Admin
│   ├── __init__.py
│   └── setup.py           # Vues sécurisées, CKEditor, uploads
│
├── blueprints/            # Modules fonctionnels (routes Flask)
│   ├── auth.py            # Authentification & compte utilisateur
│   ├── comments.py        # Commentaires modérés
│   ├── legal.py           # Pages légales (CGU, mentions, contact)
│   ├── newsletter.py      # Newsletter double opt-in
│   ├── polls.py           # Sondages
│   ├── push.py            # Notifications push web
│   └── seo.py             # Sitemap XML & flux RSS
│
├── models/                # Modèles SQLAlchemy
│   ├── __init__.py
│   └── db.py              # User, Article, Category, Tag, Author, Comment, etc.
│
├── migrations/            # Migrations Alembic (Flask-Migrate)
│
├── static/                # Assets statiques (CSS, JS, images, uploads)
│   ├── css/styles.css     # Feuille de style principale
│   ├── js/                # Scripts front (cookies, partage, push)
│   ├── images/            # Images du site (logo, hero, etc.)
│   └── uploads/           # Fichiers uploadés (images, médias, PDFs)
│
└── templates/             # Templates Jinja2
    ├── base.html          # Layout principal
    ├── index.html         # Page d'accueil
    ├── articles.html      # Liste des articles (recherche + filtres)
    ├── article.html       # Page article détaillée
    ├── author.html        # Profil auteur
    ├── tag.html           # Page tag
    ├── auth/              # Templates d'authentification
    ├── account/           # Tableau de bord utilisateur
    ├── admin_ck/          # Templates custom de l'admin CKEditor
    ├── legal/             # Pages légales
    ├── newsletter/        # Confirmation newsletter
    └── _footer.html, _poll.html  # Partials
```

---

## Prérequis

- **Python** >= 3.11
- **pip** (ou **uv**, **poetry**)
- Pour la production : **PostgreSQL** >= 13 (recommandé)
- Pour le développement : SQLite (inclus, aucune installation requise)

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/<utilisateur>/the-global-chronicle.git
cd the-global-chronicle
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
```

Activer l'environnement :

- **Linux / macOS** :
  ```bash
  source venv/bin/activate
  ```
- **Windows** :
  ```bash
  venv\Scripts\activate
  ```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

---

## Configuration

Copiez le fichier d'exemple et adaptez-le :

```bash
cp .env.example .env
```

### Variables minimales pour le développement

```env
SECRET_KEY=une-cle-super-secrete-en-hex
FLASK_ENV=development
FLASK_APP=app:create_app
DATABASE_URL=
```

> **Note** : Laissez `DATABASE_URL` vide en développement pour utiliser SQLite automatiquement (`chronicle.db`).

### Générer une clé secrète

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copiez la valeur générée dans `SECRET_KEY`.

### Pour la production (PostgreSQL)

```env
SECRET_KEY=votre-cle-hex-de-64-caracteres
FLASK_ENV=production
FLASK_APP=app:create_app
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/chronicle
```

> **Important** : En production, `SECRET_KEY` et `DATABASE_URL` sont **obligatoires**. L'application refusera de démarrer s'ils sont manquants.

---

## Lancement

### Mode développement

```bash
flask run
```

Le site sera accessible sur **http://127.0.0.1:5000/**.

Le serveur de développement Flask recharge automatiquement le code à chaque modification.

### Premiers pas

Au premier démarrage, la base de données et les tables sont créées automatiquement. Un compte administrateur par défaut est injecté :

| Champ | Valeur |
|-------|--------|
| **Nom d'utilisateur** | `admin` |
| **Mot de passe** | `admin123` |

> **⚠️ Sécurité** : Changez immédiatement ce mot de passe après le premier login en production.

### Charger les articles de démonstration

Le fichier `seed_articles.py` contient des articles de test. Pour les injecter :

```bash
python seed_articles.py
```

### Commandes Flask-Migrate (migrations)

Si vous modifiez les modèles, générez et appliquez une migration :

```bash
flask db migrate -m "description de la migration"
flask db upgrade
```

---

## Back-office administrateur

Accédez à l'administration sur **http://127.0.0.1:5000/admin**.

Identifiants par défaut :
- **Utilisateur** : `admin`
- **Mot de passe** : `admin123`

Depuis l'admin vous pouvez :
- Rédiger et publier des articles avec l'éditeur CKEditor
- Uploader des images, médias et PDFs
- Gérer les catégories, tags et auteurs
- Modérer les commentaires
- Configurer les breaking news et les sondages

---

## Déploiement

### Hébergements compatibles

Ce projet est conçu pour être déployé sur tout service supportant Python WSGI :

- **Render** (Web Service)
- **Railway**
- **Heroku**
- **DigitalOcean App Platform**
- **VPS** personnel avec Gunicorn + Nginx

### Variables d'environnement requises en production

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Clé secrète Flask (64 caractères hex recommandés) |
| `DATABASE_URL` | URL PostgreSQL (format `postgresql+psycopg2://...`) |
| `FLASK_ENV` | `production` |
| `FLASK_APP` | `app:create_app` |

### Exemple avec Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

Ou via le fichier `wsgi.py` :

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:application
```

### Points de vigilance

- Toujours utiliser **HTTPS** en production (`force_https=True` est activé automatiquement via Flask-Talisman).
- Le dossier `static/uploads/` doit être persistant si vous utilisez plusieurs workers ou redéployez fréquemment. Envisagez un stockage objet (S3, R2, etc.) pour les uploads en production.
- Le rate limiting utilise la mémoire par défaut ; pour plusieurs instances, configurez un backend Redis pour Flask-Limiter.

---

## Scripts utiles

| Commande | Description |
|----------|-------------|
| `flask run` | Lance le serveur de développement |
| `flask db init` | Initialise Flask-Migrate (une seule fois) |
| `flask db migrate -m "msg"` | Génère une migration Alembic |
| `flask db upgrade` | Applique les migrations en attente |
| `python seed_articles.py` | Injecte les articles de démonstration |
| `python migrate_sqlite_to_pg.py` | Migre les données SQLite vers PostgreSQL |

---

## Licence

Ce projet est sous licence **MIT** — voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

<p align="center">Built with passion for journalism.</p>

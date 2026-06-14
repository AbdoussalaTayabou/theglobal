"""Seed éditorial: crée 20 articles réalistes avec images, auteurs, catégories et tags.

Utilisation:
    python seed_articles.py

Le script est idempotent: il ignore les articles déjà présents et peut être
relancé sans créer de doublons. Il synchronise aussi l'ancien booléen
`published` avec le nouveau workflow `status='published'`.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models.db import db, Article, Category, Tag, Author, slugify


ARTICLES = [
    {
        "title": "Réforme institutionnelle : le Parlement ouvre un cycle de consultations",
        "category": ("Politique", "#1a2238"),
        "author": ("Awa Diop", "Rédactrice politique"),
        "tags": ["institutions", "parlement", "démocratie"],
        "image": "article-01-parlement.jpg",
        "excerpt": "Majorité, opposition et société civile doivent être reçues pendant trois semaines avant la présentation du texte final.",
        "content": """<p>Le gouvernement a ouvert une séquence de consultations destinée à préparer une réforme institutionnelle annoncée comme prioritaire. Les présidents de groupes parlementaires, les associations de magistrats et plusieurs organisations citoyennes seront auditionnés.</p>
<h2>Des points sensibles encore ouverts</h2>
<p>Le calendrier électoral, le rôle des commissions d'enquête et l'encadrement des ordonnances figurent parmi les sujets les plus discutés. Plusieurs élus demandent que le texte soit précédé d'une étude d'impact détaillée.</p>
<h2>Un vote attendu avant l'été</h2>
<p>L'exécutif espère déposer le projet de loi dans les prochaines semaines. L'opposition prévient déjà qu'elle jugera la réforme sur sa capacité à renforcer réellement le contrôle parlementaire.</p>""",
    },
    {
        "title": "Marchés financiers : les investisseurs arbitrent entre prudence et reprise",
        "category": ("Économie", "#0c6e4d"),
        "author": ("Karim Benali", "Journaliste économique"),
        "tags": ["finance", "bourse", "croissance"],
        "image": "article-02-marches.jpg",
        "excerpt": "Après plusieurs séances volatiles, les places financières cherchent une direction entre inflation persistante et résultats solides.",
        "content": """<p>Les principaux indices ont terminé en ordre dispersé, reflet d'un marché partagé entre la perspective d'une détente monétaire et la crainte d'un ralentissement de la consommation.</p>
<h2>Les valeurs industrielles résistent</h2>
<p>Les entreprises liées aux infrastructures, à l'énergie et à la logistique bénéficient de carnets de commandes encore robustes. Les valeurs technologiques, elles, restent plus sensibles aux anticipations de taux.</p>
<h2>Un trimestre décisif</h2>
<p>Les analystes surveilleront particulièrement les marges des entreprises et les indicateurs d'emploi. Une stabilisation de l'inflation pourrait relancer l'appétit pour le risque.</p>""",
    },
    {
        "title": "Intelligence artificielle : les entreprises accélèrent malgré les risques",
        "category": ("Tech", "#1f4e8c"),
        "author": ("Sophie Laurent", "Spécialiste tech"),
        "tags": ["ia", "innovation", "données"],
        "image": "article-03-ia.jpg",
        "excerpt": "De la relation client à la maintenance industrielle, les usages de l'IA se multiplient, mais la gouvernance reste inégale.",
        "content": """<p>Les directions informatiques déploient désormais des assistants internes, des outils d'analyse documentaire et des systèmes de détection d'anomalies. Les gains de productivité sont réels, mais encore difficiles à mesurer de manière homogène.</p>
<h2>La question des données</h2>
<p>La qualité des résultats dépend fortement de la gouvernance des données. Les entreprises les plus avancées ont mis en place des référentiels, des audits de biais et des circuits de validation humaine.</p>
<h2>Une régulation attendue</h2>
<p>Les juristes recommandent de documenter les modèles utilisés, les sources et les responsabilités. La transparence devient un avantage concurrentiel autant qu'une obligation de conformité.</p>""",
    },
    {
        "title": "Transports urbains : les grandes villes cherchent le bon équilibre",
        "category": ("Société", "#fd7e14"),
        "author": ("Aminata Traoré", "Reporter société"),
        "tags": ["mobilité", "ville", "transports"],
        "image": "article-04-transports.jpg",
        "excerpt": "Métros saturés, bus électriques, voies réservées : les métropoles multiplient les solutions pour absorber la demande.",
        "content": """<p>La fréquentation des réseaux de transport public retrouve, dans plusieurs capitales, des niveaux supérieurs à ceux d'avant-crise. Cette reprise met sous tension les infrastructures vieillissantes.</p>
<h2>Investir sans exclure</h2>
<p>Les autorités veulent moderniser l'offre tout en maintenant des tarifs accessibles. Les associations d'usagers réclament davantage de régularité avant toute hausse des abonnements.</p>
<h2>Le dernier kilomètre</h2>
<p>Vélos, navettes et marche sécurisée deviennent des compléments indispensables. Les urbanistes rappellent que la mobilité se joue autant dans les quartiers que dans les grands axes.</p>""",
    },
    {
        "title": "Santé publique : les hôpitaux réorganisent les urgences avant l'été",
        "category": ("Santé", "#0d6efd"),
        "author": ("Nora Haddad", "Journaliste santé"),
        "tags": ["hôpital", "santé", "urgences"],
        "image": "article-05-sante.jpg",
        "excerpt": "Face à l'afflux saisonnier, plusieurs établissements renforcent la régulation médicale et les équipes mobiles.",
        "content": """<p>Les directions hospitalières anticipent une période délicate, marquée par les départs en congé, les épisodes de chaleur et les tensions persistantes sur certains métiers.</p>
<h2>Réorienter les cas non graves</h2>
<p>Les plateformes de régulation doivent orienter plus rapidement les patients vers la médecine de ville lorsque leur situation ne nécessite pas un passage aux urgences.</p>
<h2>Des équipes sous pression</h2>
<p>Les soignants saluent les renforts annoncés mais demandent une réponse structurelle sur les effectifs, les lits disponibles et l'attractivité des carrières.</p>""",
    },
    {
        "title": "Éducation : le numérique entre dans les classes avec prudence",
        "category": ("Société", "#fd7e14"),
        "author": ("Claire Martin", "Reporter éducation"),
        "tags": ["éducation", "numérique", "école"],
        "image": "article-06-education.jpg",
        "excerpt": "Tablettes, plateformes et exercices adaptatifs gagnent du terrain, mais les enseignants demandent du temps de formation.",
        "content": """<p>Les établissements expérimentent de nouveaux outils pour personnaliser les apprentissages. L'objectif est de mieux repérer les difficultés sans remplacer le rôle central de l'enseignant.</p>
<h2>Former avant d'équiper</h2>
<p>Les syndicats insistent sur la nécessité d'accompagner les équipes. Un matériel performant ne suffit pas si les usages pédagogiques ne sont pas clairement définis.</p>
<h2>Réduire les inégalités</h2>
<p>Les collectivités veulent éviter que le numérique creuse l'écart entre élèves. L'accès à une connexion stable et à des espaces de travail reste un enjeu majeur.</p>""",
    },
    {
        "title": "Transition énergétique : les projets solaires gagnent du terrain",
        "category": ("Climat", "#2f7a3a"),
        "author": ("Élise Morel", "Journaliste environnement"),
        "tags": ["énergie", "climat", "renouvelables"],
        "image": "article-07-climat.jpg",
        "excerpt": "Les appels d'offres se multiplient, portés par la baisse des coûts et la volonté de sécuriser l'approvisionnement.",
        "content": """<p>Les installations photovoltaïques progressent dans les zones industrielles, agricoles et périurbaines. Les développeurs promettent des chantiers plus rapides et mieux concertés.</p>
<h2>Le réseau sous surveillance</h2>
<p>L'intégration de nouvelles capacités nécessite des investissements dans le stockage et les lignes électriques. Les gestionnaires de réseau veulent éviter les congestions locales.</p>
<h2>Acceptabilité locale</h2>
<p>Les élus demandent que les retombées économiques profitent davantage aux territoires. Les projets les mieux acceptés sont ceux qui associent tôt riverains et agriculteurs.</p>""",
    },
    {
        "title": "Football : les centres de formation misent sur la préparation mentale",
        "category": ("Sport", "#198754"),
        "author": ("Marc Tavernier", "Journaliste sport"),
        "tags": ["football", "formation", "performance"],
        "image": "article-08-football.jpg",
        "excerpt": "Au-delà de la technique, les clubs accompagnent désormais les jeunes joueurs sur la gestion de la pression.",
        "content": """<p>Les académies professionnelles intègrent psychologues, préparateurs mentaux et ateliers de prise de parole. La performance ne se résume plus au terrain.</p>
<h2>Prévenir l'épuisement</h2>
<p>Entre compétition, scolarité et exposition médiatique, les jeunes talents vivent un rythme intense. Les clubs veulent mieux repérer les signaux de fatigue.</p>
<h2>Un investissement de long terme</h2>
<p>Les dirigeants y voient un moyen de former des joueurs plus stables et plus autonomes. Les familles demandent une transparence accrue sur les parcours proposés.</p>""",
    },
    {
        "title": "Culture : les musées réinventent l'expérience de visite",
        "category": ("Culture", "#7a5a1f"),
        "author": ("Léa Moreau", "Critique d'art"),
        "tags": ["musée", "culture", "exposition"],
        "image": "article-09-culture.jpg",
        "excerpt": "Parcours immersifs, nocturnes et médiation renforcée attirent un public plus jeune dans les grandes institutions.",
        "content": """<p>Les musées diversifient leurs formats pour sortir d'une logique de visite silencieuse et linéaire. Les médiateurs deviennent des passeurs essentiels entre les œuvres et les publics.</p>
<h2>Le succès des horaires élargis</h2>
<p>Les nocturnes affichent souvent complet, notamment auprès des étudiants et jeunes actifs. Les établissements y voient une réponse à l'évolution des usages culturels.</p>
<h2>Préserver le sens</h2>
<p>Les conservateurs restent attentifs à ne pas transformer les expositions en simples décors. L'enjeu consiste à rendre l'art accessible sans le simplifier à l'excès.</p>""",
    },
    {
        "title": "Agriculture : l'irrigation intelligente s'impose face aux sécheresses",
        "category": ("Climat", "#2f7a3a"),
        "author": ("Yacine Berrada", "Reporter agriculture"),
        "tags": ["agriculture", "eau", "sécheresse"],
        "image": "article-10-agriculture.jpg",
        "excerpt": "Capteurs, goutte-à-goutte et prévisions météo fines aident les producteurs à réduire leur consommation d'eau.",
        "content": """<p>Dans plusieurs bassins agricoles, les exploitants investissent dans des systèmes capables d'ajuster l'arrosage au plus près des besoins des cultures.</p>
<h2>Des économies mesurables</h2>
<p>Les premières données montrent des réductions de consommation significatives, à condition que les sols soient correctement suivis et que les équipements soient entretenus.</p>
<h2>Un coût d'entrée élevé</h2>
<p>Les petites exploitations demandent des aides ciblées. Sans accompagnement, la modernisation pourrait bénéficier surtout aux structures déjà capitalisées.</p>""",
    },
    {
        "title": "Commerce mondial : les ports modernisent leur logistique",
        "category": ("Économie", "#0c6e4d"),
        "author": ("Karim Benali", "Journaliste économique"),
        "tags": ["commerce", "logistique", "ports"],
        "image": "article-11-commerce.jpg",
        "excerpt": "Automatisation, traçabilité et nouveaux terminaux doivent réduire les retards dans les chaînes d'approvisionnement.",
        "content": """<p>Les ports investissent dans des plateformes numériques pour mieux anticiper les arrivées, fluidifier les douanes et optimiser l'utilisation des quais.</p>
<h2>La donnée au cœur des opérations</h2>
<p>Armateurs, transitaires et autorités portuaires partagent davantage d'informations. Cette coopération réduit les temps d'attente mais impose de nouveaux standards de sécurité.</p>
<h2>Compétition régionale</h2>
<p>Les infrastructures capables de traiter rapidement les marchandises gagnent en attractivité. Les États y voient un levier de souveraineté économique.</p>""",
    },
    {
        "title": "Justice : les audiences filmées relancent le débat sur la transparence",
        "category": ("Politique", "#1a2238"),
        "author": ("Thomas Rivière", "Chroniqueur justice"),
        "tags": ["justice", "transparence", "tribunaux"],
        "image": "article-12-justice.jpg",
        "excerpt": "Les professionnels du droit s'interrogent sur l'équilibre entre pédagogie démocratique et protection des parties.",
        "content": """<p>La diffusion encadrée de certaines audiences pourrait rapprocher les citoyens du fonctionnement judiciaire. Mais les magistrats rappellent que le procès n'est pas un spectacle.</p>
<h2>Des garanties nécessaires</h2>
<p>Floutage, délai de diffusion et accord des personnes vulnérables font partie des garde-fous envisagés. Les avocats demandent un cadre clair avant toute généralisation.</p>
<h2>Un outil pédagogique</h2>
<p>Les facultés de droit et les médias spécialisés y voient une opportunité d'expliquer les procédures. La confiance dans l'institution dépend aussi de sa lisibilité.</p>""",
    },
    {
        "title": "Logement : les villes moyennes sous pression démographique",
        "category": ("Société", "#fd7e14"),
        "author": ("Aminata Traoré", "Reporter société"),
        "tags": ["logement", "urbanisme", "territoires"],
        "image": "article-13-logement.jpg",
        "excerpt": "L'arrivée de nouveaux habitants fait grimper les loyers et oblige les élus locaux à revoir leurs plans d'aménagement.",
        "content": """<p>Longtemps perçues comme plus accessibles, les villes moyennes connaissent une tension croissante sur le logement. Les ménages cherchent de l'espace, mais l'offre ne suit pas toujours.</p>
<h2>Construire sans étaler</h2>
<p>Les urbanistes privilégient la réhabilitation, la densification douce et la reconversion de friches. Les habitants restent attentifs à la préservation du cadre de vie.</p>
<h2>Le rôle du logement social</h2>
<p>Les bailleurs demandent des moyens pour accélérer les opérations. Sans production abordable, les travailleurs essentiels risquent d'être repoussés loin des centres.</p>""",
    },
    {
        "title": "Cybersécurité : les collectivités renforcent leurs défenses",
        "category": ("Tech", "#1f4e8c"),
        "author": ("Sophie Laurent", "Spécialiste tech"),
        "tags": ["cybersécurité", "données", "collectivités"],
        "image": "article-14-cybersecurite.jpg",
        "excerpt": "Après plusieurs attaques contre des services publics locaux, les communes mutualisent leurs outils de protection.",
        "content": """<p>Les systèmes d'information municipaux gèrent des données sensibles et des services essentiels. Leur protection devient une priorité budgétaire pour de nombreuses collectivités.</p>
<h2>Mutualiser l'expertise</h2>
<p>Les petites communes n'ont pas toujours les moyens de recruter des spécialistes. Des centres régionaux proposent désormais audit, surveillance et plans de reprise.</p>
<h2>Former les agents</h2>
<p>La majorité des incidents commence par un courriel frauduleux ou une mauvaise configuration. Les campagnes de sensibilisation restent l'un des leviers les plus efficaces.</p>""",
    },
    {
        "title": "Inflation alimentaire : les ménages adaptent leurs habitudes",
        "category": ("Économie", "#0c6e4d"),
        "author": ("Karim Benali", "Journaliste économique"),
        "tags": ["inflation", "consommation", "alimentation"],
        "image": "article-15-inflation.jpg",
        "excerpt": "Promotions ciblées, marques distributeurs et achats groupés progressent dans les paniers des consommateurs.",
        "content": """<p>La hausse des prix alimentaires ralentit mais continue de peser sur les budgets. Les familles arbitrent davantage entre qualité, quantité et prix.</p>
<h2>Des stratégies multiples</h2>
<p>Les enseignes observent une progression des achats en vrac, des lots familiaux et des marques d'entrée de gamme. Les producteurs alertent toutefois sur leurs propres coûts.</p>
<h2>Un enjeu social</h2>
<p>Les associations d'aide alimentaire signalent une demande toujours élevée. Elles appellent à renforcer les dispositifs de soutien pour les publics les plus fragiles.</p>""",
    },
    {
        "title": "Qualité de l'eau : une enquête révèle des contrôles inégaux",
        "category": ("Climat", "#2f7a3a"),
        "author": ("Élise Morel", "Journaliste environnement"),
        "tags": ["eau", "pollution", "enquête"],
        "image": "article-16-eau.jpg",
        "excerpt": "Les fréquences d'analyse varient fortement selon les territoires, alimentant les inquiétudes des riverains.",
        "content": """<p>Notre enquête montre que les moyens consacrés au suivi de certaines rivières restent très variables. Les zones proches d'activités industrielles demandent une surveillance renforcée.</p>
<h2>Des données difficiles à lire</h2>
<p>Les résultats existent souvent, mais leur accessibilité demeure limitée pour le grand public. Les associations réclament des tableaux de bord plus clairs.</p>
<h2>Responsabilités partagées</h2>
<p>Industriels, collectivités et agences de l'eau doivent coordonner leurs actions. La restauration des milieux aquatiques suppose des investissements constants.</p>""",
    },
    {
        "title": "Diplomatie : un sommet régional tente d'apaiser les tensions",
        "category": ("International", "#7a1f2b"),
        "author": ("Maya Koffi", "Correspondante internationale"),
        "tags": ["diplomatie", "sommet", "géopolitique"],
        "image": "article-17-diplomatie.jpg",
        "excerpt": "Les délégations cherchent un compromis sur la sécurité, les corridors commerciaux et la coopération énergétique.",
        "content": """<p>Les discussions se sont ouvertes dans un climat prudent. Les diplomates veulent éviter l'escalade tout en préservant les intérêts stratégiques de chaque pays.</p>
<h2>Un agenda chargé</h2>
<p>La sécurité frontalière, la circulation des marchandises et les projets énergétiques transnationaux figurent au cœur des négociations.</p>
<h2>Des attentes mesurées</h2>
<p>Les observateurs n'attendent pas d'accord spectaculaire, mais un communiqué commun poserait les bases d'un dialogue plus régulier.</p>""",
    },
    {
        "title": "Start-up : les jeunes pousses cherchent des financements plus patients",
        "category": ("Tech", "#1f4e8c"),
        "author": ("Sophie Laurent", "Spécialiste tech"),
        "tags": ["start-up", "financement", "innovation"],
        "image": "article-18-startups.jpg",
        "excerpt": "Après l'euphorie des levées rapides, les fondateurs privilégient des modèles plus sobres et rentables.",
        "content": """<p>Le marché du capital-risque s'est normalisé. Les investisseurs demandent des preuves de revenus, une trajectoire de marge et une gestion plus rigoureuse de la trésorerie.</p>
<h2>Retour aux fondamentaux</h2>
<p>Les start-up réduisent les dépenses non essentielles et allongent leur horizon de financement. La croissance reste recherchée, mais plus à n'importe quel coût.</p>
<h2>Des secteurs résistants</h2>
<p>La santé numérique, la cybersécurité et les outils industriels conservent l'attention des fonds. Les projets capables de résoudre des problèmes concrets gardent un avantage.</p>""",
    },
    {
        "title": "Cinéma : les tournages locaux attirent de nouveaux investissements",
        "category": ("Culture", "#7a5a1f"),
        "author": ("Léa Moreau", "Critique d'art"),
        "tags": ["cinéma", "culture", "production"],
        "image": "article-19-cinema.jpg",
        "excerpt": "Studios, techniciens et collectivités misent sur l'essor des productions régionales pour créer un écosystème durable.",
        "content": """<p>Les tournages se multiplient hors des capitales, portés par des décors variés et des dispositifs d'accueil plus professionnels.</p>
<h2>Former les techniciens</h2>
<p>Les écoles et associations professionnelles développent des formations courtes pour répondre aux besoins en régie, lumière, son et postproduction.</p>
<h2>Un impact économique visible</h2>
<p>Hôtels, restaurants et prestataires locaux bénéficient directement des productions. Les collectivités veulent transformer ces retombées ponctuelles en filière pérenne.</p>""",
    },
    {
        "title": "Athlétisme : les fédérations repensent la détection des talents",
        "category": ("Sport", "#198754"),
        "author": ("Marc Tavernier", "Journaliste sport"),
        "tags": ["athlétisme", "jeunesse", "sport"],
        "image": "article-20-athletisme.jpg",
        "excerpt": "Les clubs veulent repérer plus tôt les profils prometteurs sans sacrifier la santé ni les études des jeunes sportifs.",
        "content": """<p>Les performances chronométriques ne sont plus le seul critère. Les entraîneurs observent aussi la progression, la motivation et la capacité à encaisser les charges de travail.</p>
<h2>Éviter la spécialisation précoce</h2>
<p>Les médecins du sport recommandent de préserver la diversité des pratiques chez les adolescents. Une carrière longue se construit rarement dans la précipitation.</p>
<h2>Accompagner les familles</h2>
<p>Les fédérations développent des réunions d'information sur la nutrition, la récupération et l'organisation scolaire. L'entourage devient un maillon essentiel du projet sportif.</p>""",
    },
]


MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def format_date_label(dt):
    return f"{dt.day} {MONTHS_FR[dt.month - 1]} {dt.year}"


def get_or_create_category(name, color):
    cat = Category.query.filter_by(name=name).first()
    if not cat:
        cat = Category(name=name, slug=slugify(name), color=color, description=f"Actualités {name}")
        db.session.add(cat)
        db.session.flush()
    return cat


def get_or_create_author(name, role, category_name):
    author = Author.query.filter_by(name=name).first()
    if not author:
        author = Author(
            name=name,
            slug=slugify(name),
            role=role,
            bio=f"{name} couvre l'actualité {category_name.lower()} pour The Global Chronicle.",
        )
        db.session.add(author)
        db.session.flush()
    return author


def get_or_create_tags(names):
    tags = []
    for name in names:
        tag_slug = slugify(name)
        tag = Tag.query.filter((Tag.name == name) | (Tag.slug == tag_slug)).first()
        if not tag:
            tag = Tag(name=name, slug=tag_slug)
            db.session.add(tag)
            db.session.flush()
        tags.append(tag)
    return tags


def run():
    app = create_app()
    with app.app_context():
        db.create_all()
        now = datetime.utcnow()
        created = 0
        fixed_visibility = 0

        for old in Article.query.filter(Article.published.is_(True)).all():
            changed = False
            if old.status != "published":
                old.status = "published"
                changed = True
            if old.published_at is None:
                old.published_at = old.created_at or now
                changed = True
            if changed:
                fixed_visibility += 1

        for index, item in enumerate(ARTICLES):
            slug = slugify(item["title"])
            existing = Article.query.filter_by(slug=slug).first()
            if existing:
                existing.status = "published"
                existing.published = True
                if existing.published_at is None:
                    existing.published_at = now - timedelta(hours=index * 4)
                if not existing.date_label:
                    existing.date_label = format_date_label(existing.published_at)
                print(f"  - déjà présent, publication vérifiée: {item['title']}")
                continue

            cat_name, cat_color = item["category"]
            cat = get_or_create_category(cat_name, cat_color)
            author_name, author_role = item["author"]
            author = get_or_create_author(author_name, author_role, cat_name)
            tags = get_or_create_tags(item["tags"])
            image_url = f"/static/uploads/images/{item['image']}"

            article = Article(
                slug=slug,
                title=item["title"],
                excerpt=item["excerpt"],
                content=item["content"],
                image=image_url,
                image_caption="Photo d'illustration éditoriale",
                image_credit="The Global Chronicle",
                author=author_name,
                author_role=author_role,
                author_id=author.id,
                read_time="4 min",
                date_label=format_date_label(now - timedelta(hours=index * 4)),
                meta_description=item["excerpt"][:250],
                og_image=image_url,
                status="published",
                published=True,
                published_at=now - timedelta(hours=index * 4),
                category_id=cat.id,
                tags=tags,
                views=80 + index * 17,
            )
            db.session.add(article)
            created += 1
            print(f"  + créé: {item['title']}")

        db.session.commit()
        public_count = Article.query.filter(
            Article.status == "published",
            Article.published.is_(True),
            Article.published_at <= datetime.utcnow(),
        ).count()
        print(f"\n{created} article(s) créé(s).")
        print(f"{fixed_visibility} ancien(s) article(s) normalisé(s).")
        print(f"{public_count} article(s) publiés et visibles côté public.")


if __name__ == "__main__":
    run()
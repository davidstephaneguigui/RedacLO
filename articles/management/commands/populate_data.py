import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User
from articles.models import Article, ArticleVersion
from publications.models import Rubrique

class Command(BaseCommand):
    help = "Peuple la base de données avec une cinquantaine d'articles réalistes pour des tests."

    def handle(self, *args, **kwargs):
        self.stdout.write("Début du peuplement de la base de données...")

        # 1. Création des Rubriques
        rubriques_noms = ["Société", "Entreprises", "Politique", "International"]
        rubriques = {}
        for nom in rubriques_noms:
            rub, created = Rubrique.objects.get_or_create(nom=nom)
            rubriques[nom] = rub
        self.stdout.write(f"{len(rubriques)} rubriques prêtes.")

        # 2. Création des Utilisateurs (si non existants)
        # On crée quelques rédacteurs, relecteurs et éditeurs pour varier les plaisirs.
        users_data = [
            ("redac_test1", "redacteur", "Jean", "Dupont"),
            ("redac_test2", "correspondant", "Marie", "Curie"),
            ("redac_test3", "editorialiste", "Albert", "Camus"),
            ("relec_test1", "relecteur", "Simone", "Weil"),
            ("relec_test2", "relecteur", "Jean-Paul", "Sartre"),
            ("edit_test1", "editeur", "Victor", "Hugo"),
        ]
        users = {}
        for username, role, first_name, last_name in users_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": role,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@example.com",
                }
            )
            if created:
                user.set_password("password123")
                user.save()
            users[username] = user
        self.stdout.write(f"{len(users)} utilisateurs prêts.")

        # 3. Banque de titres et contenus inspirés de Lutte Ouvrière
        # (Titres issus des sommaires des numéros 3030 à 3036)
        articles_data = [
            # Éditoriaux / Politique
            ("Vive la mobilisation lycéenne, et faisons naître celle des travailleurs !", "editorial", "Politique"),
            ("Loi \"casseurs-payeurs\" : pour faire payer les manifestants !", "article", "Politique"),
            ("Budget : des attaques programmées", "article", "Politique"),
            ("Leur société : la bourgeoisie ne connaît pas la crise", "article", "Société"),
            ("Fisc : niches de riches", "article", "Politique"),
            ("Contre-budget du RN : comme promis au Medef", "article", "Politique"),
            ("Procès Ménard : l'amour au temps du racisme d'État", "article", "Société"),
            ("Les \"rafles oubliées\" de Marseille en janvier 1943", "article", "Société"),
            ("UE : la chasse aux migrants est ouverte", "article", "International"),
            ("Prime d'activité : souriez, vous êtes taxé !", "article", "Société"),

            # Économie / Entreprises
            ("Armement : explosion des profits, pour l'instant", "article", "Entreprises"),
            ("TotalEnergies : profiteur de guerre et fier de l'être", "article", "Entreprises"),
            ("Famille Peugeot : beaucoup d'œufs dans beaucoup de paniers", "article", "Entreprises"),
            ("Restos du cœur : la misère déborde", "article", "Société"),
            ("Renault-Flins, Stellantis-Poissy : l'union fait la force", "article", "Entreprises"),
            ("Chômage fiscal et perte de salaire", "article", "Entreprises"),
            ("La Poste : halte aux fermetures de bureaux !", "article", "Entreprises"),
            ("Sanofi : à la santé des actionnaires", "article", "Entreprises"),
            ("Schaeffler - Toulouse : l'automobile rapporte, l'armement aussi !", "article", "Entreprises"),
            ("CMA CGM : même pas la reconnaissance du ventre", "article", "Entreprises"),

            # International
            ("Ukraine-Europe : une \"aide\" mortelle", "article", "International"),
            ("États-Unis : exécution ratée, barbarie assumée", "article", "International"),
            ("Brésil : Bolsonaro, le retour", "article", "International"),
            ("Yémen : l'acharnement de la monarchie saoudienne", "article", "International"),
            ("Espagne : à défaut de se loger, on pourra voter...", "article", "International"),
            ("Iran : la population sous les bombes et les restrictions", "article", "International"),
            ("Mayotte : davantage de moyens... contre les pauvres !", "article", "International"),

            # Société / Mouvements sociaux
            ("Manifestations du 6 octobre : un grand succès", "article", "Société"),
            ("Lycéens : toutes les raisons de se révolter !", "article", "Société"),
            ("Lycée Gutenberg - Créteil : le ministre est de sortie... les lycéens aussi !", "article", "Société"),
            ("Guyane : ça démarre", "article", "Société"),
            ("Lycée Guillaume-Apollinaire - Thiais : ce n'est qu'un début !", "article", "Société"),
            ("Syndicats : un appel tardif", "article", "Société"),
            ("Lyon : 280 femmes et enfants menacés d'expulsion !", "article", "Société"),
            ("Octobre rose : dictature des trusts", "article", "Société"),
            ("CPF : à vos frais !", "article", "Société"),
            ("Nantes : accident mortel de vie chère", "article", "Société"),

            # Brèves / Échos
            ("Lycée de Reims : deux classes, deux ambiances", "breve", "Société"),
            ("Où est la vraie violence ?", "breve", "Politique"),
            ("Écoles : même quelques sous, c'est encore trop", "breve", "Société"),
            ("Eau contaminée : aux pollueurs de payer !", "breve", "Société"),
            ("Retraites : un racket de 6 milliards", "breve", "Politique"),
            ("Nouveau service militaire : la même mise en condition", "breve", "Société"),
        ]

        # On duplique et on mélange pour arriver à ~50 articles
        while len(articles_data) < 50:
            articles_data.extend(random.sample(articles_data, min(10, 50 - len(articles_data))))

        random.shuffle(articles_data)

        statuts_possibles = ["brouillon", "soumis", "en_relecture", "valide", "rejete"]
        count = 0

        for titre, type_art, rubrique_nom in articles_data:
            # On choisit un rédacteur au hasard
            redacteur = random.choice(list(users.values()))
            
            # On détermine le statut
            statut = random.choice(statuts_possibles)
            
            # Contenu factice mais réaliste
            contenu = f"<p>Ceci est le contenu de l'article intitulé « {titre} ».</p>"
            contenu += f"<p>Dans le cadre de la rubrique {rubrique_nom}, cet article aborde les thématiques chères à la rédaction.</p>"
            contenu += "<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</p>"
            contenu += "<p>Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>"

            article = Article.objects.create(
                titre=titre,
                sous_titre="",
                type_article=type_art,
                rubrique=rubriques[rubrique_nom],
                contenu=contenu,
                redacteur=redacteur,
                statut=statut
            )

            # Création de la version initiale (v0)
            version_initiale = ArticleVersion.creer(
                article=article,
                contenu=article.contenu,
                redacteur=redacteur,
                parent=None,
                type="redacteur",
                commentaire="Version initiale (test).",
            )
            version_initiale.statut = "brouillon" if statut == "brouillon" else "soumise"
            version_initiale.save()
            article.version_reference = version_initiale
            article.save()

            # Si l'article est en relecture ou validé, on simule une relecture
            if statut in ["en_relecture", "valide", "rejete"]:
                relecteur = random.choice([u for u in users.values() if u.role in ["relecteur", "editeur"]])
                
                # Création d'une version de relecture (v1)
                version_relec = ArticleVersion.creer(
                    article=article,
                    contenu=article.contenu + "<p>Note du relecteur : ajout d'une précision.</p>",
                    redacteur=relecteur,
                    parent=version_initiale,
                    type="relecture",
                    commentaire="Relecture de test.",
                )
                
                if statut == "valide":
                    version_relec.statut = "validee"
                elif statut == "rejete":
                    version_relec.statut = "rejetee"
                    version_relec.commentaire_validation = "Rejeté pour test."
                else:
                    version_relec.statut = "soumise"
                
                version_relec.save()

                if statut == "valide":
                    article.statut = "valide"
                    article.save()

            count += 1

        self.stdout.write(self.style.SUCCESS(f"Succès : {count} articles créés avec succès !"))
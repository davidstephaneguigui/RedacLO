from django.core.management.base import BaseCommand
from articles.models import Article, ArticleVersion


class Command(BaseCommand):
    help = (
        "Crée une version initiale pour chaque article qui n'en a pas. "
        "À lancer une fois après l'ajout du modèle Annotation."
    )

    def handle(self, *args, **options):
        articles_sans_version = [
            a for a in Article.objects.all()
            if not a.versions.exists()
        ]

        total = len(articles_sans_version)
        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                "Tous les articles ont déjà au moins une version."
            ))
            return

        for article in articles_sans_version:
            ArticleVersion.objects.create(
                article=article,
                numero=1,
                contenu=article.contenu,
                modifie_par=article.redacteur,
                commentaire="Version initiale créée automatiquement.",
            )

        self.stdout.write(self.style.SUCCESS(
            f"{total} version(s) initiale(s) créée(s)."
        ))
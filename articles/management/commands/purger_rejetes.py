from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from articles.models import Article

class Command(BaseCommand):
    help = "Supprime définitivement les articles rejetés depuis plus de 30 jours."

    def add_arguments(self, parser):
        # Option pour changer le nombre de jours (par défaut 30)
        parser.add_argument(
            '--jours', 
            type=int, 
            default=30, 
            help="Nombre de jours de rétention avant suppression (défaut : 30)"
        )

    def handle(self, *args, **options):
        jours = options['jours']
        date_limite = timezone.now() - timedelta(days=jours)

        # On cherche les articles rejetés modifiés avant la date limite
        articles_a_supprimer = Article.objects.filter(
            statut="rejete",
            date_modification__lt=date_limite
        )
        
        nombre = articles_a_supprimer.count()

        if nombre == 0:
            self.stdout.write(self.style.SUCCESS("Aucun article rejeté à purger pour le moment."))
            return

        # Suppression (attention : cela supprime aussi les versions et images liées via on_delete=CASCADE)
        articles_a_supprimer.delete()
        
        self.stdout.write(
            self.style.SUCCESS(f"Succès : {nombre} article(s) rejeté(s) depuis plus de {jours} jours ont été supprimés.")
        )
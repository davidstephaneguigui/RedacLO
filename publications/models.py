from django.db import models


class GabaritPage(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom du gabarit")
    description = models.TextField(blank=True, null=True, verbose_name="Description (optionnel)")
    
    def __str__(self):
        return self.nom

    class Meta:
        verbose_name = "Gabarit de page"
        verbose_name_plural = "Gabarits de page"


class Rubrique(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom de la rubrique")
    position = models.PositiveIntegerField(default=0, verbose_name="Position")
    
    publication = models.ForeignKey(
        'Publication', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="rubriques_diverses",
        verbose_name="Rattachée au numéro"
    )

    class Meta:
        ordering = ["position"]
        verbose_name = "Rubrique"
        verbose_name_plural = "Rubriques"

    def __str__(self):
        return self.nom

    
class Publication(models.Model):
    STATUTS = [
        ("en_cours", "En cours de bouclage"),
        ("gele", "Gelé"),
        ("publie", "Publié"),
    ]
    
    numero = models.PositiveIntegerField()
    volume = models.PositiveIntegerField()
    date = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUTS, default="en_cours")
    
    articles = models.ManyToManyField(
        "articles.Article",
        related_name="publications",
        blank=True,
    )
    fichier_pdf = models.FileField(
        upload_to="publications/",
        blank=True,
        null=True,
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = ("numero", "volume")

    @classmethod
    def prochain_numero(cls):
        """Calcule le numéro de publication en fonction du nombre de semaines écoulées."""
        from datetime import date
        
        # Date de référence : le lundi de la semaine 43 de 2026 (19 octobre 2026)
        date_reference = date(2026, 10, 19)
        numero_reference = 3038
        
        aujourd_hui = date.today()
        
        # On calcule le nombre de jours écoulés, puis on divise par 7 pour avoir les semaines
        difference_jours = (aujourd_hui - date_reference).days
        difference_semaines = difference_jours // 7
        
        numero_calcule = numero_reference + difference_semaines
        
        # Sécurité : on ne recule jamais par rapport au dernier numéro existant en base
        # (au cas où une publication aurait été créée manuellement avec un numéro plus grand)
        dernier = cls.objects.order_by('-numero').first()
        if dernier and dernier.numero >= numero_calcule:
            return dernier.numero + 1
            
        return numero_calcule

    def __str__(self):
        return f"Volume {self.volume}, n°{self.numero} ({self.date})"


class Page(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="pages")
    numero_page = models.PositiveIntegerField()
    rubrique = models.ForeignKey(Rubrique, on_delete=models.SET_NULL, null=True, blank=True)
    articles = models.ManyToManyField("articles.Article", related_name="pages", blank=True)
    titre_une = models.CharField(max_length=200, blank=True)
    
    # Deux champs pour les illustrations
    petites_illustrations = models.PositiveIntegerField(default=0)
    grandes_illustrations = models.PositiveIntegerField(default=0)

    # Lien vers le gabarit
    gabarit = models.ForeignKey(GabaritPage, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Modèle de page")

    class Meta:
        ordering = ["numero_page"]
        unique_together = ("publication", "numero_page")

    def total_signes(self):
        total = 0
        for article in self.articles.all():
            # On prend la version validée de l'article pour compter les signes
            v = article.versions.filter(statut="validee").first()
            if v:
                total += v.nombre_signes()
        return total

    def articles_tries(self):
        """Retourne les articles de la page triés par ordre d'apparition."""
        # On trie par ordre_sur_page. Si l'ordre est identique (ex: 0), on trie par date.
        return self.articles.all().order_by('ordre_sur_page', 'date_creation')

    def limite_signes(self):
        p = self.petites_illustrations
        g = self.grandes_illustrations
        
        # Règle sans illustration
        if p == 0 and g == 0: return 7500
        # Règles 1 illustration
        if p == 1 and g == 0: return 7000
        if p == 0 and g == 1: return 6700
        # Règles 2 illustrations
        if p == 2 and g == 0: return 6500
        if p == 1 and g == 1: return 6200
        if p == 0 and g == 2: return 5900
        # Règles 3 illustrations
        if p == 3 and g == 0: return 6000
        if p == 2 and g == 1: return 5700
        # Si combinaison non prévue (ex: 2 grandes + 1 petite), on met une limite basse par sécurité
        return 5500


    @property
    def nombre_illustrations(self):
        """Retourne le nombre total d'illustrations sur la page."""
        return self.petites_illustrations + self.grandes_illustrations
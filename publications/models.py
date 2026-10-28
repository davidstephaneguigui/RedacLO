from django.db import models

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
    annee = models.PositiveBigIntegerField(default=2026, verbose_name="Année")
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

    @classmethod
    def __str__(self):
        return f"N°{self.numero} ({self.annee})"

class Page(models.Model):
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name="pages")
    numero_page = models.PositiveIntegerField()
    rubrique = models.ForeignKey(Rubrique, on_delete=models.SET_NULL, null=True, blank=True)
    titre_une = models.CharField(max_length=200, blank=True)
    
    # Deux champs pour les illustrations
    petites_illustrations = models.PositiveIntegerField(default=0)
    grandes_illustrations = models.PositiveIntegerField(default=0)

    # Lien vers le gabarit
    gabarit = models.ForeignKey('display.GabaritPage', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["numero_page"]
        unique_together = ("publication", "numero_page")

    def total_signes(self):
        total = 0
        for pa in self.articles_lies.all():
            if pa.signes_sur_page is not None:
                total += pa.signes_sur_page
            else:
                version = pa.article.version_courante()
                if version:
                    total += version.nombre_signes()
        return total

    def articles_tries(self):
        """Retourne les articles de la page triés par ordre d'apparition."""
        # On trie par ordre_sur_page. Si l'ordre est identique (ex: 0), on trie par date.
        # return self.articles.all().order_by('ordre_sur_page', 'date_creation')
        return [pa.article for pa in self.articles_lies.all().order_by('position')]

    def limite_signes(self):
        # Règle spéciale pour la page Éditorial (Page 2)
        if self.numero_page == 2:
            return 6000

        p = self.petites_illustrations
        g = self.grandes_illustrations
        
        # Calcul de la limite (7500 de base - 500 par petite - 800 par grande)
        limite = 7500 - (500 * p) - (800 * g)
        
        # Sécurité : on ne descend jamais en dessous de 5700
        return max(5700, limite)


    @property
    def nombre_illustrations(self):
        """Retourne le nombre total d'illustrations sur la page."""
        return self.petites_illustrations + self.grandes_illustrations

class PageArticle(models.Model):
    page = models.ForeignKey('Page', on_delete=models.CASCADE, related_name="articles_lies")
    article = models.ForeignKey('articles.Article', on_delete=models.CASCADE, related_name="placements")
    
    position = models.PositiveIntegerField(default=1, verbose_name="Ordre sur la page")
    est_debut = models.BooleanField(default=True, verbose_name="Commence sur cette page")
    est_fin = models.BooleanField(default=True, verbose_name="Finit sur cette page")

    # Permet de forcer le nombre de signes sur cette page
    signes_sur_page = models.PositiveIntegerField(null=True, blank=True, verbose_name="Signes sur cette page (optionnel)")

    class Meta:
        ordering = ["position"]
        unique_together = ('page', 'article')
        verbose_name = "Article sur page"

    def __str__(self):
        return f"{self.article.titre} (P.{self.page.numero_page} - Pos {self.position})"

    
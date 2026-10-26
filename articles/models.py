from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError


def annotations_se_chevauchent(a, b):
    """
    Vérifie si deux annotations occupent une position commune.
    Les commentaires sont ignorés (ils ne modifient pas le texte).

    Convention :
      - une insertion à x occupe le singleton {x} ;
      - une suppression ou un remplacement occupe [debut, fin[.
    """
    if a.type == "commentaire" or b.type == "commentaire":
        return False

    a_debut = a.debut
    a_fin = a.fin if a.type == "insertion" else a.fin - 1
    b_debut = b.debut
    b_fin = b.fin if b.type == "insertion" else b.fin - 1

    return max(a_debut, b_debut) <= min(a_fin, b_fin)


class Article(models.Model):
    STATUTS = [
        ("brouillon", "Brouillon"),
        ("soumis", "Soumis"),
        ("en_relecture", "En relecture"),
        ("relu", "Relu"),
        ("revisions_demandees", "Révisions demandées"),
        ("valide", "Validé"),
        ("rejete", "Rejeté"),
        ("publie", "Publié"),
    ]
    
    STATUTS_SELECTION = [
        ("a_choisir", "À choisir pour le numéro"),
        ("disponible", "Disponible (dans le vivier)"),
        ("reserve", "Réservé (marronnier)"),
        ("utilise", "Utilisé (placé)"),
    ]

    TYPES_ARTICLE = [
        ("article", "Article"),
        ("breve", "Brève"),
        ("echo", "Écho"),
        ("courrier", "Courrier des lecteurs"),
        ("article_editorial", "Éditorial"),
    ]

    # Champs de base
    titre = models.CharField(max_length=200, help_text="Titre principal de l'article.")
    sur_titre = models.CharField(max_length=200, blank=True, help_text="Sur-titre de l'article.")
    type_article = models.CharField(max_length=20, choices=TYPES_ARTICLE, default="article", verbose_name="Type d'article")
    
    redacteur = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="articles_rediges",
        verbose_name="Rédacteur"
    )
    contenu = models.TextField()
    statut = models.CharField(max_length=20, choices=STATUTS, default="brouillon")
    
    # Champs pour la composition du numéro
    rubrique = models.ForeignKey(
        "publications.Rubrique", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="articles"
    )
    statut_selection = models.CharField(max_length=20, choices=STATUTS_SELECTION, default="a_choisir")

    # Dates et relations
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    version_reference = models.ForeignKey(
        "ArticleVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+"
    )

    # Champs pour la double validation
    valide_1_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="articles_valides_1",
        verbose_name="Premier validateur"
    )
    valide_2_par = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="articles_valides_2",
        verbose_name="Second validateur"
    )

    # Champs pour la validation par mandataire (si le rédacteur est un mandataire)

    valide_1_mandataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="articles_mandates_1",
        verbose_name="Premier validateur (mandataire)"
    )
    valide_2_mandataire = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="articles_mandates_2",
        verbose_name="Second validateur (mandataire)"
    )

    # Lier un article réservé à un numéro futur spécifique
    numero_reserve = models.ForeignKey(
        'publications.Publication', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='articles_reserves',
        verbose_name="Réservé pour le numéro"
    )

    def version_courante(self):
        """Retourne la version la plus récente de l'article."""
        return self.versions.order_by("-numero").first()

    def save(self, *args, **kwargs):
        # Nettoyage du contenu
        if self.contenu:
            import re
            contenu_nettoye = re.sub(r'[ \t]+', ' ', self.contenu)
            contenu_nettoye = re.sub(r'\n{3,}', '\n\n', contenu_nettoye)
            contenu_nettoye = '\n'.join([ligne.strip() for ligne in contenu_nettoye.split('\n')])
            self.contenu = contenu_nettoye.strip()

        super().save(*args, **kwargs)

    def info_relectures(self):
        """Retourne une chaîne indiquant le nombre de relectures en cours et déposées."""
        versions_relecture = self.versions.filter(type="relecture")
        en_cours = versions_relecture.filter(statut="brouillon").count()
        deposees = versions_relecture.exclude(statut="brouillon").count()
        
        if en_cours == 0 and deposees == 0:
            return "Aucune"
            
        elements = []
        if deposees > 0:
            elements.append(f"{deposees} déposée{'s' if deposees > 1 else ''}")
        if en_cours > 0:
            elements.append(f"{en_cours} en cours")
            
        return " et ".join(elements)

    def couleur_info_relectures(self):
        """Détermine la couleur (classe CSS) selon l'état des relectures."""
        versions_relecture = self.versions.filter(type="relecture")
        deposees = versions_relecture.exclude(statut="brouillon").count()
        
        if deposees > 0:
            return "text-success"
        elif self.info_relectures() != "Aucune":
            return "text-warning"
        return "text-muted"

    def get_avis_actuel(self):
        """Retourne l'avis du relecteur si l'article est au statut 'relu'."""
        if self.statut == "relu":
            version = self.versions.filter(type="relecture").exclude(statut="brouillon").last()
            if version:
                return version.avis_relecteur
        return None

    def __str__(self):
        return self.titre

    
class ArticleVersion(models.Model):
    """
    Version figée du texte d'un article.

    Chaque version a un parent (sauf la version initiale de le rédacteur),
    ce qui forme un arbre de versions parallèles. Un relecteur crée
    sa version à partir de la version de référence de l'article.

    Le champ est_finale est mis à True par l'éditeur sur la version
    qu'il retient.
    """
    TYPES = [
        ("redacteur", "Rédacteur"),
        ("relecture", "Relecture"),
    ]

    STATUTS = [
        ("brouillon", "Brouillon"),
        ("soumise", "Soumise (à valider)"),
        ("validee", "Validée"),
        ("rejetee", "Rejetée"),
        ("archivee", "Archivée (traitée)"),
    ]

    AVIS_CHOICES = [
        ("favorable", "Favorable"),
        ("defavorable", "Défavorable"),
    ]
    avis_relecteur = models.CharField(
        max_length=20, 
        choices=AVIS_CHOICES, 
        blank=True, 
        null=True,
        verbose_name="Avis du relecteur"
    )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enfants",
    )
    numero = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=20, choices=TYPES, default="redacteur")
    contenu = models.TextField()
    modifie_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="versions_modifiees",
        verbose_name="Modifié par"
    )
    commentaire = models.TextField(blank=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUTS,
        default="brouillon",
    )
    commentaire_validation = models.TextField(
        blank=True,
        help_text="Commentaire de l'éditeur en cas de rejet.",
    )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.article.titre} — v{self.numero} ({self.get_type_display()})"

    @classmethod
    def creer(cls, article, contenu, modifie_par, parent=None, type="relecture", commentaire=""):
        # 1. Calcul du prochain numéro
        dernier_numero = article.versions.aggregate(models.Max('numero'))['numero__max'] or 0
        prochain_numero = dernier_numero + 1

        # 2. Création de la version avec le bon nom de champ
        version = cls.objects.create(
            article=article,
            numero=prochain_numero,
            contenu=contenu,
            modifie_par=modifie_par,  # <--- C'est ici qu'on utilise le nouveau nom
            parent=parent,
            type=type,
            commentaire=commentaire
        )
        return version

    def est_modifiable_par(self, user):
        """
        Une version est modifiable par le rédacteur (son auteur), tant qu'elle est
        en brouillon. Une version soumise, validée ou rejetée est figée.
        """
        return (
            self.statut == "brouillon"
            and self.modifie_par == user
        )

    def nombre_signes(self):
        """
        Compte les signes du contenu de cette version.

        Les suites d'espaces et les sauts de ligne sont normalisés
        en un seul espace, pour un décompte fiable (convention
        typographique).
        """
        import re
        texte = re.sub(r"\s+", " ", self.contenu).strip()
        return len(texte)

    def peut_etre_supprimee(self, par_user=None):
        # RÈGLE ABSOLUE : on ne supprime jamais la version initiale de l'auteur
        if self.type == "redacteur":
            return False

        # NOUVELLE RÈGLE : une version soumise, validée ou rejetée est figée
        if self.statut != "brouillon":
            return False

        if self.enfants.exists():
            return False
        if self.article.version_reference_id == self.pk:
            return False
        if self.article.versions.count() <= 1:
            return False

        if par_user is None:
            return True

        if par_user.role in ("editeur", "admin"):
            return True

        return self.modifie_par == par_user

    def delete(self, *args, **kwargs):
        # Interdit la suppression de la version originale du rédacteur
        if self.type == "redacteur":
            from django.core.exceptions import ValidationError
            raise ValidationError("Impossible de supprimer la version initiale du rédacteur.")
        super().delete(*args, **kwargs)


class Annotation(models.Model):
    """
    Annotation d'un relecteur sur une version figée d'un article.

    Une annotation cible un intervalle [debut, fin] dans le contenu
    de la version concernée. Selon son type, elle propose une
    suppression, une insertion, un remplacement, ou un simple
    commentaire.
    """
    TYPES = [
        ("suppression", "Suppression"),
        ("insertion", "Insertion"),
        ("remplacement", "Remplacement"),
        ("commentaire", "Commentaire"),
    ]

    STATUTS = [
        ("proposee", "Proposée"),
        ("acceptee", "Acceptée"),
        ("rejetee", "Rejetée"),
        ("obsolete", "Obsolète"),
    ]

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    version = models.ForeignKey(
        ArticleVersion,
        on_delete=models.CASCADE,
        related_name="annotations",
    )
    redacteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="annotations_proposees",
    )
    type = models.CharField(max_length=20, choices=TYPES)
    debut = models.PositiveIntegerField()
    fin = models.PositiveIntegerField()
    texte_original = models.TextField(blank=True)
    texte_propose = models.TextField(blank=True)
    commentaire = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default="proposee")
    decidee_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="annotations_decidees",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_decision = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.debut > self.fin:
            raise ValidationError(
                "La position de début doit être inférieure ou égale à la fin."
            )

        if self.type == "insertion":
            if self.debut != self.fin:
                raise ValidationError(
                    "Une insertion doit avoir debut == fin."
                )
            if not self.texte_propose:
                raise ValidationError(
                    "Une insertion doit proposer un texte."
                )

        elif self.type == "suppression":
            if self.debut >= self.fin:
                raise ValidationError(
                    "Une suppression doit cibler un passage non vide."
                )
            if self.texte_propose:
                raise ValidationError(
                    "Une suppression ne propose pas de texte."
                )

        elif self.type == "remplacement":
            if self.debut >= self.fin:
                raise ValidationError(
                    "Un remplacement doit cibler un passage non vide."
                )
            if not self.texte_propose:
                raise ValidationError(
                    "Un remplacement doit proposer un texte."
                )

        elif self.type == "commentaire":
            if self.debut >= self.fin:
                raise ValidationError(
                    "Un commentaire doit cibler un passage non vide."
                )
            if self.texte_propose:
                raise ValidationError(
                    "Un commentaire ne propose pas de texte."
                )
    class Meta:
        ordering = ["version", "debut"]

    def __str__(self):
        return (
            f"{self.get_type_display()} "
            f"({self.debut}-{self.fin}) "
            f"par {self.redacteur.username}"
        )


class Image(models.Model):
    TAILLES = [
        ("petite", "Petite"),
        ("grande", "Grande"),
    ]

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="images")
    fichier = models.ImageField(upload_to="articles/images/")
    legende = models.CharField(max_length=255, blank=True)
    
    # NOUVEAU CHAMP
    est_prise_par_redacteur = models.BooleanField(
        default=False, 
        help_text="Est-ce que c'est toi qui as pris cette photo ?"
    )
    
    droits_ok = models.BooleanField(
        default=False, 
        help_text="Je certifie que nous avons les droits d'utilisation"
    )
    taille = models.CharField(max_length=10, choices=TAILLES, default="petite")
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image pour {self.article.titre} ({self.taille})"
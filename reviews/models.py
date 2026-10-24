from django.conf import settings
from django.db import models


class Review(models.Model):
    DECISIONS = [
        ("en_attente", "En attente"),
        ("accepte", "Accepté"),
        ("revisions", "Révisions demandées"),
        ("rejete", "Rejeté"),
    ]

    COULEURS = [
            ("bleu", "Bleu"),
            ("violet", "Violet"),
            ("vert", "Vert"),
            ("orange", "Orange"),
            ("rouge", "Rouge"),
            ("brun", "Brun"),
        ]
    couleur = models.CharField(max_length=20, choices=COULEURS, default="bleu")

    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    relecteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews_effectuees",
    )

    commentaire = models.TextField()
    decision = models.CharField(max_length=20, choices=DECISIONS)
    date = models.DateTimeField(auto_now_add=True)


    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"Review de {self.article.titre} par {self.relecteur.username}"

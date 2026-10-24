from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Notification in-app destinée à un utilisateur.

    Une notification est créée par un événement métier (article soumis,
    article assigné, annotation créée, annotation tranchée). Elle reste
    dans l'application, peut être consultée à tout moment, et se marque
    comme lue quand l'utilisateur clique dessus.
    """

    TYPES = [
        ("article_soumis", "Article soumis"),
        ("article_assigne", "Article assigné"),
        ("annotation_creee", "Annotation créée"),
        ("annotation_tranchee", "Annotation tranchée"),
        ("review_deposee", "Relecture déposée"),
    ]

    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_recues",
    )
    emetteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_envoyees",
    )
    type = models.CharField(max_length=30, choices=TYPES)
    message = models.TextField()
    lien = models.CharField(max_length=500, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    lue = models.BooleanField(default=False)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_creation"]
        indexes = [
            models.Index(fields=["destinataire", "lue"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()} → {self.destinataire.username}"

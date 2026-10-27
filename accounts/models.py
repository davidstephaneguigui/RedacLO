import uuid
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    # La nouvelle liste de rôles
    ROLES = [
        ("admin", "Administrateur"),
        ("editeur", "Éditeur"),
        ("membre_redaction", "Membre de la rédaction"),
        ("redacteur", "Rédacteur"),
    ]
    
    COULEURS = [
        ("bleu", "Bleu"), ("violet", "Violet"), ("gris", "Gris ardoise"),
        ("marine", "Bleu marine"), ("orangefonce", "Orange foncé"),
        ("marron", "Marron"), ("rouge", "Rouge"), ("vert", "Vert"),
    ]

    role = models.CharField(max_length=20, choices=ROLES, default="redacteur")
    couleur = models.CharField(max_length=20, choices=COULEURS, default="bleu")
    
    # Champ pour la signature par défaut
    signature_defaut = models.CharField(
        max_length=100, 
        blank=True, 
        help_text="Ex: 'Correspondant LO'. Laisser vide pour utiliser le Prénom Nom."
    )
    couleur = models.CharField(
        max_length=20,
        choices=COULEURS,
        default="bleu",
        help_text="Couleur utilisée pour ses annotations dans les articles.",
    )

    def get_signature(self):
        """Retourne la signature par défaut, ou le nom complet, ou le username."""
        if self.signature_defaut:
            return self.signature_defaut
        if self.get_full_name():
            return self.get_full_name()
        return self.username

    def est_redacteur(self):
        return self.role in ("redacteur", "redacteur_breves", "correspondant", "editorialiste")


    def __str__(self):
        return self.username


class Invitation(models.Model):
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=User.ROLES)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    auteur_modification = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invitations_envoyees",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField()
    utilisee = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_creation"]

    def __str__(self):
        return f"Invitation pour {self.email} ({self.role})"

    def est_valide(self):
        return not self.utilisee and timezone.now() < self.date_expiration

    def save(self, *args, **kwargs):
        if not self.date_expiration:
            self.date_expiration = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
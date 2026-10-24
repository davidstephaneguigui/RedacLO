from django.urls import reverse
from .models import Notification


def creer_notification(destinataire, type, message, lien="", emetteur=None):
    """
    Crée une notification in-app pour un destinataire.

    Arguments :
      - destinataire : instance User qui reçoit la notification.
      - type : chaîne, l'un des types de Notification.TYPES.
      - message : texte court décrivant l'événement.
      - lien : URL à ouvrir au clic (peut être vide).
      - emetteur : instance User à l'origine de l'action (peut être None).

    Retourne l'instance Notification créée, ou None si le destinataire
    n'est pas valide.
    """
    if not destinataire or not destinataire.pk:
        return None

    if emetteur and emetteur == destinataire:
        # On ne notifie pas quelqu'un pour sa propre action.
        return None

    return Notification.objects.create(
        destinataire=destinataire,
        emetteur=emetteur,
        type=type,
        message=message,
        lien=lien,
    )
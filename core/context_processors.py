from .models import Notification


def notifications_non_lues(request):
    """
    Rend disponible, dans tous les templates, le nombre de
    notifications non lues de l'utilisateur connecté.
    """
    if not request.user.is_authenticated:
        return {"notifications_non_lues": 0}

    count = Notification.objects.filter(
        destinataire=request.user,
        lue=False,
    ).count()

    return {"notifications_non_lues": count}
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from .models import Notification
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def accueil(request):
    notifications_recentes = []
    notifications_total_non_lues = 0
    if request.user.is_authenticated:
        qs = Notification.objects.filter(
            destinataire=request.user,
            lue=False,
        ).order_by("-date_creation")
        notifications_total_non_lues = qs.count()
        notifications_recentes = qs[:5]

    return render(request, "core/accueil.html", {
        "notifications_recentes": notifications_recentes,
        "notifications_total_non_lues": notifications_total_non_lues,
        "cacher_login": not request.user.is_authenticated,
    })


@role_required("redacteur")
def notifications(request):
    """
    Page listant les notifications de l'utilisateur connecté,
    les plus récentes en haut.
    """
    liste = Notification.objects.filter(
        destinataire=request.user,
    ).order_by("-date_creation")

    return render(request, "core/notifications.html", {"notifications": liste})


@role_required("redacteur")
def marquer_lue(request, pk):
    """
    Marque une notification comme lue, puis redirige vers son lien.
    Si le lien est vide, redirige vers la page de notifications.
    """
    notification = get_object_or_404(
        Notification,
        pk=pk,
        destinataire=request.user,
    )

    if not notification.lue:
        notification.lue = True
        notification.date_lecture = timezone.now()
        notification.save()

    if notification.lien:
        return redirect(notification.lien)
    return redirect("core:notifications")


@login_required
@require_POST
def marquer_selection(request):
    if request.method == "POST":
        notification_ids = request.POST.getlist("notification_ids")
        action = request.POST.get("action")
        
        if notification_ids:
            # On filtre toujours par utilisateur pour la sécurité
            notifications = Notification.objects.filter(pk__in=notification_ids, destinataire=request.user)
            
            if action == "lu":
                notifications.update(est_lue=True)
                messages.success(request, "Les notifications sélectionnées ont été marquées comme lues.")
            elif action == "non_lu":
                notifications.update(est_lue=False)
                messages.success(request, "Les notifications sélectionnées ont été marquées comme non lues.")
            elif action == "supprimer":
                count = notifications.count()
                notifications.delete()
                messages.success(request, f"{count} notification(s) supprimée(s).")
                
    return redirect("core:notifications")
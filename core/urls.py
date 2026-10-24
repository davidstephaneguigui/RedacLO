from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("notifications/", views.notifications, name="notifications"),
    path("notifications/<int:pk>/lire/", views.marquer_lue, name="marquer_lue"),
    path("notifications/marquer-selection/", views.marquer_selection, name="marquer_selection"),
    path("", views.accueil, name="accueil"),
]
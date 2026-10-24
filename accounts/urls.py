from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("inviter/", views.inviter, name="inviter"),
    path("invitation/<uuid:token>/", views.accepter_invitation, name="accepter_invitation"),
]
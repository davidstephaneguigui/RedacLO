from django.urls import path
from . import views

app_name = "reviews"

urlpatterns = [
    path("a-relire/", views.a_relire, name="a_relire"),
    path("deposer/<int:review_pk>/", views.deposer_review, name="deposer_review"),
]
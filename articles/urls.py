from django.urls import path
from . import views

app_name = "articles"

urlpatterns = [
    path("", views.mes_articles, name="mes_articles"),
    path("nouveau/", views.creer_article, name="creer_article"),
    path("<int:pk>/annoter/", views.annoter_article, name="annoter_article"),
    path("<int:pk>/modifier/", views.modifier_article, name="modifier_article"),
    path("<int:pk>/soumettre/", views.soumettre_article, name="soumettre_article"),
    path("<int:pk>/", views.detail_article, name="detail_article"),
    path("<int:pk>/versions/creer/", views.creer_version_relecture, name="creer_version_relecture"),
    path("<int:pk>/annoter/<int:version_id>/", views.annoter_article, name="annoter_article_avec_version"),
    path("<int:pk>/versions/", views.liste_versions, name="liste_versions"),
    path("<int:pk>/versions/<int:version_id>/valider/", views.valider_version, name="valider_version"),
    path("<int:pk>/versions/<int:version_id>/rejeter/", views.rejeter_version, name="rejeter_version"),
    path("<int:pk>/versions/<int:version_id>/soumettre/", views.soumettre_version, name="soumettre_version"),
    path("<int:pk>/versions/<int:version_id>/supprimer/", views.supprimer_version, name="supprimer_version"),
    path("<int:pk>/comparer/", views.comparer_versions, name="comparer_versions"),
    path("<int:pk>/versions/<int:version_id>/modifier/", views.modifier_version, name="modifier_version"),
    path("<int:pk>/versions/<int:version_id>/pdf/", views.telecharger_pdf_version, name="telecharger_pdf_version"),
    path("<int:pk>/versions/<int:version_id>/devalider/", views.devalider_version, name="devalider_version"),
    path("<int:pk>/supprimer/", views.supprimer_article, name="supprimer_article"),
    path("<int:pk>/versions/creer/choix/", views.choisir_base_relecture, name="choisir_base_relecture"),
    path("proposer/", views.soumettre_article_public, name="soumettre_public"),
    path("merci-soumission/", views.merci_soumission, name="merci_soumission"),
    path("<int:pk>/ajouter-image/", views.ajouter_image, name="ajouter_image"),
    path("<int:pk>/annuler-validation-1/", views.annuler_validation_1, name="annuler_validation_1"),
]
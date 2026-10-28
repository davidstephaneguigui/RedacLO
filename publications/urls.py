from django.urls import path
from . import views

app_name = "publications"

urlpatterns = [
    path("", views.liste_publications, name="liste"),
    path("composition/", views.composition_numero, name="composition"),
    path("composition/utiliser/<int:pk>/", views.utiliser_article, name="utiliser_article"),
    path("composition/reserver/<int:pk>/", views.reserver_article, name="reserver_article"),
    path("composition/page/<int:page_id>/placer/<int:article_id>/", views.placer_article_page, name="placer_article_page"),
    path("composition/page/<int:page_id>/continuite/<int:article_id>/", views.modifier_continuite_article, name="modifier_continuite_article"),
    path("composition/page/<int:page_id>/retirer/<int:article_id>/", views.retirer_article_page, name="retirer_article_page"),
    path("composition/placer/<int:article_id>/", views.placer_article_page, name="placer_article_page"),
    path("composition/renvoyer-selection/", views.renvoyer_a_selection, name="renvoyer_a_selection"),
    path("composition/article/<int:article_id>/ordre/", views.changer_ordre_article, name="changer_ordre_article"),
    path("composition/page/<int:page_id>/article/<int:article_id>/ordre/", views.changer_ordre_article, name="changer_ordre_article"),
    path("organiser/<int:page_id>/", views.organiser_page, name="organiser_page"),
    path("organiser/", views.organiser_index, name="organiser_index"), # Route pour la vue globale (onglet du menu)
    path("organiser/<int:page_id>/", views.organiser_page, name="organiser_page"), # Route pour le clic sur une page spécifique
    path("cloturer/", views.cloturer_numero, name="cloturer_numero"),
    path("decloturer/<int:pk>/", views.decloturer_numero, name="decloturer_numero"),
    path("creer-numero/", views.creer_numero, name="creer_numero"),
    path("reprendre/<int:pk>/", views.reprendre_numero, name="reprendre_numero"),
    path("numeros/", views.liste_numeros, name="numeros"),
    path("archives/", views.archives_numeros, name="archives_numeros"),
    # Nouvelles routes pour la sélection
    path("choisir/", views.choisir, name="choisir"),
    path("reserves/", views.articles_reserves, name="articles_reserves"),
    path("<int:pk>/ajouter/", views.ajouter_au_numero, name="ajouter_au_numero"),
    path("<int:pk>/reserver/", views.reserver_article, name="reserver_article"),
    path("<int:pk>/annuler-validation/", views.annuler_validation, name="annuler_validation"),
    path("image/<int:image_id>/avis/", views.modifier_avis_image, name="modifier_avis_image"),
]

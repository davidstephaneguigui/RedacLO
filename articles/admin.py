from django.contrib import admin
from .models import Article, ArticleVersion
from .models import Annotation
from .models import Article, ArticleVersion, Annotation, Image # <-- Assure-toi que Image est importé


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("titre", "type_article", "redacteur", "statut", "date_modification")
    list_filter = ("statut", "type_article")
    search_fields = ("titre",)
    date_hierarchy = "date_creation"


@admin.register(ArticleVersion)
class ArticleVersionAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "numero",
        "type",
        "modifie_par",
        "parent",
        "statut",
        "date",
    )
    list_filter = ("type", "statut")
    search_fields = ("article__titre",)


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = (
        "article",
        "version",
        "redacteur", # <--- Vérifie bien le nom exact dans models.py (auteur ou redacteur)
        "type",
        "debut",
        "fin",
        "statut",
        "date_creation",
    )
    list_filter = ("type", "statut")
    search_fields = ("article__titre", "redacteur__username", "texte_propose") # <--- Vérifie ici aussi
    readonly_fields = ("date_creation", "date_decision")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("article", "legende", "taille", "est_prise_par_redacteur", "droits_ok") 
    list_filter = ("taille", "est_prise_par_redacteur", "droits_ok")
    search_fields = ("legende", "article__titre")
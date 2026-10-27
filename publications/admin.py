from django.contrib import admin
from .models import Publication, Page, Rubrique

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ("numero", "annee", "date", "date_creation")
    list_filter = ("statut", "annee")
    search_fields = ("numero", "annee")
    filter_horizontal = ("articles",)

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("numero_page", "publication", "rubrique", "total_signes", "limite_signes")
    list_filter = ("publication", "rubrique")
    search_fields = ("numero_page",)

    # On empêche l'édition des champs calculés comme total_signes
    readonly_fields = ("total_signes", "limite_signes")

@admin.register(Rubrique)
class RubriqueAdmin(admin.ModelAdmin):
    list_display = ("nom", "position", "publication")
    list_filter = ("publication",)
    ordering = ("position",)

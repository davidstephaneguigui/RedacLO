from django.contrib import admin
from .models import GabaritPage, TemplateIDML, TemplateLaTeX

# On crée des inlines pour pouvoir uploader les templates directement depuis la page du Gabarit
class TemplateIDMLInline(admin.StackedInline):
    model = TemplateIDML
    extra = 1

class TemplateLaTeXInline(admin.StackedInline):
    model = TemplateLaTeX
    extra = 1

@admin.register(GabaritPage)
class GabaritPageAdmin(admin.ModelAdmin):
    list_display = ('nom', 'nombre_colonnes')
    inlines = [TemplateIDMLInline, TemplateLaTeXInline]
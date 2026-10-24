from django.contrib import admin
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("article", "relecteur", "decision", "date")
    list_filter = ("decision",)
    search_fields = ("article__titre", "relecteur__username")

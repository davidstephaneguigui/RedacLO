from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
from .models import Invitation


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "couleur", "is_staff")
    list_filter = ("role", "couleur", "is_staff")
    fieldsets = UserAdmin.fieldsets + (
        ("Rôle et couleur", {"fields": ("role", "couleur")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rôle", {"fields": ("role",)}),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "date_creation", "date_expiration", "utilisee")
    list_filter = ("role", "utilisee")
    search_fields = ("email",)
    readonly_fields = ("token", "date_creation")
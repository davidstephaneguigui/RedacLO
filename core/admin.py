from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("destinataire", "type", "message_court", "lue", "date_creation")
    list_filter = ("type", "lue")
    search_fields = ("destinataire__username", "message")
    readonly_fields = ("date_creation", "date_lecture")
    date_hierarchy = "date_creation"

    def message_court(self, obj):
        return obj.message[:60] + "..." if len(obj.message) > 60 else obj.message
    message_court.short_description = "Message"
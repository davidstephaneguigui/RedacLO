from django.urls import path
from .views import exports

app_name = "display"

urlpatterns = [
    path("export/idml/<int:page_id>/", exports.telecharger_page_idml, name="export_idml"),
]
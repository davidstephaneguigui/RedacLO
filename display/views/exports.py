from django.shortcuts import get_object_or_404
from django.http import FileResponse
from accounts.decorators import role_required
from publications.models import Page
from ..services.export_idml import exporter_page_en_idml

@role_required("editeur", "admin")
def telecharger_page_idml(request, page_id):
    page = get_object_or_404(Page, pk=page_id)
    
    chemin_fichier = exporter_page_en_idml(page)
    
    fichier = open(chemin_fichier, 'rb')
    response = FileResponse(fichier, content_type='application/vnd.adobe.indesign-idml-package')
    response['Content-Disposition'] = f'attachment; filename="page_{page.numero_page}.idml"'
    
    return response
import os
from django.shortcuts import get_object_or_404
from django.http import FileResponse
from django.contrib import messages
from django.shortcuts import redirect
from accounts.decorators import role_required
from publications.models import Page
from ..services.export_idml import exporter_page_en_idml

@role_required("editeur", "admin")
def telecharger_page_idml(request, page_id):
    page = get_object_or_404(Page, pk=page_id)
    
    try:
        chemin_fichier = exporter_page_en_idml(page)
        response = FileResponse(open(chemin_fichier, 'rb'), content_type='application/vnd.adobe.indesign-idml-package')
        response['Content-Disposition'] = f'attachment; filename="page_{page.numero_page}.idml"'
        return response
    except Exception as e:
        messages.error(request, f"Erreur lors de l'export : {str(e)}")
        return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")
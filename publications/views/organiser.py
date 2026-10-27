from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import role_required
from ..models import Publication, Page
from display.models import GabaritPage

@role_required("editeur", "membre_redaction", "admin")
def organiser_page(request, page_id):
    page = get_object_or_404(Page, pk=page_id)
    gabarits = GabaritPage.objects.all()
    
    if request.method == "POST":
        gabarit_id = request.POST.get("gabarit")
        if gabarit_id:
            page.gabarit_id = gabarit_id
            page.save()
            messages.success(request, f"Le modèle de la page {page.numero_page} a été mis à jour.")
        else:
            page.gabarit = None
            page.save()
            messages.warning(request, f"Le modèle de la page {page.numero_page} a été retiré.")
            
        return redirect("publications:organiser_page", page_id=page.pk)
        
    return render(request, "publications/organiser.html", {
        "page": page,
        "gabarits": gabarits
    })

@role_required("editeur", "membre_redaction", "admin")
def organiser_index(request):
    numero_en_cours = Publication.objects.filter(statut="en_cours").first()
    if not numero_en_cours:
        messages.warning(request, "Aucun numéro en cours. Veuillez d'abord composer un numéro.")
        return redirect("publications:composition")
    
    pages = numero_en_cours.pages.all().order_by("numero_page")
    
    return render(request, "publications/organiser_index.html", {
        "numero": numero_en_cours,
        "pages": pages
    })
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from accounts.decorators import role_required
from ..models import Rubrique, Page

@role_required("editeur", "admin")
@require_POST
def gerer_rubrique_page(request, page_id):
    p = get_object_or_404(Page, pk=page_id)
    action = request.POST.get("action_rubrique")
    nom_rubrique = request.POST.get("nom_rubrique")
    numero_id = request.POST.get("numero_id")
    
    if not nom_rubrique:
        messages.error(request, "Le nom de la rubrique ne peut pas être vide.")
        return redirect(f"/publications/composition/?numero_id={numero_id}#page-{p.pk}")

    if action == "anniversaire":
        nouvelle_rub = Rubrique.objects.create(nom=nom_rubrique, publication=p.publication, position=99)
        p.rubrique = nouvelle_rub
        p.save()
        messages.success(request, f"Rubrique diverse « {nom_rubrique} » créée.")
    elif action == "modifier" and p.rubrique and p.rubrique.publication == p.publication:
        p.rubrique.nom = nom_rubrique
        p.rubrique.save()
        messages.success(request, f"Rubrique renommée.")
        
    return redirect(f"/publications/composition/?numero_id={numero_id}#page-{p.pk}")
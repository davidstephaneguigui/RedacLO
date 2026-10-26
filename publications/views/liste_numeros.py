from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from datetime import date, timedelta
from accounts.decorators import role_required
from ..models import Publication, Page

# On définit une date de référence pour la numérotation des publications
DATE_REFERENCE = date(2026, 10, 19)  # Lundi de la semaine 43 de l'année 2026 : numéro 3038.
NUMERO_REFERENCE = 3038

def numero_pour_semaine(d):
    """Retourne le numéro de publication correspondant à la semaine de la date d."""
    lundi = d - timedelta(days=d.weekday())
    nb_semaines = (lundi - DATE_REFERENCE).days // 7
    return NUMERO_REFERENCE + nb_semaines

def numero_semaine_actuelle():
    return numero_pour_semaine(date.today())


@role_required("editeur", "membre_redaction", "admin")
def liste_publications(request):
    return render(request, "publications/liste.html")


@role_required("editeur", "admin")
@require_POST
def cloturer_numero(request):
    numero = Publication.objects.filter(statut="en_cours").first()
    if numero:
        numero.statut = "publie"
        numero.save()
        prochain_num = numero.numero + 1
        pub_suivante = Publication.objects.filter(numero=prochain_num).first()
        if pub_suivante:
            pub_suivante.statut = "en_cours"
            pub_suivante.save()
            messages.success(request, f"Le numéro n°{numero.numero} a été clôturé. Le numéro n°{pub_suivante.numero} est maintenant en cours.")
        else:
            messages.warning(request, f"Le numéro n°{numero.numero} a été clôturé, mais le numéro n°{prochain_num} n'existe pas encore.")
    else:
        messages.error(request, "Aucun numéro en cours à clôturer.")
    return redirect("publications:composition")


@role_required("editeur", "admin")
@require_POST
def decloturer_numero(request, pk):
    publication = get_object_or_404(Publication, pk=pk)
    if publication.statut != "publie":
        messages.warning(request, "Ce numéro n'est pas publié.")
        return redirect("publications:numeros")

    prochain_num = publication.numero + 1
    pub_suivante = Publication.objects.filter(numero=prochain_num, statut="en_cours").first()

    if pub_suivante:
        pub_suivante.statut = "gele"
        pub_suivante.save()
        messages.info(request, f"Le numéro n°{pub_suivante.numero} a été repassé en 'Gelé'.")

    publication.statut = "en_cours"
    publication.save()
    messages.success(request, f"Le numéro n°{publication.numero} a été rouvert en cours.")
    return redirect("publications:numeros")


@role_required("editeur", "admin")
@require_POST
def creer_numero(request):
    dernier_num = Publication.objects.all().order_by('-numero').first()
    prochain_num = (dernier_num.numero + 1) if dernier_num else 3038
    
    nouvelle_pub = Publication.objects.create(
        numero=prochain_num,
        annee=2026, # À rendre dynamique plus tard
        statut="gele",
        date=timezone.localdate()
    )
    messages.success(request, f"Le numéro n°{prochain_num} a été créé (Gelé). Vous pouvez maintenant y placer des articles.")
    return redirect(f"/publications/composition/?numero_id={nouvelle_pub.pk}")


@role_required("editeur", "admin")
@require_POST
def reprendre_numero(request, pk):
    pub_cible = get_object_or_404(Publication, pk=pk)
    if pub_cible.statut == "en_cours":
        messages.warning(request, "Ce numéro est déjà en cours.")
        return redirect(f"/publications/composition/?numero_id={pub_cible.pk}")

    ancien_en_cours = Publication.objects.filter(statut="en_cours").first()
    if ancien_en_cours:
        ancien_en_cours.statut = "gele"
        ancien_en_cours.save()
        messages.info(request, f"Le numéro n°{ancien_en_cours.numero} a été gelé.")

    pub_cible.statut = "en_cours"
    pub_cible.save()
    messages.success(request, f"Le numéro n°{pub_cible.numero} est maintenant en cours de bouclage.")
    return redirect(f"/publications/composition/?numero_id={pub_cible.pk}")


@role_required("editeur", "admin")
def liste_numeros(request):
    num_central = Publication.objects.filter(statut="en_cours").first()
    num_ref = num_central.numero if num_central else numero_semaine_actuelle()
    
    min_num = num_ref - 4
    max_num = num_ref + 4
    
    publications = Publication.objects.filter(
        numero__gte=min_num, 
        numero__lte=max_num
    ).order_by('numero')
    
    return render(request, "publications/liste_numeros.html", {
        "publications": publications,
        "num_semaine": numero_semaine_actuelle(),
        "min_num": min_num,
        "max_num": max_num,
    })


@role_required("editeur", "admin")
def archives_numeros(request):
    num_central = Publication.objects.filter(statut="en_cours").first()
    num_ref = num_central.numero if num_central else numero_semaine_actuelle()
    
    max_num = num_ref - 5
    publications = Publication.objects.filter(
        numero__lte=max_num
    ).order_by('-numero')
    
    return render(request, "publications/archives_numeros.html", {
        "publications": publications,
        "num_semaine": numero_semaine_actuelle(),
    })
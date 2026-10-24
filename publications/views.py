from django.shortcuts import render
from accounts.decorators import role_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Max
from django.http import JsonResponse
from accounts.decorators import role_required
from .models import Publication, Page, Rubrique, GabaritPage
from articles.models import Article
from datetime import date, timedelta


@role_required("editeur", "membre_redaction", "admin")
def liste_publications(request):
    return render(request, "publications/liste.html")


@role_required("editeur", "admin")
def composition_numero(request):
    # 1. On récupère ou crée le numéro en cours
    numero_en_cours = Publication.objects.filter(statut="en_cours").first()
    if not numero_en_cours:
        numero_en_cours = Publication.objects.create(
            numero=Publication.prochain_numero(), 
            volume=1, 
            statut="en_cours", 
            date=timezone.localdate()
        )
    
    # 2. Génération des 16 pages si vides
    if numero_en_cours.pages.count() == 0:
        for i in range(1, 17):
            Page.objects.create(publication=numero_en_cours, numero_page=i)

    # 3. TRAITEMENT DU FORMULAIRE (Illustrations ET Rubrique)
    page_id = request.GET.get("page_id")
    petites = request.GET.get("petites")
    grandes = request.GET.get("grandes")
    rubrique = request.GET.get("rubrique")
    
    if page_id and (petites is not None or grandes is not None or rubrique is not None):
        p = Page.objects.filter(pk=page_id).first()
        if p:
            val_p = int(petites) if petites else 0
            val_g = int(grandes) if grandes else 0
            
            # Contrainte : max 3 au total ET max 2 grandes
            if val_p + val_g > 3 or val_g > 2:
                messages.error(request, f"Règles non respectées pour la page {p.numero_page} : maximum 3 illustrations au total, dont 2 grandes maximum.")
            else:
                p.petites_illustrations = val_p
                p.grandes_illustrations = val_g
                
                # NOUVEAU : Sauvegarde de la rubrique
                if rubrique:
                    p.rubrique_id = rubrique
                else:
                    p.rubrique = None
                
                p.save()
                messages.success(request, f"Paramètres mis à jour pour la page {p.numero_page}.")
            
            return redirect("publications:composition")
    
    # 4. Affichage normal
    pages = numero_en_cours.pages.all().order_by("numero_page")
    
    articles_disponibles = Article.objects.filter(
        statut_selection="disponible"
    ).exclude(
        pages__publication=numero_en_cours
    ).order_by('-date_modification')

    # --- CALCUL DES COMPTEURS DE SIGNES ---
    capacite_totale = sum(page.limite_signes() for page in pages)
    signes_places = sum(page.total_signes() for page in pages)
    signes_restants = capacite_totale - signes_places
    
    signes_vivier = 0
    for article in articles_disponibles:
        version = article.versions.filter(statut="validee").first()
        if version:
            signes_vivier += version.nombre_signes()

    # --- CALCUL DE LA SEMAINE ---
    aujourd_hui = date.today()
    lundi = aujourd_hui - timedelta(days=aujourd_hui.weekday())
    vendredi = lundi + timedelta(days=4)
    numero_semaine = aujourd_hui.isocalendar()[1]

    MOIS_FR = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    mois_lundi = MOIS_FR[lundi.month]
    mois_vendredi = MOIS_FR[vendredi.month]

    if lundi.month == vendredi.month:
        dates_semaine = f"du {lundi.day} au {vendredi.day} {mois_lundi} {lundi.year}"
    else:
        dates_semaine = f"du {lundi.day} {mois_lundi} au {vendredi.day} {mois_vendredi} {vendredi.year}"

    # --- RUBRIQUES ---
    rubriques = Rubrique.objects.all().order_by('position')

    return render(request, "publications/composition.html", {
        "numero": numero_en_cours,
        "pages": pages,
        "articles": articles_disponibles,
        "numero_semaine": numero_semaine,
        "dates_semaine": dates_semaine,
        "capacite_totale": capacite_totale,
        "signes_places": signes_places,
        "signes_restants": signes_restants,
        "signes_vivier": signes_vivier,
        "rubriques": rubriques,
    })


@role_required("editeur", "membre_redaction")
def utiliser_article(request, pk):
    """Ajoute un article au numéro en cours."""
    if request.method == "POST":
        article = get_object_or_404(Article, pk=pk)
        numero = Publication.objects.filter(statut="en_cours").first()
        
        if numero:
            numero.articles.add(article)
            article.statut_selection = "utilise"
            article.save()
            messages.success(request, f"L'article « {article.titre} » a été ajouté au numéro en cours.")
        else:
            messages.error(request, "Aucun numéro en cours n'a été trouvé.")
            
    return redirect("publications:composition")


@role_required("editeur", "membre_redaction")
def reserver_article(request, pk):
    """Réserve un article pour un numéro futur."""
    if request.method == "POST":
        article = get_object_or_404(Article, pk=pk)
        article.statut_selection = "reserve"
        article.save()
        messages.success(request, f"L'article « {article.titre} » a été réservé.")
            
    return redirect("publications:composition")


@role_required("editeur", "admin")
def placer_article_page(request, article_id):
    article = get_object_or_404(Article, pk=article_id)
    
    if request.method == "POST":
        page_id = request.POST.get("page_id")
        
        if not page_id:
            messages.error(request, "Veuillez choisir une page.")
            return redirect("publications:composition")
            
        page = get_object_or_404(Page, pk=page_id)
        
        # --- VÉRIFICATION DES SIGNES AVEC TOLÉRANCE ---
        version = article.versions.filter(statut="validee").first()
        signes_nouvel_article = version.nombre_signes() if version else 0
        
        limite = page.limite_signes()
        
        # On ajoute une tolérance de 100 signes pour laisser une marge de manœuvre (ex: réduire une image)
        TOLERANCE = 100
        limite_avec_tolerance = limite + TOLERANCE
        
        total_apres_ajout = page.total_signes() + signes_nouvel_article
        
        if total_apres_ajout > limite_avec_tolerance:
            deficit = total_apres_ajout - limite
            messages.error(
                request, 
                f"Impossible de placer cet article : la page {page.numero_page} dépasserait sa limite de {limite} signes de {deficit} signes. "
                f"Astuce : Modifiez le nombre ou la taille des illustrations sur cette page pour augmenter sa capacité."
            )
            return redirect("publications:composition")

        # --- NOUVEAU : On définit l'ordre à la fin de la page ---
        from django.db.models import Max
        dernier_ordre = page.articles.aggregate(Max('ordre_sur_page'))['ordre_sur_page__max'] or 0
        article.ordre_sur_page = dernier_ordre + 1
        
        # --- SI TOUT EST BON, ON AJOUTE ---
        page.articles.add(article)
        page.publication.articles.add(article)
        article.statut_selection = "utilise"
        article.save()
        
        messages.success(request, f"L'article « {article.titre} » a été placé en page {page.numero_page}.")
        
    return redirect("publications:composition")


@role_required("editeur", "admin")
@require_POST
def changer_ordre_article(request, page_id, article_id):
    page = get_object_or_404(Page, pk=page_id)
    article = get_object_or_404(Article, pk=article_id)
    nouvel_ordre = int(request.POST.get("ordre", 1))
    
    # On s'assure que l'ordre demandé est valide (au moins 1)
    if nouvel_ordre < 1:
        nouvel_ordre = 1

    # 1. On récupère tous les articles de la page, triés par ordre actuel
    articles_page = list(page.articles_tries())
    
    # 2. On retire temporairement l'article modifié de la liste
    if article in articles_page:
        articles_page.remove(article)
    
    # 3. On réinsère l'article à la nouvelle position (index = nouvel_ordre - 1)
    # (Si on demande la position 1, on l'insère à l'index 0)
    index_insertion = min(nouvel_ordre - 1, len(articles_page))
    articles_page.insert(index_insertion, article)
    
    # 4. On réassigne les ordres de 1 à N pour tout le monde
    for i, a in enumerate(articles_page):
        a.ordre_sur_page = i + 1
        a.save()
        
    return JsonResponse({'status': 'success'})


@role_required("editeur", "admin")
def retirer_article_page(request, page_id, article_id):
    page = get_object_or_404(Page, pk=page_id)
    article = get_object_or_404(Article, pk=article_id)
    
    if request.method == "POST":
        page.articles.remove(article)
        article.ordre_sur_page = 0 # On le retire
        article.save()
        
        # --- NOUVEAU : On renumérote les articles restants pour boucher les trous ---
        articles_restants = page.articles.all().order_by('ordre_sur_page')
        for index, art in enumerate(articles_restants):
            art.ordre_sur_page = index + 1
            art.save()
        # -----------------------------------------------------------------------------

        # On vérifie s'il est sur une autre page de ce même numéro
        autres_pages = page.publication.pages.filter(articles=article).exists()
        
        if not autres_pages:
            article.statut_selection = "disponible"
            article.save()
            page.publication.articles.remove(article)
            
        messages.success(request, f"L'article a été retiré de la page {page.numero_page}.")
        
    return redirect("publications:composition")


@role_required("editeur", "membre_redaction", "admin")
def renvoyer_a_selection(request):
    """Retire des articles de la page et les renvoie vers Choisir ou Réserver."""
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        action = request.POST.get("action", "renvoyer") # Par défaut, on renvoie vers Choisir
        
        if not article_ids:
            messages.warning(request, "Aucun article n'a été sélectionné.")
            return redirect("publications:composition")

        articles = Article.objects.filter(pk__in=article_ids)
        count = articles.count()

        for article in articles:
            # 1. On le retire de toutes les pages où il se trouve
            article.pages.clear()
            
            # 2. On change son statut selon l'action choisie
            if action == "reserver":
                article.statut_selection = "reserve"
            else:
                article.statut_selection = "a_choisir"
            article.save()

        if action == "reserver":
            messages.success(request, f"{count} article(s) ont été réservés pour les prochains numéros.")
        else:
            messages.success(request, f"{count} article(s) ont été renvoyés vers la page de sélection.")
        
    return redirect("publications:composition")


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



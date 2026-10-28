from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Max, Q
from datetime import date, timedelta
from accounts.decorators import role_required
from ..models import Publication, Page, Rubrique, PageArticle
from articles.models import Article
from .. import services
from .liste_numeros import numero_semaine_actuelle
from articles.models import Image

@role_required("editeur", "admin")
def composition_numero(request):
    num_semaine = numero_semaine_actuelle()
    numero_id = request.GET.get("numero_id")

    if numero_id:
        numero_en_cours = Publication.objects.filter(pk=numero_id).first()
        if not numero_en_cours:
            messages.error(request, "Ce numéro n'existe pas.")
            return redirect("publications:composition")
    else:
        numero_en_cours = Publication.objects.filter(statut="en_cours").first()
        if not numero_en_cours:
            numero_en_cours = Publication.objects.filter(numero=num_semaine).first()
        if not numero_en_cours:
            numero_en_cours = Publication.objects.create(
                numero=num_semaine,
                annee=2026,
                statut="en_cours",
                date=timezone.localdate()
            )
        elif numero_en_cours.statut == "gele":
            numero_en_cours.statut = "en_cours"
            numero_en_cours.save()

    lecture_seule = (numero_en_cours.statut == "publie")

    if numero_en_cours.pages.count() == 0 and numero_en_cours.statut != "publie":
        for i in range(1, 17):
            Page.objects.create(publication=numero_en_cours, numero_page=i)

    # Actions spéciales Rubriques (désormais gérées dans rubriques.py, on garde la redirection si le form GET est soumis)
    action_rubrique = request.GET.get("action_rubrique")
    page_id = request.GET.get("page_id")
    nom_rubrique = request.GET.get("nom_rubrique")

    if lecture_seule and action_rubrique and page_id:
        messages.error(request, "Ce numéro est clôturé et ne peut plus être modifié.")
        return redirect(f"/publications/composition/?numero_id={numero_en_cours.pk}#page-{page_id}")

    # Formulaire classique
    petites = request.GET.get("petites")
    grandes = request.GET.get("grandes")
    rubrique = request.GET.get("rubrique")

    if lecture_seule and page_id and (petites is not None or grandes is not None or rubrique is not None):
        messages.error(request, "Ce numéro est clôturé et ne peut plus être modifié.")
        return redirect(f"/publications/composition/?numero_id={numero_en_cours.pk}#page-{page_id}")

    if page_id and (petites is not None or grandes is not None or rubrique is not None):
        p = Page.objects.filter(pk=page_id).first()
        if p:
            val_p = int(petites) if petites else 0
            val_g = int(grandes) if grandes else 0

            if val_p + val_g > 3 or val_g > 2:
                messages.error(request, f"Règles non respectées pour la page {p.numero_page} : maximum 3 illustrations au total, dont 2 grandes maximum.")
            else:
                p.petites_illustrations = val_p
                p.grandes_illustrations = val_g
                if rubrique:
                    p.rubrique_id = rubrique
                else:
                    p.rubrique = None
                p.save()
                messages.success(request, f"Paramètres mis à jour pour la page {p.numero_page}.")
            return redirect(f"/publications/composition/?numero_id={numero_en_cours.pk}&page_id={p.pk}#page-{p.pk}")

    # Affichage normal
    pages = numero_en_cours.pages.all().order_by("numero_page")
    services.equilibrer_doubles_pages(numero_en_cours)

    articles_disponibles = Article.objects.filter(
        Q(statut_selection="disponible") | 
        Q(placements__page__publication=numero_en_cours, placements__est_fin=False)
    ).distinct().order_by('-date_modification')

    capacite_totale = sum(page.limite_signes() for page in pages)
    signes_places = sum(page.total_signes() for page in pages)
    signes_restants = capacite_totale - signes_places

    signes_vivier = 0
    for article in articles_disponibles:
        if not PageArticle.objects.filter(article=article, page__publication=numero_en_cours).exists():
            version = article.version_courante()
            if version:
                signes_vivier += version.nombre_signes()

    date_ref_lundi = date(2026, 10, 19)
    decalage_semaines = numero_en_cours.numero - 3038
    lundi = date_ref_lundi + timedelta(weeks=decalage_semaines)
    vendredi = lundi + timedelta(days=4)
    numero_semaine = lundi.isocalendar()[1]
    annee_affichage = lundi.year

    MOIS_FR = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    mois_lundi = MOIS_FR[lundi.month]
    mois_vendredi = MOIS_FR[vendredi.month]

    if lundi.month == vendredi.month:
        dates_semaine = f"du {lundi.day} au {vendredi.day} {mois_lundi} {annee_affichage}"
    else:
        dates_semaine = f"du {lundi.day} {mois_lundi} au {vendredi.day} {mois_vendredi} {annee_affichage}"

    rubriques_recurrentes = Rubrique.objects.filter(publication__isnull=True).order_by('position')
    rubriques_diverses = Rubrique.objects.filter(publication=numero_en_cours).order_by('position')

    return render(request, "publications/composition.html", {
        "numero": numero_en_cours,
        "pages": pages,
        "articles": articles_disponibles,
        "rubriques_recurrentes": rubriques_recurrentes,
        "rubriques_diverses": rubriques_diverses,
        "numero_semaine": numero_semaine,
        "dates_semaine": dates_semaine,
        "capacite_totale": capacite_totale,
        "signes_places": signes_places,
        "signes_restants": signes_restants,
        "signes_vivier": signes_vivier,
        "lecture_seule": lecture_seule,
        "num_semaine": num_semaine,
    })

@role_required("editeur", "membre_redaction")
def utiliser_article(request, pk):
    if request.method == "POST":
        article = get_object_or_404(Article, pk=pk)
        numero = Publication.objects.filter(statut="en_cours").first()
        if numero:
            article.statut_selection = "utilise"
            article.save()
            messages.success(request, f"L'article « {article.titre} » a été ajouté au numéro en cours.")
        else:
            messages.error(request, "Aucun numéro en cours n'a été trouvé.")
    return redirect("publications:composition")

@role_required("editeur", "membre_redaction")
def reserver_article(request, pk):
    if request.method == "POST":
        article = get_object_or_404(Article, pk=pk)
        article.statut_selection = "reserve"
        article.save()
        messages.success(request, f"L'article « {article.titre} » a été réservé.")
    return redirect("publications:composition")

@role_required("editeur", "admin")
def placer_article_page(request, article_id):
    if request.method == "POST":
        page_id = request.POST.get("page_id")
        article = get_object_or_404(Article, pk=article_id)
        page = get_object_or_404(Page, pk=page_id)

        # NOUVELLE SÉCURITÉ : Page 2 réservée aux éditoriaux
        if page.numero_page == 2 and article.type_article != "article_editorial":
            messages.error(request, "La page 2 est réservée exclusivement aux articles de type 'Éditorial'.")
            return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")
        
        # On regarde si l'article a un placement OUVERT dans ce numéro
        placement_ouvert = PageArticle.objects.filter(
            article=article, 
            page__publication=page.publication, 
            est_fin=False
        ).first()

        # On regarde aussi s'il a un placement FERMÉ
        placement_ferme = PageArticle.objects.filter(
            article=article, 
            page__publication=page.publication, 
            est_fin=True
        ).first()

        # --- CAS 1 : C'EST UNE CONTINUATION ---
        if placement_ouvert:
            # Règle de parité : pas de débordement depuis une page impaire
            if placement_ouvert.page.numero_page % 2 != 0:
                messages.error(request, "Impossible de faire déborder un article d'une page impaire.")
                return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")

            # Règle de la page suivante immédiate
            if page.numero_page != placement_ouvert.page.numero_page + 1:
                messages.error(request, f"Un article en cours de débordement doit être placé sur la page {placement_ouvert.page.numero_page + 1}.")
                return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")

            # Calcul des signes
            total_art = article.version_courante().nombre_signes() if article.version_courante() else 0
            autres_signes = 0
            for pa in placement_ouvert.page.articles_lies.all():
                if pa.article_id != article.id:
                    if pa.signes_sur_page is not None:
                        autres_signes += pa.signes_sur_page
                    elif pa.article.version_courante():
                        autres_signes += pa.article.version_courante().nombre_signes()
            
            place_dispo = placement_ouvert.page.limite_signes() - autres_signes
            signes_prec = min(max(0, place_dispo), total_art)
            
            # On ferme la page précédente
            placement_ouvert.signes_sur_page = signes_prec
            placement_ouvert.est_fin = True
            placement_ouvert.save()
            
            est_un_debut = False
            signes_cette_page = total_art - signes_prec

        # --- CAS 2 : L'ARTICLE EST DÉJÀ PLACÉ ET FINI ---
        elif placement_ferme:
            messages.error(request, f"Cet article est déjà terminé sur la page {placement_ferme.page.numero_page}.")
            return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")

        # --- CAS 3 : NOUVEAU PLACEMENT NORMAL ---
        else:
            est_un_debut = True
            signes_cette_page = None # Prendra toute la place disponible

        # Création du placement sur la nouvelle page
        max_pos = PageArticle.objects.filter(page=page).aggregate(Max('position'))['position__max']
        nouvelle_pos = (max_pos or 0) + 1
        
        PageArticle.objects.create(
            page=page, 
            article=article, 
            position=nouvelle_pos,
            est_debut=est_un_debut,
            est_fin=True, 
            signes_sur_page=signes_cette_page
        )
        
        article.statut_selection = "utilise"
        article.save()
        messages.success(request, f"L'article a été placé sur la page {page.numero_page}.")
            
    return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")

@role_required("editeur", "admin")
@require_POST
def modifier_continuite_article(request, page_id, article_id):
    placement = get_object_or_404(PageArticle, page_id=page_id, article_id=article_id)
    champ = request.POST.get("champ")
    if champ == "debut":
        placement.est_debut = not placement.est_debut
    elif champ == "fin":
        placement.est_fin = not placement.est_fin
        
    placement.save()
    return redirect(f"/publications/composition/?numero_id={placement.page.publication.pk}#page-{page_id}")

@role_required("editeur", "admin")
@require_POST
def changer_ordre_article(request, page_id, article_id):
    nouvelle_pos = int(request.POST.get("ordre"))
    placements = list(PageArticle.objects.filter(page_id=page_id).order_by('position'))
    placement_actuel = next((p for p in placements if p.article_id == article_id), None)
    
    if placement_actuel:
        placements.remove(placement_actuel)
        nouvelle_pos = max(1, min(nouvelle_pos, len(placements) + 1))
        placements.insert(nouvelle_pos - 1, placement_actuel)
        
        for index, p in enumerate(placements):
            p.position = index + 1
            p.save()
            
        return redirect(f"/publications/composition/?numero_id={placement_actuel.page.publication.pk}#page-{page_id}")

    page = get_object_or_404(Page, pk=page_id)
    return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page_id}")

@role_required("editeur", "admin")
@require_POST
def retirer_article_page(request, page_id, article_id):
    page = get_object_or_404(Page, pk=page_id)
    article = get_object_or_404(Article, pk=article_id)
    placement = PageArticle.objects.filter(page=page, article=article).first()
    
    if placement:
        placement.delete()
        article.statut_selection = "disponible"
        article.save()
        messages.success(request, f"L'article a été retiré de la page {page.numero_page}.")
        
    return redirect(f"/publications/composition/?numero_id={page.publication.pk}#page-{page.pk}")

@role_required("editeur", "membre_redaction", "admin")
def renvoyer_a_selection(request):
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        action = request.POST.get("action", "renvoyer")
        
        if not article_ids:
            messages.warning(request, "Aucun article n'a été sélectionné.")
            return redirect("publications:composition")

        articles = Article.objects.filter(pk__in=article_ids)
        count = articles.count()

        for article in articles:
            # On le retire de toutes les pages où il se trouve (le nouveau système !)
            PageArticle.objects.filter(article=article).delete()
            
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

@role_required("editeur", "admin")
@require_POST
def modifier_avis_image(request, image_id):
    image = get_object_or_404(Image, pk=image_id)
    nouvel_avis = request.POST.get("avis")
    commentaire = request.POST.get("commentaire", "").strip()

    if nouvel_avis in ["favorable", "defavorable", "a_remplacer"]:
        image.avis_editeur = nouvel_avis
        if commentaire:
            image.commentaire_editeur = commentaire
        image.save()
        messages.success(request, f"L'avis sur l'image de « {image.article.titre} » a été mis à jour.")
    else:
        messages.error(request, "Avis invalide.")

    # On redirige vers la page d'où l'on vient (le Chemin de fer)
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect("publications:composition")
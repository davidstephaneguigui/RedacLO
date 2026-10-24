from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Case, When, IntegerField, Q
from django.core.paginator import Paginator

from accounts.decorators import role_required
from accounts.models import User
from articles.models import Article

from .forms import ReviewForm
from .models import Review
from core.utils import creer_notification


@role_required("editeur", "membre_redaction", "admin")
def a_relire(request):
    est_archive = request.GET.get('archives') == '1'
    
    if est_archive:
        articles = Article.objects.filter(statut="rejete")
    else:
        articles = Article.objects.filter(statut__in=["soumis", "en_relecture", "relu", "valide_1_fois"])

    articles = articles.annotate(
        nb_relectures=Count('versions', filter=Q(versions__type='relecture', versions__statut__in=['soumise', 'validee']))
    )

    # --- NOUVELLE LOGIQUE DE TRI INDÉPENDANT ---
    tri_statut = request.GET.get('tri_statut', '')
    tri_date = request.GET.get('tri_date', '-date') # Date par défaut
    tri_relectures = request.GET.get('tri_relectures', '')
    
    ordre_statut = Case(
        When(statut='soumis', then=0),
        When(statut='en_relecture', then=1),
        When(statut='relu', then=2),
        When(statut='valide_1_fois', then=3),
        default=4,
        output_field=IntegerField(),
    )
    
    criteres = []
    
    # On ajoute le tri par statut s'il est demandé
    if tri_statut == 'asc':
        criteres.append(ordre_statut)
    elif tri_statut == 'desc':
        criteres.append(ordre_statut.desc())

    # On ajoute le tri par date s'il est demandé
    if tri_date == 'asc':
        criteres.append('date_modification')
    elif tri_date == 'desc':
        criteres.append('-date_modification')

    # On ajoute le tri par relectures s'il est demandé
    if tri_relectures == 'asc':
        criteres.append('nb_relectures')
    elif tri_relectures == 'desc':
        criteres.append('-nb_relectures')
        
    # Si aucun critère n'est sélectionné (ou juste l'option vide), on met la date par défaut
    if not criteres:
        criteres.append('-date_modification')

    articles = articles.order_by(*criteres)

    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # Préparation de l'avis actuel
    for article in page_obj:
        if article.statut == "relu":
            version = article.versions.filter(type="relecture").exclude(statut="brouillon").last()
            if version:
                article.avis_actuel = version.avis_relecteur

    return render(request, "reviews/a_relire.html", {
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'est_archive': est_archive,
        'tri_statut': tri_statut,
        'tri_date': tri_date,
        'tri_relectures': tri_relectures,
    })


@role_required("editeur", "membre_redaction", "admin")
def deposer_review(request, review_pk):
    review = get_object_or_404(Review, pk=review_pk)

    # Seul le relecteur assigné (ou un admin) peut déposer
    if review.relecteur != request.user and not request.user.is_superuser:
        raise PermissionDenied

    # Une review déjà déposée n'est plus modifiable
    if review.decision != "en_attente":
        return render(request, "reviews/review_verrouillee.html", {"review": review})

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()

            # Notifier les éditeurs
            editeurs = User.objects.filter(role__in=["editeur", "admin"])
            for editeur in editeurs:
                creer_notification(
                    destinataire=editeur,
                    type="annotation_creee",
                    message=(
                        f"Une relecture a été déposée pour l'article "
                        f"« {review.article.titre} » par "
                        f"{review.relecteur.username} "
                        f"({review.get_decision_display().lower()})."
                    ),
                    lien=f"/articles/{review.article.pk}/",
                    emetteur=request.user,
                )

            return redirect("articles:detail_article", pk=review.article.pk)
    else:
        form = ReviewForm(instance=review)

    return render(request, "reviews/deposer_review.html", {
        "form": form,
        "review": review,
    })
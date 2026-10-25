from django.shortcuts import render
from django.db.models import Count, Case, When, IntegerField, Q
from django.core.paginator import Paginator

from accounts.decorators import role_required
from articles.models import Article

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

    # --- LOGIQUE DE TRI INDÉPENDANT ---
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
    
    if tri_statut == 'asc':
        criteres.append(ordre_statut)
    elif tri_statut == 'desc':
        criteres.append(ordre_statut.desc())

    if tri_date == 'asc':
        criteres.append('date_modification')
    elif tri_date == 'desc':
        criteres.append('-date_modification')

    if tri_relectures == 'asc':
        criteres.append('nb_relectures')
    elif tri_relectures == 'desc':
        criteres.append('-nb_relectures')
        
    if not criteres:
        criteres.append('-date_modification')

    articles = articles.order_by(*criteres)

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
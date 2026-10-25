from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from core.utils import creer_notification
from core.models import Notification
from ..forms import ArticleForm, ImageForm, ImageFormSet
from ..models import Article, ArticleVersion

User = get_user_model()

@role_required("redacteur")
def creer_article(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES)
  
        if form.is_valid() and formset.is_valid():
            article = form.save(commit=False)
            article.redacteur = request.user
            article.statut = "brouillon"
            article.save()

            version = ArticleVersion.creer(
                article=article,
                contenu=article.contenu,
                modifie_par=request.user,
                parent=None,
                type="auteur",
                commentaire="Version initiale.",
            )
            article.version_reference = version
            article.save()

            formset.instance = article
            formset.save()

            return redirect("articles:mes_articles")
    else:
        form = ArticleForm()
        formset = ImageFormSet()

    return render(request, "articles/article_form.html", {
        "form": form,
        "formset": formset,
        "titre": "Nouvel article",
    })

@login_required
def mes_articles(request):
    articles = Article.objects.filter(redacteur=request.user)

    tris_autorises = {
        'statut': 'statut',
        '-statut': '-statut',
        'date': 'date_modification',
        '-date': '-date_modification',
    }
    tri = request.GET.get('tri', '-date')
    if tri not in tris_autorises:
        tri = '-date'
    articles = articles.order_by(tris_autorises[tri])

    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'articles/mes_articles.html', {
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'tri_courant': tri,
    })

@role_required("redacteur")
def detail_article(request, pk):
    article = get_object_or_404(Article, pk=pk)

    if request.user.role == "redacteur" and article.redacteur != request.user:
        raise PermissionDenied

    version_validee = article.versions.filter(statut="validee").first()
    if version_validee:
        texte_brut = version_validee.contenu
        source_texte = "version validée"
    elif article.version_reference:
        texte_brut = article.version_reference.contenu
        source_texte = "version de référence"
    else:
        texte_brut = article.contenu
        source_texte = "texte original"

    texte_affiche = [p.strip() for p in texte_brut.splitlines() if p.strip()]
    reviews = article.reviews.exclude(decision="en_attente")

    return render(request, "articles/article_detail.html", {
        "article": article,
        "reviews": reviews,
        "texte_affiche": texte_affiche,
        "source_texte": source_texte,
        "version_validee": version_validee,
    })

@role_required("redacteur")
def modifier_article(request, pk):
    article = get_object_or_404(Article, pk=pk, redacteur=request.user)

    if article.statut != "brouillon" and not request.user.is_superuser:
        return render(request, "articles/article_verrouille.html", {"article": article})

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save()

            version = article.version_reference
            if version:
                version.contenu = article.contenu
                version.commentaire = "Modification par le rédacteur."
                version.save()

            return redirect("articles:mes_articles")
    else:
        form = ArticleForm(instance=article)

    return render(request, "articles/article_form.html", {
        "form": form,
        "titre": "Modifier l'article",
    })

@role_required("editeur", "membre_redaction", "admin")
@require_POST
def supprimer_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if request.user.role == "admin":
        titre = article.titre
        article.delete()
        messages.success(request, f"L'article « {titre} » a été supprimé définitivement par l'administrateur.")
        return redirect("reviews:a_relire")

    if article.redacteur != request.user:
        raise PermissionDenied
        
    if article.statut != "brouillon":
        messages.error(request, "Vous ne pouvez supprimer qu'un article en brouillon.")
        return redirect("articles:mes_articles")
        
    article.delete()
    messages.success(request, f"L'article « {article.titre} » a été supprimé.")
    return redirect("articles:mes_articles")

@role_required("redacteur")
def ajouter_image(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if article.redacteur != request.user and request.user.role not in ("editeur", "admin"):
        raise PermissionDenied

    if request.method == "POST":
        form = ImageForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.article = article
            image.save()
            messages.success(request, "L'image a bien été ajoutée.")
            return redirect("articles:detail_article", pk=article.pk)
    else:
        form = ImageForm()

    return render(request, "articles/ajouter_image.html", {
        "article": article,
        "form": form,
    })

@role_required("redacteur")
@require_POST
def soumettre_article(request, pk):
    article = get_object_or_404(Article, pk=pk, redacteur=request.user)

    if article.statut == "brouillon":
        article.statut = "soumis"

        version = ArticleVersion.creer(
            article=article,
            contenu=article.contenu,
            modifie_par=request.user,
            parent=article.version_reference,
            type="auteur",
            commentaire="Version soumise.",
        )
        version.statut = "soumise"
        version.save()
        article.version_reference = version
        article.save()

        editeurs = User.objects.filter(role__in=["editeur", "admin"])
        for editeur in editeurs:
            creer_notification(
                destinataire=editeur,
                type="article_soumis",
                message=f"L'article « {article.titre} » a été soumis par {request.user.username}.",
                lien=f"/articles/{article.pk}/",
                emetteur=request.user,
            )
        
        messages.success(request, "Votre article a bien été soumis.")

    return redirect("articles:mes_articles")

@role_required("redacteur")
@require_POST
def annuler_soumission(request, pk):
    article = get_object_or_404(Article, pk=pk, redacteur=request.user)
    
    if article.statut == "soumis":
        version_soumise = article.version_reference
        if version_soumise and version_soumise.type == "auteur" and version_soumise.statut == "soumise":
            if not version_soumise.enfants.exists():
                version_soumise.delete()
        
        v_brouillon = article.versions.filter(type="auteur", statut="brouillon").order_by("-numero").first()
        if v_brouillon:
            article.version_reference = v_brouillon
        
        article.statut = "brouillon"
        article.save()
        
        Notification.objects.filter(
            type="article_soumis",
            lien=f"/articles/{article.pk}/",
            emetteur=request.user
        ).delete()
        
        messages.success(request, "La soumission a été annulée. L'article est de retour en brouillon.")
        
    return redirect("articles:mes_articles")
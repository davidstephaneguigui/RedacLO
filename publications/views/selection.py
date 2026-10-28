from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from articles.models import Article
from ..models import Publication

@role_required("editeur", "admin")
def choisir(request):
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        action = request.POST.get("action")
        
        if article_ids:
            if action == "reserver":
                Article.objects.filter(pk__in=article_ids).update(statut_selection="reserve")
                messages.success(request, f"{len(article_ids)} article(s) ont été réservés pour les numéros suivants.")
                return redirect("publications:articles_reserves")
            
            elif action == "ajouter":
                Article.objects.filter(pk__in=article_ids).update(statut_selection="disponible")
                messages.success(request, f"{len(article_ids)} article(s) ont été ajoutés au vivier de composition.")
                return redirect("publications:composition")
                
        return redirect("publications:choisir")

    articles = Article.objects.filter(
        statut="valide",
        statut_selection="a_choisir"
    ).order_by('-date_modification')
    
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    numero_en_cours = Publication.objects.filter(statut="en_cours").first()
    
    return render(request, "publications/choisir.html", {
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'numero_en_cours': numero_en_cours,
    })

@role_required("editeur", "admin")
def articles_reserves(request):
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        action = request.POST.get("action", "remettre")
        
        if article_ids:
            if action == "ajouter":
                numero_id = request.POST.get("numero_id")
                
                if numero_id:
                    numero_cible = Publication.objects.filter(pk=numero_id).first()
                    if numero_cible:
                        if numero_cible.statut == "gele":
                            ancien = Publication.objects.filter(statut="en_cours").first()
                            if ancien:
                                ancien.statut = "gele"
                                ancien.save()
                            numero_cible.statut = "en_cours"
                            numero_cible.save()
                            messages.info(request, f"Le numéro n°{numero_cible.numero} est maintenant en cours.")
                        
                        Article.objects.filter(pk__in=article_ids).update(statut_selection="disponible")
                        messages.success(request, f"{len(article_ids)} article(s) ont été envoyés au numéro n°{numero_cible.numero}.")
                        return redirect(f"/publications/composition/?numero_id={numero_cible.pk}")
                else:
                    Article.objects.filter(pk__in=article_ids).update(statut_selection="disponible")
                    messages.success(request, f"{len(article_ids)} article(s) ont été envoyés au vivier de composition.")
                    return redirect("publications:composition")
            else:
                Article.objects.filter(pk__in=article_ids).update(statut_selection="a_choisir")
                messages.success(request, f"{len(article_ids)} article(s) ont été remis dans la liste 'À choisir'.")
        return redirect("publications:choisir")

    articles = Article.objects.filter(
        statut="valide",
        statut_selection="reserve"
    ).order_by('-date_modification')
    
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    numeros_disponibles = Publication.objects.filter(statut="gele").order_by('numero')
    prochain_numero_id = numeros_disponibles.first().pk if numeros_disponibles.exists() else None
    
    return render(request, "publications/articles_reserves.html", {
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'numero_en_cours': Publication.objects.filter(statut="en_cours").first(),
        'numeros_disponibles': numeros_disponibles,
        'prochain_numero_id': prochain_numero_id,
    })

@role_required("editeur", "membre_redaction", "admin")
def ajouter_au_numero(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        article.statut_selection = "disponible"
        article.save()
        messages.success(request, f"L'article « {article.titre} » a été ajouté au vivier de composition.")
    return redirect("publications:composition")

@role_required("editeur", "membre_redaction", "admin")
def reserver_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        article.statut_selection = "reserve"
        article.save()
        messages.success(request, f"L'article « {article.titre} » est réservé pour un prochain numéro.")
    return redirect("publications:choisir")

@role_required("editeur", "membre_redaction", "admin")
def annuler_validation(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        article.statut = "en_relecture"
        article.statut_selection = "a_choisir"
        article.save()
        messages.warning(request, f"L'article « {article.titre} » a été renvoyé en relecture.")
    return redirect("publications:choisir")
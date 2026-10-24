from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

from accounts.decorators import role_required
from accounts.models import User
from core.utils import creer_notification
from core.models import Notification
from .forms import ArticleForm, ArticleVersionForm, ArticlePublicForm, ImageForm, ImageFormSet
from .models import Article, ArticleVersion
from .utils import rendre_diff
from publications.models import Publication
from articles.templatetags.typographie import typographier


User = get_user_model()


# ============================================
# BLOC 1 : GESTION DES ARTICLES (CRUD RÉDACTEUR)
# ============================================


def soumettre_article_public(request):
    if request.method == "POST":
        form = ArticlePublicForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            
            # 1. On cherche ou crée l'utilisateur
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": form.cleaned_data.get("prenom", ""),
                    "last_name": form.cleaned_data.get("nom", ""),
                }
            )
            
            # 2. Si on l'a créé (ou s'il met à jour ses infos), on gère la signature
            if created:
                if form.cleaned_data.get("signer_comme_correspondant"):
                    user.signature_defaut = "Correspondant LO"
                elif form.cleaned_data.get("prenom") or form.cleaned_data.get("nom"):
                    user.signature_defaut = f"{form.cleaned_data.get('prenom', '')} {form.cleaned_data.get('nom', '')}".strip()
                else:
                    user.signature_defaut = "Correspondant"
                
                user.set_unusable_password()
                user.save()

            # 3. On crée l'article
            article = Article.objects.create(
                titre=form.cleaned_data["titre"],
                sur_titre=form.cleaned_data.get("sur_titre", ""),
                type_article=form.cleaned_data["type_article"],
                rubrique=form.cleaned_data["rubrique"],
                contenu=form.cleaned_data["contenu"],
                redacteur=user,
                statut="soumis"
            )
            
            # 4. On crée la version v1 (soumise) en y glissant les commentaires
            commentaires = form.cleaned_data.get("commentaires", "").strip()
            texte_commentaire = f"Soumission publique. {commentaires}" if commentaires else "Soumission publique."
            
            version = ArticleVersion.creer(
                article=article,
                contenu=article.contenu,
                modifie_par=user,
                parent=None,
                type="auteur",
                commentaire=texte_commentaire,
            )
            version.statut = "soumise"
            version.save()
            article.version_reference = version
            article.save()
            
            # 5. On notifie les éditeurs (en ajoutant le commentaire s'il y en a un)
            editeurs = User.objects.filter(role__in=["editeur", "membre_redaction", "admin"])
            message_notif = f"Nouvel article public soumis : « {article.titre} » par {user.get_signature()}."
            if commentaires:
                message_notif += f" (Note : {commentaires[:50]}...)"
                
            for editeur in editeurs:
                creer_notification(
                    destinataire=editeur,
                    type="article_soumis",
                    message=message_notif,
                    lien=f"/articles/{article.pk}/",
                    emetteur=user,
                )
            
            return redirect("articles:merci_soumission")
            
    else:
        form = ArticlePublicForm()
        formset = ImageFormSet() 
        
    return render(request, "articles/soumettre_public.html", {
        "form": form,
        "formset": formset
    })


@role_required("redacteur")
def creer_article(request):
    if request.method == "POST":
        form = ArticleForm(request.POST)
        formset = ImageFormSet(request.POST, request.FILES)
  
        if form.is_valid() and formset.is_valid():
            article = form.save(commit=False)
            article.redacteur = request.user # <--- CORRIGÉ
            article.statut = "brouillon"
            article.save()

            # Version initiale
            version = ArticleVersion.creer(
                article=article,
                contenu=article.contenu,
                modifie_par=request.user, # <--- CORRIGÉ
                parent=None,
                type="auteur",
                commentaire="Version initiale.",
            )
            article.version_reference = version
            article.save()

            # On sauvegarde les images
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
    articles = Article.objects.filter(redacteur=request.user) # <--- CORRIGÉ

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

    if request.user.role == "redacteur" and article.redacteur != request.user: # <--- CORRIGÉ
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
    article = get_object_or_404(Article, pk=pk, redacteur=request.user) # <--- CORRIGÉ

    if article.statut != "brouillon" and not request.user.is_superuser:
        return render(request, "articles/article_verrouille.html", {"article": article})

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save()

            version = article.version_reference
            if version:
                version.contenu = article.contenu
                version.commentaire = "Modification par le rédacteur." # <--- CORRIGÉ
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

    if article.redacteur != request.user: # <--- CORRIGÉ
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
    
    if article.redacteur != request.user and request.user.role not in ("editeur", "admin"): # <--- CORRIGÉ
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


# ============================================
# BLOC 2 : CYCLE DE VIE DE L'ARTICLE
# ============================================

@role_required("redacteur")
@require_POST
def soumettre_article(request, pk):
    article = get_object_or_404(Article, pk=pk, redacteur=request.user) # <--- CORRIGÉ

    if article.statut == "brouillon":
        article.statut = "soumis"

        version = ArticleVersion.creer(
            article=article,
            contenu=article.contenu,
            modifie_par=request.user, # <--- CORRIGÉ
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
    article = get_object_or_404(Article, pk=pk, redacteur=request.user) # <--- CORRIGÉ
    
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


# ============================================
# BLOC 3 : TRAVAIL DE RELECTURE (VERSIONS)
# ============================================

@role_required("editeur", "membre_redaction", "admin")
def annoter_article(request, pk, version_id=None):
    article = get_object_or_404(Article, pk=pk)
    texte_affiche = ""

    if version_id:
        version = get_object_or_404(ArticleVersion, pk=version_id, article=article)
    else:
        version_get = request.GET.get("version")
        if version_get:
            version = get_object_or_404(ArticleVersion, pk=version_get, article=article)
        else:
            version = article.versions.order_by("-numero").first()
            if not version:
                version = article.version_reference

    versions = article.versions.order_by("numero")
    mode = request.GET.get("mode", "propre")
    if mode not in ("diff", "propre"):
        mode = "propre"

    if version:
        modifie_par = getattr(version, "modifie_par", None) # <--- CORRIGÉ
        est_texte_auteur = version.type == "auteur" or modifie_par == article.redacteur # <--- CORRIGÉ

        if est_texte_auteur or modifie_par is None: # <--- CORRIGÉ
            couleur = None
        else:
            couleur = modifie_par.couleur # <--- CORRIGÉ

        if mode == "propre":
            texte_affiche = version.contenu
        else:
            if version.parent:
                texte_parent = version.parent.contenu
                texte_actuel = version.contenu
                couleur_str = couleur if couleur else "black"
                texte_affiche = rendre_diff(texte_parent, texte_actuel, couleur_str)
            else:
                texte_affiche = version.contenu

    version_modifiable = version is not None and version.est_modifiable_par(request.user)
    version_supprimable = version is not None and version.peut_etre_supprimee(par_user=request.user)

    return render(request, "reviews/annoter_article.html", {
        "article": article,
        "version": version,
        "versions": versions,
        "texte_affiche": texte_affiche,
        "mode": mode,
        "version_modifiable": version_modifiable,
        "version_supprimable": version_supprimable,
    })


@role_required("editeur", "membre_redaction", "admin")
def choisir_base_relecture(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if article.statut == "valide":
        messages.error(request, "Cet article est actuellement validé. L'éditeur doit le dévalider avant que vous puissiez proposer une nouvelle version.")
        return redirect("articles:liste_versions", pk=article.pk)
        
    ma_version = article.versions.filter(type="relecture", modifie_par=request.user).first() # <--- CORRIGÉ

    if ma_version:
        return render(request, "articles/choisir_base_relecture.html", {
            "article": article,
            "ma_version": ma_version
        })
    else:
        return redirect("articles:creer_version_relecture", pk=article.pk)


@role_required("editeur", "membre_redaction", "admin")
def creer_version_relecture(request, pk):
    article = get_object_or_404(Article, pk=pk)

    version_parent = article.version_reference
    if not version_parent:
        version_parent = article.versions.order_by("-numero").first()

    if not version_parent:
        return render(request, "articles/version_impossible.html", {"article": article})

    if request.method == "POST":
        form = ArticleVersionForm(request.POST)
        if form.is_valid():
            version = ArticleVersion.creer(
                article=article,
                contenu=form.cleaned_data["contenu"],
                modifie_par=request.user, # <--- CORRIGÉ
                parent=version_parent,
                type="relecture",
                commentaire=form.cleaned_data["commentaire"],
            )
            return redirect("articles:annoter_article_avec_version", pk=article.pk, version_id=version.pk)
    else:
        form = ArticleVersionForm(initial={"contenu": version_parent.contenu})

    return render(request, "articles/creer_version.html", {
        "article": article,
        "version_parent": version_parent,
        "form": form,
    })


@role_required("editeur", "membre_redaction", "admin")
def modifier_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if not version.est_modifiable_par(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = ArticleVersionForm(request.POST, instance=version)
        if form.is_valid():
            version = form.save()
            return redirect("articles:annoter_article_avec_version", pk=article.pk, version_id=version.pk)
    else:
        form = ArticleVersionForm(instance=version)

    return render(request, "articles/modifier_version.html", {
        "article": article,
        "version": version,
        "form": form,
    })


@role_required("editeur", "membre_redaction", "admin")
@require_POST
def soumettre_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if version.modifie_par != request.user and request.user.role not in ("editeur", "admin"): # <--- CORRIGÉ
        raise PermissionDenied

    if version.statut != "brouillon":
        messages.error(request, "Cette version a déjà été soumise ou n'est plus modifiable.")
        return redirect("articles:liste_versions", pk=article.pk)

    avis = request.POST.get("avis", "favorable")
    if avis not in ["favorable", "defavorable"]:
        avis = "favorable"

    version.statut = "soumise"
    version.avis_relecteur = avis
    version.save()

    article.statut = "relu"

    # --- On réinitialise les compteurs de validation ---
    article.valide_1_par = None
    article.valide_1_mandataire = None
    article.valide_2_par = None
    article.valide_2_mandataire = None

    article.save()

    editeurs = User.objects.filter(role__in=["editeur", "admin"])
    
    message_notif = f"L'article « {article.titre} » a été relu par {request.user.username} (Avis : {avis})."
    lien_notif = f"/articles/{article.pk}/versions/"
    
    for editeur in editeurs:
        creer_notification(
            destinataire=editeur,
            type="review_deposee", 
            message=message_notif,
            lien=lien_notif
        )

    messages.success(request, f"Votre relecture de l'article « {article.titre} » a bien été transmise à l'éditeur.")
    
    return redirect("articles:liste_versions", pk=article.pk)


@role_required("editeur", "membre_redaction", "admin")
def supprimer_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if not version.peut_etre_supprimee(par_user=request.user):
        messages.error(request, "Vous n'avez pas le droit de supprimer cette version.")
        return redirect("articles:annoter_article", pk=article.pk)

    if request.method == "POST":
        version.delete()
        messages.success(request, "La version a bien été supprimée.")
        return redirect("articles:detail_article", pk=article.pk)

    return redirect("articles:annoter_article", pk=article.pk)


# ============================================
# BLOC 4 : CONTRÔLE ÉDITORIAL (ÉDITEUR)
# ============================================

@role_required("editeur", "membre_redaction", "admin")
def liste_versions(request, pk):
    article = get_object_or_404(Article, pk=pk)

    versions = [
        v for v in article.versions.select_related(
            "parent", "modifie_par"
        ).exclude(numero=0).order_by("numero")
        if not (v.statut == "brouillon" and v.enfants.exists())
    ]

    versions_comparables = article.versions.filter(
        type="relecture", 
        statut__in=["soumise", "validee"]
    ).count()
    peut_comparer = versions_comparables >= 2

    from accounts.models import User
    editeurs = User.objects.filter(role__in=["editeur", "membre_redaction", "admin"]).exclude(pk=request.user.pk)

    return render(request, "articles/liste_versions.html", {
            "article": article,
            "versions": versions,
            "version_reference": article.version_reference,
            "peut_comparer": peut_comparer,
            "editeurs": editeurs,
    })


@role_required("editeur", "membre_redaction", "admin")
@require_POST
def valider_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if version.type != "relecture":
        messages.error(request, "Vous ne pouvez pas valider une version initiale.")
        return redirect("articles:liste_versions", pk=article.pk)

    if version.statut not in ("soumise", "validee"):
        raise PermissionDenied

    # Gestion du mandataire
    au_nom_de_id = request.POST.get("au_nom_de")
    responsable = request.user
    mandataire = None

    if au_nom_de_id:
        from accounts.models import User
        try:
            responsable = User.objects.get(pk=au_nom_de_id)
            mandataire = request.user 
        except User.DoesNotExist:
            pass

    # --- PREMIÈRE VALIDATION ---
    if article.statut in ["soumis", "en_relecture", "relu"]:
        ArticleVersion.objects.filter(article=article, statut="validee").exclude(pk=version.pk).update(statut="soumise")
        version.statut = "validee"
        version.save()
        
        article.statut = "valide_1_fois"
        article.valide_1_par = responsable
        article.valide_1_mandataire = mandataire
        article.save()
        
        messages.success(request, f"Article validé une première fois par {responsable.username}. En attente d'un second éditeur.")

    # --- DEUXIÈME VALIDATION ---
    elif article.statut == "valide_1_fois":
        # On compare le responsable (et non le mandataire) avec la première validation
        if article.valide_1_par == responsable:
            messages.warning(request, f"{responsable.username} a déjà validé cet article. Un autre éditeur doit le valider pour confirmer.")
        else:
            version.statut = "validee"
            version.save()
            
            article.statut = "valide"
            article.valide_2_par = responsable
            article.valide_2_mandataire = mandataire
            article.statut_selection = "a_choisir"
            article.save()
            
            article.versions.filter(statut="soumise").exclude(pk=version.pk).update(statut="archivee")
            
            messages.success(request, f"Article validé définitivement par {responsable.username} ! Il est prêt pour la composition.")

    return redirect("articles:liste_versions", pk=article.pk)


@role_required("editeur", "membre_redaction", "admin")
@require_POST
def annuler_validation_1(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if article.statut == "valide_1_fois":
        # 1. On remet l'article en attente
        article.statut = "relu"
        article.valide_1_par = None
        article.valide_1_mandataire = None
        article.save()
        
        # 2. On remet la version validée en soumise (LA LIGNE MANQUANTE)
        article.versions.filter(statut="validee").update(statut="soumise")
        
        messages.success(request, "La première validation a été annulée. L'article est de nouveau en attente.")
    
    return redirect("articles:liste_versions", pk=article.pk)


@role_required("editeur", "admin")
@require_POST
def devalider_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if version.statut != "validee":
        messages.error(request, "Seule une version validée peut être dévalidée.")
        return redirect("articles:liste_versions", pk=article.pk)

    version.statut = "soumise"
    version.save()

    # --- NOUVEAU : On vérifie s'il reste d'autres versions validées ---
    autre_version_validee = article.versions.filter(statut="validee").exclude(pk=version.pk).exists()
    
    if autre_version_validee:
        # Il reste une autre version validée, on redescend juste d'un cran
        article.statut = "valide_1_fois"
        article.valide_2_par = None
        article.valide_2_mandataire = None
    else:
        # Plus aucune version validée, on repart en relecture classique
        article.statut = "en_relecture"
        article.valide_1_par = None
        article.valide_1_mandataire = None
        article.valide_2_par = None
        article.valide_2_mandataire = None
    # -----------------------------------------------------------------

    article.save()

    messages.success(request, f"La version v{version.numero} a été dévalidée. Le statut de l'article a été mis à jour.")
    return redirect("articles:liste_versions", pk=article.pk)


@role_required("editeur", "membre_redaction", "admin")
@require_POST
def rejeter_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if version.statut not in ("soumise", "validee"):
        raise PermissionDenied

    commentaire = request.POST.get("commentaire", "").strip()
    if not commentaire:
        messages.error(request, "Un commentaire est obligatoire pour rejeter.")
        return redirect("articles:liste_versions", pk=article.pk)

    version.statut = "rejetee"
    version.commentaire_validation = commentaire
    version.save()

    # --- AJOUT IMPORTANT : On rejette aussi l'article global ---
    article.statut = "rejete" 
    article.save()
    # -----------------------------------------------------------

    messages.success(request, f"Version v{version.numero} rejetée.")
    return redirect("articles:liste_versions", pk=article.pk)


@role_required("editeur", "membre_redaction", "admin")
def comparer_versions(request, pk):
    article = get_object_or_404(Article, pk=pk)
    versions = article.versions.order_by("numero")

    versions_relecture = versions.filter(type="relecture")
    if versions_relecture.count() < 2:
        return render(request, "articles/comparer_versions.html", {
            "article": article,
            "message": "La comparaison n'est possible qu'à partir de deux versions de relecture.",
            "versions": versions,
        })

    versions_valides = versions_relecture.filter(statut__in=["soumise", "validee"])
    if versions_valides.count() < 2:
        return render(request, "articles/comparer_versions.html", {
            "article": article,
            "message": "Les deux versions à comparer doivent être soumises ou validées.",
            "versions": versions,
        })

    from collections import defaultdict
    par_parent = defaultdict(list)
    for v in versions_valides:
        par_parent[v.parent_id].append(v)

    groupes_valides = [g for g in par_parent.values() if len(g) >= 2]

    if not groupes_valides:
        return render(request, "articles/comparer_versions.html", {
            "article": article,
            "message": "Les versions de relecture ne partagent pas la même version parente : la comparaison serait biaisée.",
            "versions": versions,
        })

    groupe = groupes_valides[0]
    
    # --- NOUVELLE LOGIQUE DE SÉLECTION DES VERSIONS ---
    v1_id = request.GET.get("v1")
    v2_id = request.GET.get("v2")

    v1 = None
    v2 = None

    # 1. On cherche v1 si l'ID est fourni dans l'URL
    if v1_id:
        try:
            v1 = groupe[int(v1_id)]
        except (ValueError, IndexError):
            pass # Si l'ID est invalide, on laissera le fallback par défaut plus bas

    # 2. On cherche v2 si l'ID est fourni dans l'URL
    if v2_id:
        try:
            v2 = groupe[int(v2_id)]
        except (ValueError, IndexError):
            pass

    # 3. Fallback : si v1 n'a pas été trouvé ou n'était pas demandé, on prend la 1ère version du groupe
    if not v1:
        v1 = groupe[0]

    # 4. Fallback : si v2 n'a pas été trouvé, ou si v2 est égal à v1, on prend la 1ère version du groupe qui n'est pas v1
    if not v2 or v2 == v1:
        v2 = next((v for v in groupe if v != v1), groupe[0])
    # --------------------------------------------------

    def _diff_pour(version):
        if version.parent:
            return rendre_diff(
                version.parent.contenu,
                version.contenu,
                version.modifie_par.couleur if version.modifie_par else "bleu",
            )
        return version.contenu

    v1_diff = _diff_pour(v1)
    v2_diff = _diff_pour(v2)

    mode = request.GET.get("mode", "diff")
    if mode not in ("diff", "propre"):
        mode = "diff"

    return render(request, "articles/comparer_versions.html", {
        "article": article,
        "versions": versions,
        "groupe": groupe,
        "v1": v1,
        "v2": v2,
        "v1_diff": v1_diff,
        "v2_diff": v2_diff,
        "mode": mode,
    })


@role_required("editeur", "membre_redaction", "admin")
def telecharger_pdf_version(request, pk, version_id):
    article = get_object_or_404(Article, pk=pk)
    version = get_object_or_404(ArticleVersion, pk=version_id, article=article)

    if version.type == "auteur" or version.numero == 0:
        label_version = "initiale"
    else:
        auteur_nom = version.modifie_par.get_full_name() or version.modifie_par.username # <--- CORRIGÉ
        label_version = f"validée par {auteur_nom}"

    signature = article.redacteur.get_signature() # <--- CORRIGÉ

    contenu_brut = version.contenu.replace("\r\n", "\n")
    paragraphes = contenu_brut.split("\n")
    
    # On applique la typographie sur CHAQUE PARAGRAPHE BRUT, puis on ajoute les <p>
    contenu_html = "".join([f"<p>{typographier(p)}</p>" for p in paragraphes if p.strip() != ""])
    
    context = {
        "nb_signes": version.nombre_signes(),
        "label_version": label_version,
        "sur_titre": article.sur_titre, # <--- Remplace sous_titre par sur_titre
        "titre": article.titre,
        "contenu": contenu_html,
        "signature": signature,
    }

    html_string = render_to_string("articles/version_print.html", context)
    pdf_file = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    filename = f"article_{article.pk}_v{version.numero}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


def merci_soumission(request):
    return render(request, "articles/merci_soumission.html")


# ============================================
# BLOC 5 : COMPOSITION DU NUMERO (ÉDITEUR)
# ============================================


@role_required("editeur", "admin")
def choisir(request):
    if request.method == "POST":
        article_ids = request.POST.getlist("article_ids")
        action = request.POST.get("action")
        
        if article_ids:
            if action == "reserver":
                Article.objects.filter(pk__in=article_ids).update(statut_selection="reserve")
                messages.success(request, f"{len(article_ids)} article(s) ont été réservés pour les numéros suivants.")
                return redirect("articles:articles_reserves")
            
            elif action == "ajouter":
                Article.objects.filter(pk__in=article_ids).update(statut_selection="disponible")
                messages.success(request, f"{len(article_ids)} article(s) ont été ajoutés au vivier de composition.")
                return redirect("publications:composition")
                
        return redirect("articles:choisir")

    articles = Article.objects.filter(
        statut="valide",
        statut_selection="a_choisir"
    ).order_by('-date_modification')
    
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    # On récupère le numéro en cours pour l'afficher dans le bouton
    numero_en_cours = Publication.objects.filter(statut="en_cours").first()
    
    return render(request, "articles/choisir.html", {
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
                Article.objects.filter(pk__in=article_ids).update(statut_selection="disponible")
                messages.success(request, f"{len(article_ids)} article(s) ont été envoyés au vivier de composition.")
                return redirect("publications:composition")
            else:
                Article.objects.filter(pk__in=article_ids).update(statut_selection="a_choisir")
                messages.success(request, f"{len(article_ids)} article(s) ont été remis dans la liste 'À choisir'.")
        return redirect("articles:choisir")

    articles = Article.objects.filter(
        statut="valide",
        statut_selection="reserve"
    ).order_by('-date_modification')
    
    paginator = Paginator(articles, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    
    # On récupère le numéro en cours pour le bouton de droite
    numero_en_cours = Publication.objects.filter(statut="en_cours").first()
    
    return render(request, "articles/articles_reserves.html", {
        'articles': page_obj.object_list,
        'page_obj': page_obj,
        'numero_en_cours': numero_en_cours,
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
    return redirect("articles:choisir")


@role_required("editeur", "membre_redaction", "admin")
def annuler_validation(request, pk):
    article = get_object_or_404(Article, pk=pk)
    if request.method == "POST":
        article.statut = "en_relecture"
        article.statut_selection = "a_choisir"
        article.save()
        messages.warning(request, f"L'article « {article.titre} » a été renvoyé en relecture.")
    return redirect("articles:choisir")
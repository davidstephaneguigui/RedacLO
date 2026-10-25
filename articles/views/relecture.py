from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML

from accounts.decorators import role_required
from accounts.models import User
from core.utils import creer_notification
from ..forms import ArticleVersionForm
from ..models import Article, ArticleVersion
from ..utils import rendre_diff
from ..templatetags.typographie import typographier

User = get_user_model()

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
        modifie_par = getattr(version, "modifie_par", None)
        est_texte_auteur = version.type == "auteur" or modifie_par == article.redacteur

        if est_texte_auteur or modifie_par is None:
            couleur = None
        else:
            couleur = modifie_par.couleur

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
        
    ma_version = article.versions.filter(type="relecture", modifie_par=request.user).first()

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
                modifie_par=request.user,
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

    if version.modifie_par != request.user and request.user.role not in ("editeur", "admin"):
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

@role_required("editeur", "membre_redaction", "admin")
def liste_versions(request, pk):
    article = get_object_or_404(Article, pk=pk)

    versions = [
        v for v in article.versions.select_related("parent", "modifie_par").exclude(numero=0).order_by("numero")
        if not (v.statut == "brouillon" and v.enfants.exists())
    ]

    versions_comparables = article.versions.filter(type="relecture", statut__in=["soumise", "validee"]).count()
    peut_comparer = versions_comparables >= 2

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

    au_nom_de_id = request.POST.get("au_nom_de")
    responsable = request.user
    mandataire = None

    if au_nom_de_id:
        try:
            responsable = User.objects.get(pk=au_nom_de_id)
            mandataire = request.user 
        except User.DoesNotExist:
            pass

    if article.statut in ["soumis", "en_relecture", "relu"]:
        ArticleVersion.objects.filter(article=article, statut="validee").exclude(pk=version.pk).update(statut="soumise")
        version.statut = "validee"
        version.save()
        
        article.statut = "valide_1_fois"
        article.valide_1_par = responsable
        article.valide_1_mandataire = mandataire
        article.save()
        
        messages.success(request, f"Article validé une première fois par {responsable.username}. En attente d'un second éditeur.")

    elif article.statut == "valide_1_fois":
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
        article.statut = "relu"
        article.valide_1_par = None
        article.valide_1_mandataire = None
        article.save()
        
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

    autre_version_validee = article.versions.filter(statut="validee").exclude(pk=version.pk).exists()
    
    if autre_version_validee:
        article.statut = "valide_1_fois"
        article.valide_2_par = None
        article.valide_2_mandataire = None
    else:
        article.statut = "en_relecture"
        article.valide_1_par = None
        article.valide_1_mandataire = None
        article.valide_2_par = None
        article.valide_2_mandataire = None

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

    article.statut = "rejete" 
    article.save()

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
    
    v1_id = request.GET.get("v1")
    v2_id = request.GET.get("v2")

    v1 = None
    v2 = None

    if v1_id:
        try:
            v1 = groupe[int(v1_id)]
        except (ValueError, IndexError):
            pass 

    if v2_id:
        try:
            v2 = groupe[int(v2_id)]
        except (ValueError, IndexError):
            pass

    if not v1:
        v1 = groupe[0]

    if not v2 or v2 == v1:
        v2 = next((v for v in groupe if v != v1), groupe[0])

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
        auteur_nom = version.modifie_par.get_full_name() or version.modifie_par.username
        label_version = f"validée par {auteur_nom}"

    signature = article.redacteur.get_signature()

    contenu_brut = version.contenu.replace("\r\n", "\n")
    paragraphes = contenu_brut.split("\n")
    
    contenu_html = "".join([f"<p>{typographier(p)}</p>" for p in paragraphes if p.strip() != ""])
    
    context = {
        "nb_signes": version.nombre_signes(),
        "label_version": label_version,
        "sur_titre": article.sur_titre,
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
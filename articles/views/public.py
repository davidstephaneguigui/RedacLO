from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from accounts.models import User
from core.utils import creer_notification
from ..forms import ArticlePublicForm, ImageFormSet
from ..models import Article, ArticleVersion

User = get_user_model()

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
            
            # 5. On notifie les éditeurs
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

def merci_soumission(request):
    return render(request, "articles/merci_soumission.html")
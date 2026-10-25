from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from accounts.decorators import role_required
from accounts.models import User
from ..forms import ReviewForm
from ..models import Review
from core.utils import creer_notification

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
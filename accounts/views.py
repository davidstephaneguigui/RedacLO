from django.shortcuts import render
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.conf import settings

from .decorators import role_required
from .forms import InvitationForm, AcceptInvitationForm
from .models import Invitation, User


@role_required("admin")
def inviter(request):
    if request.method == "POST":
        form = InvitationForm(request.POST)
        if form.is_valid():
            invitation = form.save(commit=False)
            invitation.auteur_modification = request.user
            invitation.save()

            lien = request.build_absolute_uri(
                reverse("accounts:accepter_invitation", args=[invitation.token])
            )
            send_mail(
                subject="Invitation à rejoindre RedacLo",
                message=f"Bonjour,\n\nVous êtes invité à rejoindre RedacLo.\n"
                        f"Cliquez sur ce lien pour créer votre compte :\n{lien}\n\n"
                        f"Ce lien expire le {invitation.date_expiration:%d/%m/%Y}.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
            )
            return render(request, "accounts/invitation_envoyee.html", {
                "email": invitation.email,
                "lien": lien,
            })
    else:
        form = InvitationForm()

    return render(request, "accounts/inviter.html", {"form": form})


def accepter_invitation(request, token):
    invitation = get_object_or_404(Invitation, token=token)

    if not invitation.est_valide():
        return render(request, "accounts/invitation_invalide.html")

    if request.method == "POST":
        form = AcceptInvitationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=invitation.email,
                password=form.cleaned_data["password1"],
                role=invitation.role,
            )
            invitation.utilisee = True
            invitation.save()
            return redirect("login")
    else:
        form = AcceptInvitationForm()

    return render(request, "accounts/accepter_invitation.html", {
        "form": form,
        "invitation": invitation,
    })

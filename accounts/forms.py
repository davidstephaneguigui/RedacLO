from django import forms
from .models import Invitation, User


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ["email", "role"]
        widgets = {
            "email": forms.EmailInput(attrs={"placeholder": "prenom.nom@exemple.fr"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse.")
        return email

class AcceptInvitationForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nom d'utilisateur")
    password1 = forms.CharField(
        widget=forms.PasswordInput,
        label="Mot de passe",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput,
        label="Confirmer le mot de passe",
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Les deux mots de passe ne correspondent pas.")
        return cleaned
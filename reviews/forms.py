from django import forms
from accounts.models import User
from .models import Review


class AssignationForm(forms.Form):
    relecteur = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Choisir un relecteur",
        empty_label="— Sélectionner —",
    )
 

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["commentaire", "decision"]
        widgets = {
            "commentaire": forms.Textarea(attrs={"rows": 8}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On retire "En attente" des choix : on ne dépose pas une review en attente
        self.fields["decision"].choices = [
            (v, l) for v, l in Review.DECISIONS if v != "en_attente"
        ]
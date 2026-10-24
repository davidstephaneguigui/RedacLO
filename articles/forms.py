from django import forms
from .models import Article
from publications.models import Rubrique
from .models import ArticleVersion
from django.contrib.auth import get_user_model
from .models import Article, ArticleVersion, Image # Ajoute Image ici
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

import re


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["titre", "sur_titre", "type_article", "rubrique", "contenu"]
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On rend ces champs facultatifs
        self.fields['sur_titre'].required = False
        self.fields['rubrique'].required = False
        self.fields['type_article'].required = False
        
        # Optionnel : on peut ajouter un texte "facultatif" à côté du label
        self.fields['sur_titre'].label = "Sur-titre (facultatif)"
        self.fields['rubrique'].label = "Rubrique (facultatif)"
        

class ArticleVersionForm(forms.ModelForm):
    """
    Formulaire de création d'une version de relecture.

    On ne demande que le contenu et un commentaire optionnel.
    Les autres champs (article, parent, type, redacteur_modification)
    sont remplis par la vue.
    """
    class Meta:
        model = ArticleVersion
        fields = ["contenu", "commentaire"]
        widgets = {
                "contenu": forms.Textarea(attrs={
                "rows": 30,
                "class": "textarea-large",
            }),
            "commentaire": forms.TextInput(attrs={
                "placeholder": "Commentaire sur cette version (facultatif)",
            }),
        }
        labels = {
            "contenu": "Texte de la version",
            "commentaire": "Commentaire",
        }

    def nombre_signes(self):
        """Retourne le nombre de caractères en excluant le texte barré (obsolète)."""
        if not self.contenu:
            return 0
        # On supprime tout ce qui est entre <del> et </del>
        texte_propre = re.sub(r'<del[^>]*>.*?</del>', '', self.contenu, flags=re.DOTALL)
        # On supprime les autres balises HTML (<ins>, <span>, etc.)
        texte_propre = re.sub(r'<[^>]+>', '', texte_propre)
        return len(texte_propre.strip())

    def contenu_pour_latex(self):
        """Échappe les caractères spéciaux LaTeX et nettoie le HTML."""
        if not self.contenu:
            return ""
        
        # 1. Nettoyage du HTML (on garde le texte, on vire les balises)
        # Mais attention, pour le diff, on veut garder le texte barré ? 
        # Pour l'impression, on veut généralement le texte propre.
        texte_propre = re.sub(r'<[^>]+>', '', self.contenu)
        
        # 2. Échappement LaTeX
        remplacements = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}',
            '\\': r'\textbackslash{}',
        }
        for ancien, nouveau in remplacements.items():
            texte_propre = texte_propre.replace(ancien, nouveau)
            
        # Remplacement des paragraphes par des doubles sauts de ligne LaTeX
        texte_propre = texte_propre.replace('\n', '\n\n')
        
        return texte_propre


User = get_user_model()


class ArticlePublicForm(forms.Form):
    # Champs de l'article
    sur_titre = forms.CharField(max_length=200, required=False, label="Sur-titre (optionnel)")
    titre = forms.CharField(max_length=200, label="Titre de l'article")
    type_article = forms.ChoiceField(choices=Article.TYPES_ARTICLE, label="Type d'article")
    rubrique = forms.ModelChoiceField(queryset=Rubrique.objects.all(), required=False, label="Rubrique")
    contenu = forms.CharField(widget=forms.Textarea(attrs={'rows': 15}), label="Contenu de l'article")
    
    # Champs utilisateur
    email = forms.EmailField(label="Votre adresse email (requise pour vous recontacter)", required=True)
    prenom = forms.CharField(max_length=100, label="Prénom (facultatif)", required=False)
    nom = forms.CharField(max_length=100, label="Nom (facultatif)", required=False)

    # Signature et informations
    signer_comme_correspondant = forms.BooleanField(
        required=False, 
        label="Je signe comme Correspondant LO"
    )
    
    commentaires = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Laisse un numéro de téléphone si tu juges nécessaire de nous expliquer le contexte.'}),
        required=False, 
        label="Informations pour la rédaction (facultatif)"
    )


class ImageForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ["fichier", "legende", "est_prise_par_redacteur", "droits_ok"]
        labels = {
            "fichier": "Fichier image",
            "legende": "Légende de l'image (optionnel)",
            "est_prise_par_redacteur": "Est-ce que c'est toi qui as pris cette photo ?",
            "droits_ok": "Je certifie que nous avons les droits d'utilisation",
        }

    def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # On rend le fichier facultatif
            self.fields['fichier'].required = False

    def clean(self):
        cleaned_data = super().clean()
        fichier = cleaned_data.get('fichier')
        droits_ok = cleaned_data.get('droits_ok')
        est_prise_par_redacteur = cleaned_data.get('est_prise_par_redacteur')

        if fichier and not droits_ok and not est_prise_par_redacteur:
            raise ValidationError("Vous devez soit cocher 'C'est bien moi qui ai pris cette photo', soit certifier que vous avez les droits d'utilisation.")
        
        return cleaned_data


# On crée le formset APRÈS avoir défini ImageForm
ImageFormSet = inlineformset_factory(
    Article,
    Image,
    form=ImageForm,
    extra=1,          # Affiche 1 champ image vide par défaut
    can_delete=True,  # Ajoute une case à cocher pour supprimer l'image
)
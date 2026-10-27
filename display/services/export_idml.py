from simple_idml import idml
from pathlib import Path
from django.conf import settings

def exporter_page_en_idml(page):
    """
    Prend une page, charge son template IDML et y injecte les articles.
    Retourne le chemin vers le fichier généré (ou les octets).
    """
    # 1. On vérifie que le gabarit a bien un fichier IDML associé
    if not hasattr(page.gabarit, 'template_idml'):
        raise ValueError(f"Aucun template IDML n'est configuré pour le gabarit '{page.gabarit.nom}'.")

    # 2. On charge le fichier IDML de base
    chemin_template = page.gabarit.template_idml.fichier.path
    package = idml.IDMLPackage(chemin_template)

    # 3. On récupère les articles de la page, triés par position
    articles_places = page.articles_lies.all().order_by('position')

    # 4. On boucle sur les articles pour injecter le contenu
    # (Note : l'API exacte dépend de la structure de ton IDML, 
    # on utilise ici une logique générique de remplacement de texte)
    for i, pa in enumerate(articles_places):
        article = pa.article
        
        # On cherche les balises dans le template (ex: {{TITRE_1}}, {{CONTENU_1}})
        # et on les remplace par le contenu de l'article.
        try:
            # Exemple avec la librairie simple_idml
            story_titre = package.story(f"TITRE_{i+1}")
            story_titre.set_content(article.titre)
            
            story_contenu = package.story(f"CONTENU_{i+1}")
            story_contenu.set_content(article.contenu)
        except Exception as e:
            print(f"Attention : impossible de trouver la balise pour l'article {i+1} : {e}")

    # 5. On génère et on sauvegarde le nouveau fichier IDML
    # (Pour l'instant, on le sauvegarde dans un dossier temporaire ou media)
    chemin_sortie = Path(settings.MEDIA_ROOT) / f"export_page_{page.numero_page}.idml"
    package.save(chemin_sortie)

    return chemin_sortie
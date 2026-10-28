import zipfile

def exporter_page_en_idml(page):
    if not page.gabarit:
        raise ValueError(f"La page {page.numero_page} n'a aucun gabarit de configuré dans l'admin.")
        
    if not hasattr(page.gabarit, 'template_idml'):
        raise ValueError(f"Aucun template IDML n'est configuré pour le gabarit '{page.gabarit.nom}'.")

    chemin_template = page.gabarit.template_idml.fichier.path
    chemin_sortie = chemin_template.replace('.idml', f'_export_{page.numero_page}.idml')

    # On récupère les articles triés
    articles_places = page.articles_lies.all().order_by('position')
    
    # On prépare les textes de remplacement
    remplacements = {}
    for i, pa in enumerate(articles_places):
        remplacements[f"TITRE_{i+1}"] = pa.article.titre or "Sans titre"
        remplacements[f"CONTENU_{i+1}"] = pa.article.contenu or ""

    # On ouvre l'IDML de base (c'est un ZIP) et on crée le nouveau
    with zipfile.ZipFile(chemin_template, 'r') as zin:
        with zipfile.ZipFile(chemin_sortie, 'w', zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                buffer = zin.read(item.filename)
                
                # Si c'est un fichier XML (où se trouve le texte), on applique les remplacements
                if item.filename.endswith('.xml'):
                    try:
                        texte = buffer.decode('utf-8')
                        for ancien, nouveau in remplacements.items():
                            texte = texte.replace(ancien, nouveau)
                        buffer = texte.encode('utf-8')
                    except UnicodeDecodeError:
                        pass # Si ce n'est pas du texte, on ignore

                # On écrit le fichier (modifié ou non) dans le nouveau ZIP
                zout.writestr(item, buffer)

    return chemin_sortie
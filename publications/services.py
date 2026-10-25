from .models import PageArticle

def equilibrer_doubles_pages(publication):
    """
    Répartit automatiquement les signes et synchronise les boutons 
    sur les doubles pages pour une publication donnée.
    """
    pages_list = list(publication.pages.all().order_by("numero_page"))
    
    for i, page in enumerate(pages_list):
        if i < len(pages_list) - 1:
            page_suivante = pages_list[i + 1]
            
            # 1. Rééquilibrage des signes
            total = page.total_signes()
            if total > page.limite_signes():
                depassement = total - page.limite_signes()
                placements = page.articles_lies.filter(est_fin=False)
                for pa in placements:
                    if depassement <= 0: break
                    if pa.signes_sur_page is None:
                        version = pa.article.version_courante()
                        if version: pa.signes_sur_page = version.nombre_signes()
                    
                    if pa.signes_sur_page and pa.signes_sur_page > 0:
                        a_retirer = min(pa.signes_sur_page, depassement)
                        pa.signes_sur_page -= a_retirer
                        pa.save()
                        depassement -= a_retirer
                        
                        pa_suivant = PageArticle.objects.filter(page=page_suivante, article=pa.article).first()
                        if pa_suivant:
                            if pa_suivant.signes_sur_page is None: pa_suivant.signes_sur_page = 0
                            pa_suivant.signes_sur_page += a_retirer
                            pa_suivant.save()

            # 2. Synchronisation visuelle (bouton Fin)
            for pa in page.articles_lies.all():
                if PageArticle.objects.filter(page=page_suivante, article=pa.article).exists():
                    if pa.est_fin:
                        pa.est_fin = False
                        pa.save()
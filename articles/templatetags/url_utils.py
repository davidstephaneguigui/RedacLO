from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_tri(context, colonne, tri_courant):
    """Construit l'URL pour trier par `colonne`, en basculant si on reclique."""
    request = context['request']
    query = request.GET.copy()
    if tri_courant == colonne:
        nouveau_tri = '-' + colonne          # déjà croissant → on passe décroissant
    elif tri_courant == '-' + colonne:
        nouveau_tri = colonne                # déjà décroissant → on repasse croissant
    else:
        nouveau_tri = colonne                # première activation → croissant
    query['tri'] = nouveau_tri
    query.pop('page', None)                  # on repart en page 1
    return query.urlencode()


@register.simple_tag(takes_context=True)
def url_page(context, num_page):
    """Construit l'URL pour aller à la page `num_page`, en gardant le tri."""
    request = context['request']
    query = request.GET.copy()
    if num_page == 1:
        query.pop('page', None)              # page 1 : pas besoin du paramètre
    else:
        query['page'] = num_page
    return query.urlencode()
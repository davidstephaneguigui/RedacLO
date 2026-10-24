import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def typographier(texte):
    if not texte:
        return texte

    # 1. On échappe le HTML pour la sécurité
    texte_echappe = escape(texte)
    
    # 2. On restaure les guillemets et apostrophes (que escape a détruits)
    texte_echappe = texte_echappe.replace("&quot;", '"').replace("&#x27;", "'")

    # 3. Guillemets droits (") -> guillemets français (« »)
    texte_formate = re.sub(r'"(.*?)"', r'&laquo;&nbsp;\1&nbsp;&raquo;', texte_echappe)
    
    # 4. Italique auto entre les guillemets
    texte_formate = re.sub(r'(&laquo;&nbsp;.*?&nbsp;&raquo;)', r'<i>\1</i>', texte_formate)

    # 5. Apostrophes courbes
    texte_formate = texte_formate.replace("'", "&rsquo;")
    
    return mark_safe(texte_formate)
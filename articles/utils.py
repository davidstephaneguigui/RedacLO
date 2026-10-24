from django.utils.html import escape
import difflib
import html



def _envelopper(html, debut, fin, type_seg, couleur=None):
    """
    Enveloppe un fragment HTML dans un <span> qui porte les
    positions dans le texte original.
    """
    classes = ["seg"]
    if couleur:
        classes.append(f"rel-{couleur}")

    attrs = (
        f'class="{" ".join(classes)}" '
        f'data-debut="{debut}" '
        f'data-fin="{fin}" '
        f'data-type="{type_seg}"'
    )
    return f"<span {attrs}>{html}</span>"


def rendre_texte_annote(texte, couleur=None):
    """
    Produit une version annotable du texte : chaque fragment
    est enveloppé dans un <span class="seg">.
    """
    import re
    parties = re.split(r'((?:\r?\n){2,})', texte)
    resultat = []
    pos = 0

    for partie in parties:
        if not partie:
            continue
        fin = pos + len(partie)
        resultat.append(
            _envelopper(
                escape(partie),
                debut=pos,
                fin=fin,
                type_seg="texte",
                couleur=couleur,
            )
        )
        pos = fin

    return "".join(resultat)


SEUIL_EQUAL = 20  # en dessous, un "equal" est absorbé dans la zone modifiée


def rendre_diff(texte_parent, texte_actuel, couleur):
    """
    Produit une chaîne HTML représentant le diff entre deux textes.

    Le diff est calculé caractère par caractère sur le texte complet.
    Entre deux passages identiques assez longs (>= SEUIL_EQUAL), toutes
    les suppressions sont regroupées avant toutes les insertions :

        ... égal <del>supprimé</del><ins>ajouté</ins> égal ...

    Les passages identiques trop courts (espaces, virgules, lettres
    communes au milieu d'une réécriture) sont absorbés dans la zone
    modifiée, pour éviter un entremêlement illisible.
    """

    # On s'assure que les textes ne contiennent pas d'entités HTML
    texte_parent = html.unescape(texte_parent)
    texte_actuel = html.unescape(texte_actuel)

    sm = difflib.SequenceMatcher(
        None, texte_parent, texte_actuel, autojunk=False
    )
    morceaux = []
    del_buffer = []
    ins_buffer = []

    def vider():
        if del_buffer:
            morceaux.append(
                f'<del class="rel-{couleur}">{"".join(del_buffer)}</del>'
            )
            del_buffer.clear()
        if ins_buffer:
            morceaux.append(
                f'<ins class="rel-{couleur}">{"".join(ins_buffer)}</ins>'
            )
            ins_buffer.clear()

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            txt = texte_parent[i1:i2]
            if len(txt) >= SEUIL_EQUAL:
                # Passage identique assez long : on clôt la zone modifiée.
                vider()
                morceaux.append(escape(txt))
            else:
                # Passage identique trop court : absorbé dans la zone.
                # On le met dans les deux buffers pour qu'il apparaisse
                # à la fois dans l'ancien (barré) et dans le nouveau.
                del_buffer.append(escape(txt))
                ins_buffer.append(escape(txt))
        elif tag == 'delete':
            del_buffer.append(escape(texte_parent[i1:i2]))
        elif tag == 'insert':
            ins_buffer.append(escape(texte_actuel[j1:j2]))
        elif tag == 'replace':
            if i2 > i1:
                del_buffer.append(escape(texte_parent[i1:i2]))
            if j2 > j1:
                ins_buffer.append(escape(texte_actuel[j1:j2]))

    vider()
    return ''.join(morceaux)
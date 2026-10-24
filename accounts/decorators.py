from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

HIERARCHIE = {
    "admin": ["admin", "editeur", "relecteur", "redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "editeur": ["editeur", "relecteur", "redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "relecteur": ["relecteur", "redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "redacteur": ["redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "redacteur_breves": ["redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "correspondant": ["redacteur", "redacteur_breves", "correspondant", "editorialiste"],
    "editorialiste": ["redacteur", "redacteur_breves", "correspondant", "editorialiste"],
}

def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # On récupère les rôles effectifs de l'utilisateur
            roles_effectifs = HIERARCHIE.get(user.role, [user.role])
            
            # LA CORRECTION EST ICI : on convertit les deux en set()
            if not set(roles_effectifs) & set(roles):
                raise PermissionDenied
                
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
document.addEventListener('DOMContentLoaded', function() {
    // --- 1. GESTION DU VIVIER ---
    const vivier = document.getElementById('vivier-container');
    const actionsVivier = document.getElementById('actions-vivier');
    
    // Masquer les actions si le vivier est masqué au chargement
    if (vivier && vivier.style.display === 'none') {
        if (actionsVivier) actionsVivier.style.display = 'none';
    }

    // La fonction toggleVivier doit être globale pour être appelée par le bouton HTML
    window.toggleVivier = function() {
        const btn = document.getElementById('btn-toggle-vivier');
        if (vivier.style.display === 'none') {
            vivier.style.display = 'block';
            if (actionsVivier) actionsVivier.style.display = 'flex';
            btn.innerHTML = 'Masquer le vivier';
        } else {
            vivier.style.display = 'none';
            if (actionsVivier) actionsVivier.style.display = 'none';
            btn.innerHTML = 'Afficher le vivier';
        }
    };

    // --- 2. GESTION DU "TOUT SÉLECTIONNER" ---
    const selectAll = document.getElementById('select-all-composer');
    const checkboxes = document.querySelectorAll('input[name="article_ids"]');

    if (selectAll && checkboxes.length > 0) {
        selectAll.addEventListener('change', function() {
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
        });

        checkboxes.forEach(cb => {
            cb.addEventListener('change', function() {
                if (!this.checked) {
                    selectAll.checked = false;
                } else if (document.querySelectorAll('input[name="article_ids"]:checked').length === checkboxes.length) {
                    selectAll.checked = true;
                }
            });
        });
    }

    // --- 3. GESTION DES ACTIONS RUBRIQUES (Anniversaire / Modifier) ---
    window.gererActionRubrique = function(select, pageId) {
        const val = select.value;
        const url = new URL(window.location.href);
        
        if (val === 'ACTION_ANNIVERSAIRE') {
            const nom = prompt("Quel est le nom de la rubrique ? (ex: Il y a 70 ans)");
            if (nom) {
                url.searchParams.set('page_id', pageId);
                url.searchParams.set('action_rubrique', 'anniversaire');
                url.searchParams.set('nom_rubrique', nom);
                url.hash = 'page-' + pageId;
                window.location.href = url.href;
            } else {
                select.value = ""; 
            }
        } else if (val === 'ACTION_MODIFIER') {
            const nom = prompt("Nouveau nom pour la rubrique de cette page :");
            if (nom) {
                url.searchParams.set('page_id', pageId);
                url.searchParams.set('action_rubrique', 'modifier');
                url.searchParams.set('nom_rubrique', nom);
                url.hash = 'page-' + pageId;
                window.location.href = url.href;
            } else {
                select.value = ""; 
            }
        }
    };
});

// --- 4. GESTION DU SCROLL AU CHARGEMENT ---
window.addEventListener('load', function() {
    // Si on a une ancre dans l'URL (ex: #page-3)
    if (window.location.hash) {
        const targetId = window.location.hash.substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            const yOffset = -100; 
            const y = targetElement.getBoundingClientRect().top + window.pageYOffset + yOffset;
            window.scrollTo({top: y, behavior: 'instant'});
        }
        return; // On s'arrête là
    }

    // Sinon, restauration du scroll classique
    if (localStorage.getItem('scrollPos')) {
        window.scrollTo(0, parseInt(localStorage.getItem('scrollPos')));
        localStorage.removeItem('scrollPos');
    }
});
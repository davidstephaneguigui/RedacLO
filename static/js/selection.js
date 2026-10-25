// 1. On garde la fonction toggleAll au cas où le HTML l'appelle encore via onclick
window.toggleAll = function(source) {
    const checkboxes = document.querySelectorAll('input[name="article_ids"]');
    for (let i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = source.checked;
    }
};

document.addEventListener('DOMContentLoaded', function() {
    // On cherche la case par son ID (qu'on soit sur Choisir ou Réserver)
    const selectAll = document.getElementById('select-all');
    const checkboxes = document.querySelectorAll('input[name="article_ids"]');

    // Si la case a l'ID "select-all" et qu'il y a des articles, on gère l'événement
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
});

// 2. La fonction pour le bouton Annuler
window.annulerSelection = function() {
    const checkboxes = document.querySelectorAll('input[name="article_ids"]');
    checkboxes.forEach(cb => cb.checked = false);
    
    const selectAll = document.getElementById('select-all');
    if (selectAll) {
        selectAll.checked = false;
    }
};
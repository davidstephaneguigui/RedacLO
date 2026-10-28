# 📰 RedacLO

**RedacLO** est une application web métier complète conçue pour gérer l'intégralité du cycle de vie d'un journal : de la rédaction des articles jusqu'à la mise en page finale, en passant par la relecture, la validation et la composition.

## 🎯 Objectif du projet

L'objectif de RedacLO est de fournir une plateforme centralisée pour une rédaction, permettant de :
- Gérer les rôles (Rédacteurs, Éditeurs, Administrateurs).
- Suivre l'évolution des articles (versions, relectures, validations).
- Composer le journal (Chemin de fer, attribution des articles aux pages).
- Exporter les données pour la mise en page (InDesign).

## 🚀 Fonctionnalités principales

- **Rédaction** : Création d'articles avec versions, gestion des images et brouillons.
- **Relecture** : Système d'annotation avec calcul de différences (diff) et double validation.
- **Composition** : Un "Chemin de fer" interactif pour placer les articles sur les pages, gérer l'ordre, les doubles pages et les compteurs de signes en temps réel.
- **Mise en page** : Export des pages composées vers InDesign au format IDML (via la bibliothèque `simple_idml`).
- **Gestion des numéros** : Tableau de bord des numéros (en cours, gelés, archivés) avec navigation par année.
- **Responsive** : Interface adaptée aux ordinateurs, tablettes et smartphones (menu burger, tableaux en cartes).

## 🏗️ Architecture (Applications Django)

Le projet est divisé en plusieurs applications, chacune ayant une responsabilité unique (Principe de Responsabilité Unique - SRP) :

- `accounts` : Gestion des utilisateurs et des rôles.
- `articles` : Cycle de vie des articles et de leurs versions.
- `reviews` : Processus de relecture et d'annotation.
- `publications` : Composition du journal (Pages, Rubriques, Numéros, Chemin de fer).
- `display` : Mise en page et exports (IDML, LaTeX).
- `core` : Fonctionnalités transverses (Notifications, page d'accueil).

## 🛠️ Stack Technique

- **Backend** : Python 3.10+, Django 5+
- **Base de données** : SQLite (développement)
- **Frontend** : HTML5, CSS3, JavaScript natif (Vanilla JS)
- **Bibliothèques notables** :
  - `Pillow` (gestion des images)
  - `WeasyPrint` (génération de PDF pour la relecture)
  - `simple_idml` (export InDesign)

## ⚙️ Installation et lancement en local

1. **Cloner le dépôt** :
    ```bash
    git clone https://github.com/votre-nom/RedacLO.git
    cd RedacLO

2. **Créer et activer un environnement virtuel**
```bash
    python -m venv .venv
    # Sur Windows :
    .venv\Scripts\activate
    # Sur macOS/Linux :
    source .venv/bin/activate

3. **Installer les dépendances**
    pip install -r requirements.txt


4. **Appliquer les migrations**
    python manage.py makemigrations
    python manage.py migrate


5. **Lancer le serveur de développement**
    python manage.py runserver
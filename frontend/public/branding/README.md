# Logo de l'application

Le fichier `logo.svg` fourni est un **emplacement réservé** (monogramme générique), pas le logo officiel.

Pour installer le logo officiel de la SBEE :

1. Copier le fichier fourni par la communication de la SBEE dans ce dossier (SVG ou PNG transparent, hauteur ≥ 64 px).
2. Soit le nommer `logo.svg` (remplace ce fichier), soit définir `VITE_LOGO_URL` au build du frontend,
   par exemple `VITE_LOGO_URL=/branding/logo-sbee.png`.
   Pour une variante adaptée aux fonds sombres (barre latérale) : `VITE_LOGO_DARK_URL`.
3. Reconstruire le frontend : `docker compose up --build`.

Les couleurs de l'interface se règlent dans `src/theme/tokens.css` (palette provisoire à valider avec la charte officielle).
Aucun composant n'a besoin d'être modifié.

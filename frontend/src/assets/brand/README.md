# Ressources officielles de la charte graphique SBEE

Source : **« CHARTE GRAPHIQUE — Juillet 2023 » (SBEE)**, pages 4 et 5 (logotype, version carrée / symbole).

| Fichier | Contenu | Usage dans l'application |
|---|---|---|
| `logo.png` | Logotype original, **rouge sur fond blanc / clair** | Écran de connexion (carte blanche) |
| `logo-light.png` | Logotype original, **blanc sur fond rouge / foncé** | Barre latérale rouge |
| `symbol.png` | Symbole seul, rouge | Trame décorative sur fond clair (7 % d'opacité) |
| `symbol-light.png` | Symbole seul, blanc | Trame décorative sur fond rouge (7 % d'opacité) |

## Traitement appliqué (extraction uniquement)

Les images de la charte sont des JPEG sur fond uni (blanc ou rouge). Elles ont été **extraites sans modification du dessin** : le fond uni a été rendu transparent par démixage mathématique (le dessin conserve ses couleurs officielles, rouge `#ED1F24` ou blanc) et l'image a été rognée aux limites du dessin avec une marge de 4 %. Proportions, formes et typographie du logotype sont strictement celles de la charte : aucun redessin, aucune déformation, rotation ni recoloration.

## Règles de la charte respectées par `components/ui/Logo.tsx`

- proportions d'origine : hauteur imposée, largeur automatique ;
- version couleur sur fond blanc / clair, version blanche sur fond rouge ; pas de version noire ni négative sur fond noir ;
- zone de protection : le logotype est toujours entouré de marges (carte de connexion, bloc d'en-tête de la barre latérale) ;
- taille minimale à l'écran : 40 px de haut (la charte impose 30 mm de large en impression) ;
- le symbole n'est utilisé qu'en **trame** décorative, opacité 7 % (5 à 10 % imposés), sans jamais gêner la lisibilité ;
- la signature institutionnelle n'est pas utilisée (interface métier sobre).

Pour remplacer un fichier (nouvelle version de la charte), déposer le nouveau fichier sous le même nom (`.svg`, `.png` ou `.webp`) et reconstruire le frontend (`docker compose up --build`) : aucun composant à modifier.

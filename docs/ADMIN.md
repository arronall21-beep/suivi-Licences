# Guide d'administration — V1.1

Ce guide décrit les fonctions réservées aux administrateurs (menu **Administration**) et les règles de sécurité de l'application.

## Rôles et permissions

Les droits sont vérifiés **par le serveur sur chaque requête** ; masquer un bouton dans l'interface n'est jamais une mesure de sécurité. Le changement de rôle, la désactivation ou la réinitialisation du mot de passe d'un compte prennent effet **immédiatement** (les sessions en cours sont refusées).

| Action | VIEWER | MANAGER | ADMIN |
|---|:-:|:-:|:-:|
| Consulter dashboard, actifs, contrats, planning, affectations, notifications | ✓ | ✓ | ✓ |
| Exporter en Excel | ✓ | ✓ | ✓ |
| Créer / modifier actifs, contrats, fournisseurs | — | ✓ | ✓ |
| Affecter / désaffecter une licence | — | ✓ | ✓ |
| Supprimer actifs, contrats, fournisseurs | — | — | ✓ |
| Importer un fichier Excel | — | — | ✓ |
| Lancer le contrôle des alertes | — | — | ✓ |
| Utilisateurs, paramètres, SMTP, journal d'audit, système | — | — | ✓ |

La matrice est définie dans `backend/app/core/permissions.py` et affichée dans **Administration → Utilisateurs → Rôles et permissions**.

## Utilisateurs

- Création, modification, désactivation / réactivation, réinitialisation du mot de passe, recherche et filtres (rôle, statut).
- Champs : nom, prénom, email, téléphone, direction / département, rôle, statut, date de création, dernière connexion.
- Garde-fous : on ne peut ni désactiver son propre compte, ni retirer le rôle ADMIN ou désactiver **le dernier administrateur actif**.
- **Mots de passe** : hachés (bcrypt), jamais affichés ni journalisés. Politique : 8 caractères minimum, au moins une lettre et un chiffre, différent de l'email. Chaque utilisateur peut changer le sien (menu en haut à droite).
- **Connexion** : jeton JWT de 8 h (`ACCESS_TOKEN_EXPIRE_MINUTES`). Après 5 échecs en 15 minutes pour un même couple IP + email, les tentatives sont bloquées temporairement (limiteur en mémoire, par processus).
- **Mot de passe oublié** : la demande depuis l'écran de connexion est signalée aux administrateurs (notification interne) qui réinitialisent le mot de passe. La réponse est identique que le compte existe ou non. *Limite connue : l'envoi d'un lien de réinitialisation par email n'est pas implémenté ; il pourra s'appuyer sur la configuration SMTP.*
- Les comptes initiaux (`ADMIN_*`, `MANAGER_*`, `VIEWER_*` du `.env`) ne sont créés que s'ils n'existent pas : **changer ces mots de passe par défaut** dès la première connexion.

## Références automatiques

Les références `LIC-001`, `CERT-001`, `MAT-001`, `APP-001`, `CTR-001`, `VEN-001` sont générées côté serveur par des **séquences PostgreSQL** : sans collision en cas de créations simultanées, numéros jamais réutilisés après suppression. Le formulaire affiche « Référence générée automatiquement ».

Import Excel : une référence présente dans le fichier est conservée ; une ligne identifiable (nom renseigné) mais sans référence en reçoit une ; une ligne manifestement invalide (ni référence ni nom) est signalée et ignorée sans consommer de numéro. Les références explicites du fichier sont réservées avant toute génération, et un ré-import reconnaît les lignes sans référence par leur nom (pas de doublon).

## Paramètres (Administration → Paramètres)

- **Généraux** : organisation, nom de l'application, devise (code ISO, ex. `XOF` → « FCFA »), fuseau horaire, email administrateur, seuil critique, seuil d'alerte. Ces valeurs pilotent le calcul des statuts, l'affichage, les exports Excel et l'heure du contrôle quotidien. Les valeurs de départ viennent du `.env`.
- **Alertes** : seuils activables (J-90, J-60, J-30, J-7 par défaut, seuils personnalisés possibles), alerte « expiré », destinataires (administrateur, responsable interne, adresses personnalisées). L'idempotence est conservée : une seule notification par élément, seuil et échéance. Le « responsable interne » reçoit uniquement ses alertes, si son nom ou son email correspond à un utilisateur actif.

Les paramètres sont rechargés à chaud (processus unique). Avec plusieurs workers, redémarrer le backend après modification.

## SMTP (Administration → SMTP)

- Serveur, port, sécurité (`NONE`, `STARTTLS`, `SSL/TLS`), utilisateur, mot de passe, expéditeur.
- **Le mot de passe est chiffré en base (Fernet) et n'est jamais renvoyé par l'API** : l'interface affiche `••••••••` ; saisir une valeur le remplace, laisser vide le conserve, une case permet de le supprimer. La clé de chiffrement dérive de `SETTINGS_ENCRYPTION_KEY` (à défaut `SECRET_KEY`) : si elle change, le mot de passe est à ressaisir (l'interface le signale).
- **Tester la connexion** et **Envoyer un email de test** utilisent les valeurs du formulaire (sans les enregistrer) ; les messages d'erreur sont lisibles et ne contiennent jamais d'identifiant.
- Tant qu'aucun serveur n'est configuré, l'interface affiche **SMTP non configuré** ; les alertes restent calculées, tracées dans l'historique et visibles dans les notifications.
- Les variables `SMTP_*` du `.env` servent de valeur de repli.

## Notifications internes

La cloche (en-tête) et la page **Notifications** listent les événements : contrat arrivant à échéance, licence critique, certificat expiré (et variantes), import terminé, erreur d'import, demande de mot de passe. Lu / non lu **par utilisateur**, priorité, date et lien vers l'objet concerné. Les événements d'import et de mot de passe sont réservés aux administrateurs. Le contrôle des échéances s'exécute chaque jour à `ALERT_HOUR` (fuseau configuré), au démarrage du backend (rattrapage, idempotent) et à la demande depuis la page Notifications.

## Journal d'audit

Écriture seule, consultable par les administrateurs (recherche, filtres action / utilisateur / entité / résultat / dates, pagination). Chaque entrée : utilisateur, action, entité, identifiant, date/heure, adresse IP (indicative, issue de `X-Forwarded-For` derrière nginx), résultat. Actions tracées : connexions (réussies et échouées), utilisateurs (création, modification, rôle, désactivation, réactivation, réinitialisation), paramètres, alertes, SMTP (et tests), imports et exports Excel, actifs, contrats, fournisseurs, affectations et désaffectations. Les secrets (mots de passe, clés) n'y figurent jamais : seuls les noms des champs modifiés sont conservés.

## Import / export

L'historique des imports (date, utilisateur, fichier, taille, lignes analysées / importées / ignorées, avertissements, erreurs, statut) conserve aussi les imports refusés ; chaque rapport détaillé reste consultable. Exports : inventaire complet (7 onglets du gabarit), licences, contrats, échéances (expirés / critiques / alerte), planning de renouvellement.

## Système et sauvegarde

**Administration → Système** : version (`v1.1.0`), état de la base, SMTP, planificateur, utilisateurs actifs / désactivés, dernier import, dernière alerte envoyée, dernière sauvegarde.

L'application ne produit pas de sauvegarde elle-même. Le script `scripts/backup.sh` crée un dump compressé dans `./backups` (rétention `BACKUP_KEEP_DAYS`, 14 jours par défaut) ; ce dossier est monté en lecture seule dans le backend, qui en affiche le dernier fichier et alerte au-delà de 48 h. Planification suggérée (cron) : `0 2 * * * cd /chemin/suivi-Licences && ./scripts/backup.sh >> backups/backup.log 2>&1`. Restauration : `gunzip -c backups/<fichier>.sql.gz | docker compose exec -T postgres psql -U suivi suivi_licences`. Ce n'est pas un plan de reprise d'activité complet (copie hors site et test de restauration à prévoir).

## Charte graphique SBEE

L'interface applique la **charte graphique officielle SBEE (Juillet 2023)**.

- **Couleurs** : toutes définies dans `frontend/src/theme/tokens.css` (aucune valeur codée en dur dans les composants). Couleurs officielles : rouge `#ED1F24` (dominante : barre latérale, boutons, états actifs, fond de connexion), blanc `#FFFFFF` ; association : jaune `#F9A825` (avertissement, repère d'état actif), vert `#00CC66` (succès), bleu `#3B5998` (information) ; neutres : gris clair `#C0C0C0`, gris foncé `#555555` (texte), noir `#000000`. Les nuances intermédiaires (survol, fonds légers, textes lisibles sur fond blanc) en sont déduites ; seul le niveau « critique » des échéances utilise une teinte orange intermédiaire (rouge → jaune), absente de la charte, pour distinguer quatre niveaux de statut.
- **Typographie** : Poppins (police de marque), auto-hébergée via `@fontsource/poppins` (4 graisses latines, ≈ 32 Ko, aucun service externe) ; Century Gothic en repli.
- **Logo** : logotype officiel extrait de la charte (`frontend/src/assets/brand/`, voir son README), version blanche sur la barre latérale rouge, version couleur sur la carte de connexion. Symbole utilisé uniquement en trame décorative à 7 % d'opacité (connexion, dashboard, états vides).
- **Contrastes** (WCAG) : texte courant ≥ 5,1:1, badges ≥ 5,7:1, liens rouges 7,4:1. Seul le blanc sur le rouge officiel (barre latérale, boutons) fait 4,35:1 : inhérent à la couleur imposée par la charte, au-dessus du seuil de 3:1 des composants d'interface et du texte en gras, légèrement sous 4,5:1 pour le texte normal.
- **Affichage** : conçu pour poste de travail. Aucun débordement de page de 1024 à 1440 px ; à 1440 px aucun tableau ne défile, entre 1024 et 1280 px les tableaux les plus larges (licences, contrats) défilent horizontalement dans leur carte. Pas de mise en page mobile.

## Mise à jour depuis la V1.0

`docker compose up --build` applique automatiquement les migrations Alembic 0002 à 0005 : séquences de références initialisées à partir des données existantes, références fournisseurs `VEN-xxx` rétro-remplies, nouvelles colonnes utilisateurs, tables de paramètres, d'audit et de notifications. Les données, comptes et mots de passe existants sont conservés ; les jetons émis avant la mise à jour restent valables jusqu'à leur expiration. Les comptes existants sont `ADMIN` / `VIEWER` ; ajouter les gestionnaires depuis l'interface.

# Suivi Licences SI — Gestion du Patrimoine SI (V1.1)

Application web de **gestion, suivi et pilotage** des licences logicielles, certificats, matériels, applications et contrats fournisseurs du SI.
Le fichier métier `Suivi_Licence.xlsx` sert de source de référence : il est importé en base PostgreSQL, enrichi dans l'application, puis ré-exporté dans le même format.

## Fonctionnalités

| Domaine | Contenu |
|---|---|
| **Import Excel** | Détection des onglets et des en-têtes (libellés tolérants), normalisation des dates et montants, cellules vides, doublons, formules. **UPSERT** par référence, aucune suppression. Rapport : lignes analysées / importées / ignorées, avertissements, erreurs. |
| **Dashboard** | KPIs (actifs, licences, certificats, matériels, applications, contrats), échéances (expirés / ≤ 30 j / ≤ 90 j), utilisation des licences, finances, graphiques, prochains renouvellements. Tout est calculé depuis la base. |
| **Actifs** | Modèle unifié LICENCE / CERTIFICAT / MATERIEL / APPLICATION. Liste avec recherche, tri, pagination et filtres (catégorie, statut, criticité, direction, fournisseur). Fiche détaillée, CRUD en modales. |
| **Cycle de vie** | `days_remaining` et `status` **calculés** (jamais stockés) dans `backend/app/core/lifecycle.py` : EXPIRÉ ≤ 0 j, CRITIQUE 1–30 j, ALERTE 31–90 j, OK > 90 j. Matériels : échéance = fin de contrat, sinon fin de support, sinon fin de garantie. |
| **Affectations** | Affectation de licences à un utilisateur, un poste ou une direction. Règle `SUM(quantity) ≤ total_quantity` (verrou de ligne). Quantité affectée, quantité disponible, taux d'utilisation. |
| **Contrats** | CRUD, préavis, `renewal_start_date = end_date − notice_period_days`, indicateur « préavis atteint ». |
| **Renouvellements** | Planning mensuel unifié actifs + contrats, horizons de 30 j à 24 mois, priorité P1/P2/P3, budget. |
| **Alertes** | Job APScheduler quotidien. Seuils J-90 / J-60 / J-30 / J-7, plus les éléments expirés. Email de synthèse via SMTP. Historique anti-doublon : une notification par élément, seuil et échéance. Bouton « Lancer le contrôle maintenant ». |
| **Export Excel** | Les 7 onglets métier (`Licences_Logicielles`, `Certificats`, `Materiels`, `Applications`, `Contrats_Fournisseurs`, `Planning_Renouvellement`, `Dashboard`). Dates JJ/MM/AAAA, statuts colorés, fichier ré-importable. |
| **Administration (V1.1)** | Utilisateurs et rôles **ADMIN / MANAGER / VIEWER** (RBAC vérifié côté serveur), paramètres généraux (organisation, devise, fuseau, seuils), **SMTP configurable depuis l'interface** (mot de passe chiffré, tests), configuration des alertes, journal d'audit, notifications internes, état du système et de la sauvegarde. Voir [docs/ADMIN.md](docs/ADMIN.md). |
| **Références automatiques** | `LIC-001`, `CERT-001`, `MAT-001`, `APP-001`, `CTR-001`, `VEN-001` générées côté serveur par séquences PostgreSQL. |
| **Charte SBEE** | Identité conforme à la charte graphique officielle (rouge `#ED1F24`, Poppins, logotype officiel, trame du symbole), design system centralisé (`frontend/src/theme`, `components/ui`). Voir [docs/ADMIN.md](docs/ADMIN.md). |
| **Sécurité** | JWT à durée limitée et invalidable immédiatement, mots de passe hachés (bcrypt) avec politique minimale, limitation des échecs de connexion, secrets chiffrés en base, CORS, validation Pydantic, limite de taille d'upload, erreurs centralisées. |

## Architecture

```text
Navigateur ──► frontend (React + Vite + Tailwind, servi par nginx :8080)
                   │  /api/* (reverse proxy)
                   ▼
               backend (FastAPI, SQLAlchemy async, APScheduler :8000) ──► SMTP
                   │
                   ▼
               PostgreSQL 16 (volume pgdata)        adminer (debug, 127.0.0.1:8081)
```

```text
backend/app/
  api/        routes REST (auth, vendors, contracts, assets, assignments, reporting)
  core/       config (.env), sécurité JWT, lifecycle (règles d'échéance centralisées)
  models/     modèles SQLAlchemy
  schemas/    schémas Pydantic v2
  services/   import/export Excel, dashboard, affectations, notifications
  jobs/       planificateur APScheduler
backend/alembic/   migrations
backend/tests/     tests pytest (lifecycle, import/export, API)
backend/scripts/   générateur du fichier de démonstration
frontend/src/      pages, composants, client API
data/              Suivi_Licence.xlsx (jeu de démonstration)
```

## Prérequis

- Docker et Docker Compose v2
- Pour le développement local, en option : Python 3.11, Node 20+, PostgreSQL 15+

## Installation et lancement (Docker)

```bash
cp .env.example .env        # puis adapter SECRET_KEY, mots de passe, SMTP…
docker compose up --build
```

| Service | URL |
|---|---|
| Application | http://localhost:8080 |
| API (Swagger) | http://localhost:8000/api/docs |
| Santé | http://localhost:8000/api/v1/health |
| Adminer (debug) | http://127.0.0.1:8081 (serveur `postgres`) |

Les migrations Alembic s'appliquent automatiquement au démarrage du backend.
Comptes créés au premier lancement (à changer dans `.env`) :

- `admin@example.com` / `admin123` : administrateur
- `manager@example.com` / `manager123` : gestionnaire (écriture des données métier, sans administration)
- `viewer@example.com` / `viewer123` : lecture seule

Ensuite, gérer les comptes depuis **Administration → Utilisateurs** (rôles, désactivation, réinitialisation).

> Adminer n'est exposé que sur `127.0.0.1`. Ne pas le publier en production : retirer le service ou le placer derrière un accès restreint.

## Configuration `.env`

| Variable | Rôle |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Base PostgreSQL |
| `SECRET_KEY` | Clé de signature JWT (**obligatoire en production**) |
| `SETTINGS_ENCRYPTION_KEY` | Clé de chiffrement des secrets en base (mot de passe SMTP) ; vide = dérivée de `SECRET_KEY` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de session |
| `ADMIN_*`, `MANAGER_*`, `VIEWER_*` (`EMAIL`, `PASSWORD`) | Comptes initiaux (créés s'ils n'existent pas) : **à changer** |
| `ORGANIZATION_NAME`, `APPLICATION_NAME`, `CURRENCY`, `DEFAULT_TIMEZONE`, `CRITICAL_DAYS`, `ALERT_DAYS` | Valeurs de départ des paramètres généraux (ensuite modifiables dans Administration → Paramètres) |
| `CORS_ORIGINS` | Origines autorisées, séparées par des virgules |
| `MAX_UPLOAD_MB` | Taille maximale du fichier Excel (10 Mo par défaut) |
| `BACKUP_DIR` | Répertoire des sauvegardes lu par Administration → Système (`./backups` monté dans le conteneur) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `SMTP_SECURITY` | Valeurs de repli pour l'envoi des alertes : la configuration saisie dans **Administration → SMTP** est prioritaire |
| `ALERT_RECIPIENTS` | Adresses personnalisées de départ pour les alertes (ensuite : Administration → Paramètres) |
| `ALERT_THRESHOLDS` | Seuils en jours (`90,60,30,7`) |
| `ALERT_HOUR`, `SCHEDULER_ENABLED` | Heure du job quotidien (Europe/Paris), activation |
| `FRONTEND_PORT`, `BACKEND_PORT`, `ADMINER_PORT` | Ports exposés |

Aucun secret n'est présent dans le code : tout passe par `.env`, qui est ignoré par git.

## Import Excel

Depuis l'interface : **Import / Export → déposer `Suivi_Licence.xlsx` → Lancer l'import**. Par l'API :

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login -H 'content-type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}' | jq -r .access_token)
curl -X POST localhost:8000/api/v1/import/excel -H "Authorization: Bearer $TOKEN" -F file=@data/Suivi_Licence.xlsx
```

Règles appliquées :

- Onglets reconnus par leur nom ou un alias (`Licences`, `Contrats`…). Onglets manquants ou inconnus : avertissement, sans blocage.
- Ligne d'en-têtes recherchée dans les 15 premières lignes. Les colonnes sont reconnues par libellé ou alias (`Réf.`, `Editeur`, `Nb licences`, `Date d'expiration`…).
- Colonnes calculées (`Jours restants`, `Statut`, `Taux`…) ignorées, puis recalculées par l'application.
- Date invalide : champ laissé vide et avertissement, la ligne est importée.
- Doublon de référence dans le fichier : première occurrence conservée, la suivante est signalée.
- Référence manquante : générée à partir du nom, avec avertissement. Ligne sans référence ni nom : erreur, ligne ignorée.
- `Quantité utilisée` d'une licence : crée une affectation globale « reprise Excel » si la licence n'en a aucune (ré-import idempotent). Une sur-allocation présente dans Excel est plafonnée et signalée.
- Contrat référencé mais absent de l'onglet contrats : créé avec des informations minimales et signalé.
- Fournisseurs créés automatiquement, sans doublon (comparaison insensible à la casse et aux accents).
- Chaque import est historisé avec son rapport complet.

> `data/Suivi_Licence.xlsx` est le fichier métier réel. Un jeu de démonstration au même format, avec des anomalies volontaires, peut être généré par `python backend/scripts/generate_demo_excel.py <chemin_sortie>`.

## Export Excel

**Import / Export → Télécharger l'export Excel**, ou `GET /api/v1/export/excel`. Le classeur reprend les onglets et l'ordre des colonnes ; il est directement ré-importable.

## API (principaux endpoints, préfixe `/api/v1`)

```text
GET  /health                    POST /auth/login           GET /auth/me
GET|POST /vendors               GET|PUT|DELETE /vendors/{id}
GET|POST /contracts             GET|PUT|DELETE /contracts/{id}
GET|POST /assets                GET|PUT|DELETE /assets/{id}     GET /assets/options
GET|POST /assignments           PUT|DELETE /assignments/{id}
POST /import/excel              GET /import/history[/{id}]      GET /export/excel
GET  /dashboard                 GET /renewals?horizon_days=365
GET  /alerts                    POST /alerts/run                GET /notifications
```

Documentation interactive : `/api/docs`.

## Configuration SMTP

Depuis l'interface (recommandé) : **Administration → SMTP** (serveur, port, sécurité NONE / STARTTLS / SSL-TLS, utilisateur, mot de passe, expéditeur), avec **Tester la connexion** et **Envoyer un email de test**. Le mot de passe est chiffré en base et jamais renvoyé par l'API. Destinataires et seuils : **Administration → Paramètres → Alertes d'échéance**.

Les variables `SMTP_*` du `.env` ne servent que de valeur de repli. Sans SMTP, l'interface affiche « SMTP non configuré » ; les alertes sont tout de même calculées et tracées (`NON_ENVOYE`) et visibles dans les notifications. Le contrôle tourne chaque jour à `ALERT_HOUR` (fuseau des paramètres), au démarrage du backend, et à la demande depuis **Notifications → Alertes d'échéance**.

## Tests

```bash
# Backend : nécessite un PostgreSQL de test (base suivi_test)
cd backend
pip install -r requirements-dev.txt
DATABASE_URL=postgresql+asyncpg://suivi:suivi@localhost:5432/suivi_test pytest -q
ruff check .

# Dans Docker (base de test créée dans le conteneur postgres)
docker compose exec postgres createdb -U suivi suivi_test
docker compose exec -e DATABASE_URL=postgresql+asyncpg://suivi:${POSTGRES_PASSWORD}@postgres:5432/suivi_test backend pytest -q

# Frontend
cd frontend && npm ci && npm run build
```

Couverture des tests (backend : 89 tests) : références automatiques (format, unicité, suppression, concurrence, import), utilisateurs et rôles (création, désactivation immédiate, dernier administrateur, politique de mot de passe, limitation des échecs), matrice RBAC rôle × endpoint, paramètres généraux et seuils dynamiques, SMTP (chiffrement, secret jamais exposé, tests de connexion et d'email), alertes configurables et idempotentes, audit, notifications internes, historique d'import, exports par périmètre, top des risques, recherche, système ; puis, historiquement : import valide, onglet manquant, date invalide, doublons, ré-import (UPSERT), aller-retour export → import ; lifecycle OK / ALERTE / CRITIQUE / EXPIRÉ et seuils d'alerte ; affectations (valide, sur-allocation refusée, quantité disponible, taux d'utilisation) ; CRUD, droits ADMIN/VIEWER, dashboard, renouvellements, alertes sans doublon, health.

## Développement local (sans Docker)

```bash
# Backend
cd backend && python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
export DATABASE_URL=postgresql+asyncpg://suivi:suivi@localhost:5432/suivi_licences
alembic upgrade head && uvicorn app.main:app --reload

# Frontend (proxy /api vers localhost:8000)
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Scénario de démonstration pas à pas : [docs/DEMO.md](docs/DEMO.md). Guide d'administration (rôles, SMTP, audit, sauvegarde, logo) : [docs/ADMIN.md](docs/ADMIN.md).

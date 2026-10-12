# Déploiement initial SBEE — v1.1.1-demo (commit `c977c51`)

Serveur cible : Ubuntu 24.04, Docker Engine + Compose v2+. Une seule instance (pas de haute disponibilité).
Services (noms vérifiés dans `docker-compose.yml`) : `postgres`, `backend`, `frontend` (nginx, seul service publié), `adminer` (exclu en production).

## 0. Principes
- PostgreSQL n'est **jamais** publié ; le backend n'est **pas** publié (le frontend nginx proxifie `/api/` vers `backend:8000` sur le réseau Docker) ; Adminer est exclu (profil `debug`).
- Les données vivent dans le volume nommé `suivi-licences_pgdata`. **Ne jamais exécuter `docker compose down -v`**, ni `docker volume rm`, ni `docker system prune --volumes`.
- Aucune donnée de démonstration : la base démarre vide (migrations Alembic 0001→0005 au démarrage du backend). Seul le compte ADMIN défini dans `.env` est créé.

## 1. Récupérer le code
```bash
sudo mkdir -p /opt/sbee-si && sudo chown "$USER" /opt/sbee-si
git clone https://github.com/arronall21-beep/suivi-Licences.git /opt/sbee-si/app
cd /opt/sbee-si/app
git checkout --detach v1.1.1-demo
test "$(git rev-parse HEAD)" = "c977c5147cfc277e889e5d50b4f82ecf821da11a" && echo "commit OK"
# Fichiers de déploiement (aucun code applicatif) :
git checkout origin/deploy/sbee-v1.1.1 -- docker-compose.prod.yml .env.production.example scripts/preflight.sh scripts/restore.sh docs/DEPLOY.md
```

## 2. Configuration
```bash
cp .env.production.example .env && chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"   # → SECRET_KEY ; relancer pour SETTINGS_ENCRYPTION_KEY et POSTGRES_PASSWORD
nano .env                                                        # remplacer toutes les valeurs <A_DEFINIR>
./scripts/preflight.sh                                           # doit afficher « Preflight OK »
```
Sauvegarder `SECRET_KEY` et `SETTINGS_ENCRYPTION_KEY` dans le coffre de la DSI (hors serveur) : sans elles, le mot de passe SMTP chiffré en base est irrécupérable.

## 3. Construire et démarrer
```bash
docker compose build
docker compose up -d
docker compose ps                       # postgres, backend, frontend : healthy
docker compose logs backend | grep -iE "alembic|Utilisateur|ERROR"
docker compose exec backend alembic current          # attendu : 0005 (head)
mkdir -p backups && chmod 700 backups
```

## 4. Vérifications
```bash
curl -fsS http://localhost/api/v1/health                      # {"status":"ok"...}
curl -fsS -o /dev/null -w "%{http_code}\n" http://localhost/  # 200
ss -tlnp | grep -E ':(5432|8000|8081)\b' || echo "OK : PostgreSQL / backend / Adminer non exposés"
# Depuis un poste du réseau utilisateur : seul le port du frontend doit répondre (nmap -p 80,443,5432,8000,8081 <serveur>)
```
Puis dans le navigateur : connexion ADMIN, **Administration → Utilisateurs** (créer les comptes nominatifs), **Paramètres**, **SMTP** (test de connexion + email de test), **Système** (état de la base, dernière sauvegarde).

## 5. Sauvegarde
```bash
./scripts/backup.sh                                  # dump compressé dans ./backups (rétention BACKUP_KEEP_DAYS)
./scripts/restore.sh backups/<fichier>.sql.gz --verify   # prouve que la sauvegarde est restaurable (base temporaire, supprimée ensuite)
# Planification quotidienne (crontab -e) :
0 2 * * * cd /opt/sbee-si/app && ./scripts/backup.sh >> backups/backup.log 2>&1
```
À prévoir par la DSI : copie hors serveur des dumps **et** du `.env` (séparément, chiffrée), test de restauration périodique. Les dumps contiennent les empreintes de mots de passe et le journal d'audit : accès restreint.

## 6. Retour arrière
- **Avant toute mise à jour** : `./scripts/backup.sh`.
- **Code** : `git checkout --detach <tag précédent> && docker compose build && docker compose up -d`.
- **Base** (si le schéma a changé ou si les données sont altérées) : `./scripts/restore.sh backups/<fichier>.sql.gz --live` (sauvegarde de sécurité automatique, arrêt du backend/frontend, confirmation « RESTAURER » exigée). Les migrations Alembic ne sont pas garanties réversibles : privilégier la restauration.
- v1.1.1 n'ajoute aucune migration par rapport à v1.1.0 (head = 0005).

## 7. Exploitation courante
```bash
docker compose ps && docker compose logs --tail=100 backend
docker compose restart backend          # sans perte de données
docker compose down                     # arrêt (le volume est conservé) — JAMAIS « down -v »
docker compose --profile debug up -d adminer   # diagnostic ponctuel, écoute 127.0.0.1:8081 ; accès via tunnel SSH ; l'arrêter ensuite
```

#!/usr/bin/env bash
# Sauvegarde de la base PostgreSQL dans ./backups (affichée dans Administration → Système).
# Usage : ./scripts/backup.sh            (depuis la racine du dépôt, stack démarrée)
# Planification (cron, tous les jours à 02:00) :
#   0 2 * * * cd /chemin/vers/suivi-Licences && ./scripts/backup.sh >> backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
DB="${POSTGRES_DB:-suivi_licences}"
USER_DB="${POSTGRES_USER:-suivi}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
mkdir -p backups
FILE="backups/${DB}_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose exec -T postgres pg_dump -U "$USER_DB" --no-owner "$DB" | gzip > "$FILE"
[ -s "$FILE" ] || { echo "Sauvegarde vide : échec" >&2; rm -f "$FILE"; exit 1; }
find backups -name "${DB}_*.sql.gz" -mtime +"$KEEP_DAYS" -delete
echo "Sauvegarde créée : $FILE ($(du -h "$FILE" | cut -f1))"

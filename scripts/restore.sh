#!/usr/bin/env bash
# Restauration d'une sauvegarde produite par scripts/backup.sh.
#   ./scripts/restore.sh <fichier.sql.gz> --verify   Restaure dans une base TEMPORAIRE, contrôle, puis la supprime
#                                                      (n'affecte pas la base en service). À faire après chaque sauvegarde type.
#   ./scripts/restore.sh <fichier.sql.gz> --live     Retour arrière : remplace la base en service par la sauvegarde
#                                                      (sauvegarde de sécurité préalable, arrêt du backend, confirmation requise).
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
DB="${POSTGRES_DB:-suivi_licences}"; USER_DB="${POSTGRES_USER:-suivi}"
FILE="${1:-}"; MODE="${2:-}"
[ -f "$FILE" ] && [ -n "$MODE" ] || { sed -n 2,8p "$0"; exit 2; }
gzip -t "$FILE" || { echo "Archive corrompue : $FILE" >&2; exit 1; }
psql_() { docker compose exec -T postgres psql -U "$USER_DB" -v ON_ERROR_STOP=1 "$@"; }

case "$MODE" in
  --verify)
    TMP="restore_check_$(date +%s)"
    psql_ -d postgres -c "CREATE DATABASE $TMP" >/dev/null
    trap 'psql_ -d postgres -c "DROP DATABASE IF EXISTS '"$TMP"'" >/dev/null' EXIT
    gunzip -c "$FILE" | psql_ -q -d "$TMP" >/dev/null
    echo "Version de schéma : $(psql_ -d "$TMP" -Atc 'SELECT version_num FROM alembic_version')"
    for t in users assets contracts vendors license_assignments audit_logs import_logs; do
      n=$(psql_ -d "$TMP" -Atc "SELECT count(*) FROM $t" 2>/dev/null || echo "?")
      echo "  $t : $n"
    done
    echo "Vérification OK : la sauvegarde est restaurable (base temporaire supprimée)."
    ;;
  --live)
    echo "ATTENTION : la base '$DB' va être REMPLACÉE par $FILE."
    read -r -p "Tapez RESTAURER pour confirmer : " ok; [ "$ok" = "RESTAURER" ] || { echo "Annulé."; exit 1; }
    ./scripts/backup.sh   # sauvegarde de sécurité de l'état actuel
    docker compose stop backend frontend
    psql_ -d postgres -c "DROP DATABASE \"$DB\" WITH (FORCE)" -c "CREATE DATABASE \"$DB\" OWNER \"$USER_DB\""
    gunzip -c "$FILE" | psql_ -q -d "$DB" >/dev/null
    docker compose up -d backend frontend
    echo "Restauration terminée. Vérifier : curl -fsS http://localhost:\${FRONTEND_PORT:-80}/api/v1/health"
    ;;
  *) sed -n 2,8p "$0"; exit 2 ;;
esac

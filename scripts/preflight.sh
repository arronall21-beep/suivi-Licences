#!/usr/bin/env bash
# Contrôle de la configuration de production AVANT le premier démarrage (aucune écriture, aucun secret affiché).
# Usage : ./scripts/preflight.sh   (depuis la racine du dépôt, .env présent)
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0
err() { echo "ERREUR : $*" >&2; fail=1; }
[ -f .env ] || { echo "ERREUR : .env absent (copier .env.production.example)" >&2; exit 1; }
perm=$(stat -c %a .env); [ "$perm" = "600" ] || err ".env doit être en chmod 600 (actuel : $perm)"
get() { grep -E "^$1=" .env | tail -n1 | cut -d= -f2-; }
for k in POSTGRES_PASSWORD SECRET_KEY SETTINGS_ENCRYPTION_KEY ADMIN_EMAIL ADMIN_PASSWORD CORS_ORIGINS; do
  v=$(get "$k"); case "$v" in ""|"<A_DEFINIR"*) err "$k non défini" ;; esac
done
[ "$(get ENVIRONMENT)" = "production" ] || err "ENVIRONMENT doit valoir production"
case "$(get SECRET_KEY)" in change-me*) err "SECRET_KEY par défaut" ;; esac
sk=$(get SECRET_KEY); [ "${#sk}" -ge 32 ] || err "SECRET_KEY trop courte (32 caractères minimum)"
pw=$(get POSTGRES_PASSWORD); [ "${#pw}" -ge 16 ] || err "POSTGRES_PASSWORD trop court (16 caractères minimum)"
ap=$(get ADMIN_PASSWORD); [ "${#ap}" -ge 12 ] || err "ADMIN_PASSWORD trop court (12 caractères minimum recommandés)"
case "$ap" in admin123|change-me*) err "ADMIN_PASSWORD par défaut" ;; esac
[ "$(get ADMIN_EMAIL)" = "admin@example.com" ] && err "ADMIN_EMAIL par défaut (admin@example.com)"
for k in MANAGER_EMAIL MANAGER_PASSWORD VIEWER_EMAIL VIEWER_PASSWORD; do
  [ -z "$(get "$k")" ] || err "$k doit être vide en production (comptes de démonstration)"
done
case "$(get COMPOSE_FILE)" in *docker-compose.prod.yml*) ;; *) err "COMPOSE_FILE doit inclure docker-compose.prod.yml" ;; esac
if command -v docker >/dev/null; then
  docker compose config >/dev/null 2>&1 || err "docker compose config invalide"
  docker compose config 2>/dev/null | grep -qE '^\s+published: "?(5432|8081)"?' && err "PostgreSQL ou Adminer publié sur l'hôte"
fi
[ "$fail" -eq 0 ] && echo "Preflight OK" || { echo "Preflight ÉCHEC" >&2; exit 1; }

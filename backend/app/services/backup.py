"""Information sur la dernière sauvegarde connue : lecture seule d'un répertoire de dépôt (BACKUP_DIR).

L'application ne crée pas de sauvegarde (le conteneur backend n'embarque pas pg_dump) : le script
`scripts/backup.sh` du dépôt produit des dumps dans ./backups, monté en lecture seule dans le backend.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

PATTERNS = ("*.sql", "*.sql.gz", "*.dump", "*.backup", "*.dump.gz")
STALE_AFTER_HOURS = 48


def latest_backup() -> dict:
    directory = Path(settings.backup_dir)
    if not directory.is_dir():
        return {"status": "NON_CONFIGURE", "message": "Répertoire de sauvegarde absent", "directory": str(directory)}
    files = [f for pattern in PATTERNS for f in directory.glob(pattern) if f.is_file()]
    if not files:
        return {"status": "AUCUN", "message": "Aucune sauvegarde détectée", "directory": str(directory)}
    newest = max(files, key=lambda f: f.stat().st_mtime)
    stat = newest.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - modified).total_seconds() / 3600
    return {
        "status": "OK" if age_hours <= STALE_AFTER_HOURS else "ANCIEN",
        "message": "Dernière sauvegarde récente"
        if age_hours <= STALE_AFTER_HOURS
        else f"Dernière sauvegarde datant de plus de {STALE_AFTER_HOURS} h",
        "directory": os.fspath(directory),
        "filename": newest.name,
        "size_bytes": stat.st_size,
        "modified_at": modified,
        "age_hours": round(age_hours, 1),
        "count": len(files),
    }

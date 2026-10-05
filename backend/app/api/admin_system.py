import platform
import time

from fastapi import APIRouter
from sqlalchemy import func, select, text

from app.api.deps import DB, AdminUser
from app.core.config import settings
from app.jobs import scheduler as sched
from app.models import ImportLog, User
from app.services import app_settings, backup
from app.services.notifications import last_email_alert
from app.version import VERSION

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/system")
async def system_info(db: DB, _: AdminUser):
    started = time.perf_counter()
    db_version = (await db.execute(text("SHOW server_version"))).scalar_one()
    latency_ms = round((time.perf_counter() - started) * 1000, 1)

    counts = dict((await db.execute(select(User.is_active, func.count()).group_by(User.is_active))).all())
    smtp_cfg, smtp_source, smtp_warning = await app_settings.get_smtp_config(db)
    general = await app_settings.get_general(db)
    last_import = (await db.execute(select(ImportLog).order_by(ImportLog.id.desc()).limit(1))).scalar_one_or_none()
    last_alert = await last_email_alert(db)
    next_run = sched.next_run()
    return {
        "version": VERSION,
        "environment": settings.environment,
        "python": platform.python_version(),
        "timezone": general["timezone"],
        "database": {"status": "ok", "version": db_version, "latency_ms": latency_ms},
        "smtp": {
            "configured": smtp_cfg.configured,
            "source": smtp_source,
            "host": smtp_cfg.host or None,
            "port": smtp_cfg.port if smtp_cfg.host else None,
            "security": smtp_cfg.security if smtp_cfg.host else None,
            "warning": smtp_warning,
        },
        "users": {"active": counts.get(True, 0), "inactive": counts.get(False, 0)},
        "last_import": None
        if last_import is None
        else {
            "id": last_import.id,
            "filename": last_import.filename,
            "status": last_import.status,
            "rows_imported": last_import.rows_imported,
            "imported_by": last_import.imported_by,
            "created_at": last_import.created_at,
        },
        "last_alert_sent": None
        if last_alert is None
        else {"created_at": last_alert.created_at, "recipients": last_alert.recipients, "target": last_alert.target_reference},
        "scheduler": {
            "enabled": settings.scheduler_enabled,
            "running": sched.scheduler.running,
            "next_run": next_run,
            "hour": settings.alert_hour,
        },
        "backup": backup.latest_backup(),
    }

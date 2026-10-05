import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import DB, AdminUser, CurrentUser, ImporterUser
from app.core.config import settings
from app.models import ImportLog, Notification
from app.schemas import NotificationOut
from app.services import app_settings, inbox
from app.services.audit import Audit
from app.services.dashboard import build_dashboard, filter_renewals, load_all, renewal_items
from app.services.excel_export import export_workbook
from app.services.excel_import import ImportFileError, import_workbook
from app.services.notifications import pending_alerts, run_alerts

router = APIRouter()
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/dashboard", tags=["dashboard"])
async def dashboard(db: DB, _: CurrentUser):
    return await build_dashboard(db)


@router.get("/renewals", tags=["renewals"])
async def renewals(
    db: DB,
    _: CurrentUser,
    horizon_days: int | None = Query(365, ge=1, le=3650),
    type: str | None = None,
    status: str | None = None,
):
    assets, contracts = await load_all(db)
    items = filter_renewals(renewal_items(assets, contracts), horizon_days)
    if type:
        items = [i for i in items if i["type"] == type.upper()]
    if status:
        items = [i for i in items if i["status"] == status]
    return items


async def _record_failed_import(db, user, filename: str, size: int | None, message: str) -> None:
    """Un import refusé reste visible dans l'historique et dans la cloche des administrateurs."""
    actor = user.email  # lu avant le rollback, qui expire l'objet user
    await db.rollback()
    db.add(
        ImportLog(
            filename=(filename or "?")[:255],
            status="FAILED",
            file_size=size,
            errors_count=1,
            imported_by=actor,
            report=json.dumps(
                {"filename": filename, "error": message, "errors": [{"sheet": "-", "row": None, "message": message}]},
                ensure_ascii=False,
            ),
        )
    )
    await inbox.create_notification(
        db, "IMPORT_ERROR", f"Erreur d'import : {filename}", message, priority="HIGH", link="/import-export", audience="ADMIN"
    )
    await db.commit()


@router.post("/import/excel", tags=["import-export"])
async def import_excel(file: UploadFile, db: DB, user: ImporterUser, audit: Audit):
    filename = file.filename or "fichier"
    if not filename.lower().endswith((".xlsx", ".xlsm")):
        await audit.log(user, "IMPORT_EXCEL", "IMPORT", None, filename, result="FAILURE", details="format non supporté")
        await _record_failed_import(db, user, filename, None, "Format attendu : fichier Excel .xlsx")
        raise HTTPException(415, "Format attendu : fichier Excel .xlsx")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        msg = f"Fichier trop volumineux (max {settings.max_upload_mb} Mo)"
        await audit.log(user, "IMPORT_EXCEL", "IMPORT", None, filename, result="FAILURE", details=msg)
        await _record_failed_import(db, user, filename, len(content), msg)
        raise HTTPException(413, msg)
    try:
        result = await import_workbook(db, content, filename, user.email, file_size=len(content))
    except ImportFileError as exc:
        await audit.log(user, "IMPORT_EXCEL", "IMPORT", None, filename, result="FAILURE", details=str(exc))
        await _record_failed_import(db, user, filename, len(content), str(exc))
        raise HTTPException(422, str(exc)) from None
    summary = {k: result[k] for k in ("rows_analyzed", "rows_imported", "rows_skipped", "warnings_count", "errors_count")}
    await audit.log(user, "IMPORT_EXCEL", "IMPORT", None, filename, details=summary)
    clean = result["errors_count"] == 0
    await inbox.create_notification(
        db,
        "IMPORT_DONE",
        f"Import terminé : {filename}",
        f"{result['rows_imported']} ligne(s) importée(s) sur {result['rows_analyzed']}, {result['rows_skipped']} ignorée(s), "
        f"{result['warnings_count']} avertissement(s), {result['errors_count']} erreur(s).",
        priority="LOW" if clean else "MEDIUM",
        link="/import-export",
        audience="ADMIN",
    )
    await db.commit()
    return result


@router.get("/import/history", tags=["import-export"])
async def import_history(db: DB, _: CurrentUser, limit: int = Query(20, ge=1, le=100)):
    logs = (await db.execute(select(ImportLog).order_by(ImportLog.id.desc()).limit(limit))).scalars().all()
    return [
        {
            "id": lg.id,
            "filename": lg.filename,
            "file_size": lg.file_size,
            "status": lg.status,
            "rows_analyzed": lg.rows_analyzed,
            "rows_imported": lg.rows_imported,
            "rows_skipped": lg.rows_skipped,
            "warnings_count": lg.warnings_count,
            "errors_count": lg.errors_count,
            "imported_by": lg.imported_by,
            "created_at": lg.created_at,
        }
        for lg in logs
    ]


@router.get("/import/history/{log_id}", tags=["import-export"])
async def import_report(log_id: int, db: DB, _: CurrentUser):
    lg = await db.get(ImportLog, log_id)
    if lg is None:
        raise HTTPException(404, "Import introuvable")
    return json.loads(lg.report or "{}")


EXPORT_FILENAMES = {
    "all": "Suivi_Licence_export",
    "licences": "Export_licences",
    "contrats": "Export_contrats",
    "echeances": "Export_echeances",
    "planning": "Export_planning_renouvellement",
}


async def _export(db, user, audit, scope: str, horizon_days: int | None = None) -> Response:
    content = await export_workbook(db, scope, horizon_days)
    await audit.log(user, "EXPORT_EXCEL", "EXPORT", None, EXPORT_FILENAMES[scope], details={"perimetre": scope})
    name = f"{EXPORT_FILENAMES[scope]}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/export/excel", tags=["import-export"])
async def export_excel(db: DB, user: CurrentUser, audit: Audit):
    """Inventaire complet : les 7 onglets du gabarit métier."""
    return await _export(db, user, audit, "all")


@router.get("/export/licences", tags=["import-export"])
async def export_licences(db: DB, user: CurrentUser, audit: Audit):
    return await _export(db, user, audit, "licences")


@router.get("/export/contrats", tags=["import-export"])
async def export_contrats(db: DB, user: CurrentUser, audit: Audit):
    return await _export(db, user, audit, "contrats")


@router.get("/export/echeances", tags=["import-export"])
async def export_echeances(db: DB, user: CurrentUser, audit: Audit):
    """Éléments expirés, critiques ou en alerte (actifs et contrats)."""
    return await _export(db, user, audit, "echeances")


@router.get("/export/planning", tags=["import-export"])
async def export_planning(db: DB, user: CurrentUser, audit: Audit, horizon_days: int | None = Query(None, ge=1, le=3650)):
    """Planning de renouvellement (tous les éléments datés, ou limité à un horizon en jours)."""
    return await _export(db, user, audit, "planning", horizon_days)


@router.get("/notifications", response_model=list[NotificationOut], tags=["alerts"])
async def notifications(db: DB, _: CurrentUser, limit: int = Query(200, ge=1, le=1000)):
    return (await db.execute(select(Notification).order_by(Notification.id.desc()).limit(limit))).scalars().all()


@router.get("/alerts", tags=["alerts"])
async def alerts(db: DB, _: CurrentUser):
    cfg = await app_settings.get_alerts(db)
    smtp_cfg, _, _ = await app_settings.get_smtp_config(db)
    general = await app_settings.get_general(db)
    items = sorted(await pending_alerts(db, cfg), key=lambda x: x["days_remaining"])
    rcpt = cfg["recipients"]
    static = ([general["admin_email"]] if rcpt["notify_admin"] and general["admin_email"] else []) + list(rcpt["custom"])
    return {
        "smtp_configured": smtp_cfg.configured,
        "recipients": static,
        "notify_owner": rcpt["notify_owner"],
        "thresholds": app_settings.enabled_thresholds(cfg),
        "notify_expired": cfg["notify_expired"],
        "items": items,
    }


@router.post("/alerts/run", tags=["alerts"])
async def alerts_run(db: DB, user: AdminUser, audit: Audit):
    result = await run_alerts(db)
    await audit.log(
        user,
        "ALERTS_RUN",
        "ALERTS",
        None,
        "Contrôle manuel des alertes",
        details={k: result.get(k) for k in ("checked", "new", "delivery_status")},
    )
    return result

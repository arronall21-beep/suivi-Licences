import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from app.api.deps import DB, AdminUser, CurrentUser, ImporterUser
from app.core.config import settings
from app.models import ImportLog, Notification
from app.schemas import NotificationOut
from app.services.dashboard import build_dashboard, filter_renewals, load_all, renewal_items
from app.services.excel_export import export_workbook
from app.services.excel_import import ImportFileError, import_workbook
from app.services.notifications import pending_alerts, run_alerts, smtp_configured

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


@router.post("/import/excel", tags=["import-export"])
async def import_excel(file: UploadFile, db: DB, user: ImporterUser):
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(415, "Format attendu : fichier Excel .xlsx")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"Fichier trop volumineux (max {settings.max_upload_mb} Mo)")
    try:
        return await import_workbook(db, content, file.filename, user.email)
    except ImportFileError as exc:
        await db.rollback()
        raise HTTPException(422, str(exc)) from None


@router.get("/import/history", tags=["import-export"])
async def import_history(db: DB, _: CurrentUser):
    logs = (await db.execute(select(ImportLog).order_by(ImportLog.id.desc()).limit(20))).scalars().all()
    return [
        {
            "id": lg.id,
            "filename": lg.filename,
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


@router.get("/export/excel", tags=["import-export"])
async def export_excel(db: DB, _: CurrentUser):
    content = await export_workbook(db)
    name = f"Suivi_Licence_export_{datetime.now():%Y%m%d_%H%M}.xlsx"
    return Response(content, media_type=XLSX, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/notifications", response_model=list[NotificationOut], tags=["alerts"])
async def notifications(db: DB, _: CurrentUser, limit: int = Query(200, ge=1, le=1000)):
    return (await db.execute(select(Notification).order_by(Notification.id.desc()).limit(limit))).scalars().all()


@router.get("/alerts", tags=["alerts"])
async def alerts(db: DB, _: CurrentUser):
    items = sorted(await pending_alerts(db), key=lambda x: x["days_remaining"])
    return {
        "smtp_configured": smtp_configured(),
        "recipients": settings.alert_recipient_list,
        "thresholds": settings.alert_threshold_list,
        "items": items,
    }


@router.post("/alerts/run", tags=["alerts"])
async def alerts_run(db: DB, _: AdminUser):
    return await run_alerts(db)

from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.services import app_settings
from app.version import VERSION

router = APIRouter(tags=["config"])


@router.get("/public/config")
async def public_config(db: DB):
    """Identité de l'application, affichée sur l'écran de connexion (aucune donnée sensible)."""
    g = await app_settings.get_general(db)
    return {"org_name": g["org_name"], "app_name": g["app_name"], "version": VERSION}


@router.get("/config")
async def config(db: DB, _: CurrentUser):
    g = await app_settings.get_general(db)
    alerts = await app_settings.get_alerts(db)
    return {
        "org_name": g["org_name"],
        "app_name": g["app_name"],
        "currency": g["currency"],
        "currency_label": g["currency_label"],
        "timezone": g["timezone"],
        "critical_days": g["critical_days"],
        "alert_days": g["alert_days"],
        "alert_thresholds": app_settings.enabled_thresholds(alerts),
        "version": VERSION,
    }

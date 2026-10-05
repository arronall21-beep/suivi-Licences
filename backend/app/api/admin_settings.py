from fastapi import APIRouter

from app.api.deps import DB, AdminUser
from app.schemas.settings import AlertSettings, GeneralSettings, SmtpIn, SmtpTestEmail
from app.services import app_settings, mailer
from app.services.audit import Audit

router = APIRouter(prefix="/admin/settings", tags=["admin"])


@router.get("/general")
async def get_general(db: DB, _: AdminUser):
    return await app_settings.get_general(db)


@router.put("/general")
async def put_general(body: GeneralSettings, db: DB, admin: AdminUser, audit: Audit):
    data, changed = await app_settings.save_general(db, body, admin.email)
    await audit.log(admin, "SETTINGS_UPDATE", "SETTINGS", "general", "Paramètres généraux", details={"champs": changed})
    return data


@router.get("/alerts")
async def get_alerts(db: DB, _: AdminUser):
    return await app_settings.get_alerts(db)


@router.put("/alerts")
async def put_alerts(body: AlertSettings, db: DB, admin: AdminUser, audit: Audit):
    data = await app_settings.save_alerts(db, body, admin.email)
    await audit.log(admin, "ALERTS_CONFIG_UPDATE", "SETTINGS", "alerts", "Configuration des alertes")
    return data


@router.get("/smtp")
async def get_smtp(db: DB, _: AdminUser):
    """Configuration SMTP : le mot de passe n'est jamais renvoyé (indicateur `password_set` uniquement)."""
    return await app_settings.smtp_public(db)


@router.put("/smtp")
async def put_smtp(body: SmtpIn, db: DB, admin: AdminUser, audit: Audit):
    changed = await app_settings.save_smtp(db, body, admin.email)
    await audit.log(admin, "SMTP_UPDATE", "SETTINGS", "smtp", "Configuration SMTP", details={"champs": changed})
    return await app_settings.smtp_public(db)


@router.post("/smtp/test-connection")
async def smtp_test_connection(body: SmtpIn, db: DB, admin: AdminUser, audit: Audit):
    """Teste la connexion avec les valeurs du formulaire (mot de passe enregistré si aucun nouveau n'est saisi)."""
    cfg = await app_settings.effective_smtp_from_draft(db, body)
    ok, message = await mailer.test_connection(cfg)
    await audit.log(
        admin, "SMTP_TEST_CONNECTION", "SETTINGS", "smtp", cfg.host, result="SUCCESS" if ok else "FAILURE", details=message
    )
    return {"ok": ok, "message": message}


@router.post("/smtp/test-email")
async def smtp_test_email(body: SmtpTestEmail, db: DB, admin: AdminUser, audit: Audit):
    cfg = await app_settings.effective_smtp_from_draft(db, body)
    if not cfg.configured:
        return {"ok": False, "message": "SMTP non configuré : renseignez le serveur et l'adresse expéditeur", "to": None}
    general = await app_settings.get_general(db)
    to = str(body.to) if body.to else admin.email
    ok, err = await mailer.send_email(
        cfg,
        [to],
        f"[{general['org_name']}] Email de test",
        f"Ceci est un email de test envoyé depuis « {general['app_name']} ».\nSi vous le recevez, la configuration SMTP est correcte.",
    )
    await audit.log(
        admin, "SMTP_TEST_EMAIL", "SETTINGS", "smtp", to, result="SUCCESS" if ok else "FAILURE", details=None if ok else err
    )
    return {"ok": ok, "message": f"Email de test envoyé à {to}" if ok else err, "to": to}

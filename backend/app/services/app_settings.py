"""Paramètres applicatifs persistés en base (avec valeurs par défaut issues de l'environnement).

Les paramètres non sensibles sont stockés en JSON. Le mot de passe SMTP est chiffré (Fernet) et n'est
jamais renvoyé par l'API : on n'expose qu'un indicateur `password_set`.
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto, lifecycle
from app.core.config import settings
from app.models import AppSetting
from app.schemas.settings import AlertSettings, GeneralSettings, SmtpIn, currency_label
from app.services.mailer import SmtpConfig

SMTP_KEYS = ("smtp_host", "smtp_port", "smtp_security", "smtp_username", "smtp_password", "smtp_from_email", "smtp_from_name")
DEFAULT_THRESHOLDS = (90, 60, 30, 7)


async def _stored(db: AsyncSession, prefix: str | None = None) -> dict[str, AppSetting]:
    rows = (await db.execute(select(AppSetting))).scalars().all()
    return {r.key: r for r in rows if prefix is None or r.key.startswith(prefix)}


def _val(row: AppSetting | None, default: Any) -> Any:
    if row is None or row.value is None:
        return default
    try:
        return json.loads(row.value)
    except ValueError:
        return default


async def _put(db: AsyncSession, key: str, value: Any, user_email: str | None, secret: bool = False) -> None:
    row = await db.get(AppSetting, key)
    payload = None if value is None else (crypto.encrypt(value) if secret else json.dumps(value, ensure_ascii=False))
    if row is None:
        db.add(AppSetting(key=key, value=payload, is_secret=secret, updated_by=user_email))
    else:
        row.value, row.is_secret, row.updated_by = payload, secret, user_email


# ---------------- Paramètres généraux ----------------
def general_defaults() -> dict[str, Any]:
    return {
        "org_name": settings.organization_name,
        "app_name": settings.application_name,
        "currency": settings.currency.upper(),
        "timezone": settings.default_timezone,
        "admin_email": settings.admin_email or None,
        "critical_days": settings.critical_days,
        "alert_days": settings.alert_days,
    }


async def get_general(db: AsyncSession) -> dict[str, Any]:
    stored = await _stored(db)
    data = {k: _val(stored.get(f"general.{k}"), v) for k, v in general_defaults().items()}
    data["currency_label"] = currency_label(data["currency"])
    return data


async def save_general(db: AsyncSession, body: GeneralSettings, user_email: str | None) -> tuple[dict[str, Any], list[str]]:
    before = await get_general(db)
    new = body.model_dump()
    changed = [k for k, v in new.items() if before.get(k) != v]
    for k, v in new.items():
        await _put(db, f"general.{k}", v, user_email)
    await db.commit()
    await apply_runtime(db)
    return await get_general(db), changed


async def apply_runtime(db: AsyncSession) -> dict[str, Any]:
    """Applique seuils et fuseau au moteur de cycle de vie (et replanifie le job d'alertes)."""
    general = await get_general(db)
    lifecycle.config.critical_days = general["critical_days"]
    lifecycle.config.alert_days = general["alert_days"]
    lifecycle.config.timezone = general["timezone"]
    from app.jobs.scheduler import reschedule

    reschedule(general["timezone"])
    return general


# ---------------- Alertes ----------------
def alert_defaults() -> dict[str, Any]:
    days = settings.alert_threshold_list or list(DEFAULT_THRESHOLDS)
    return {
        "thresholds": [{"days": d, "enabled": True} for d in days],
        "notify_expired": True,
        "recipients": {"notify_owner": False, "notify_admin": True, "custom": settings.alert_recipient_list},
    }


async def get_alerts(db: AsyncSession) -> dict[str, Any]:
    stored = await _stored(db)
    return {k: _val(stored.get(f"alerts.{k}"), v) for k, v in alert_defaults().items()}


async def save_alerts(db: AsyncSession, body: AlertSettings, user_email: str | None) -> dict[str, Any]:
    data = json.loads(body.model_dump_json())
    for k, v in data.items():
        await _put(db, f"alerts.{k}", v, user_email)
    await db.commit()
    return await get_alerts(db)


def enabled_thresholds(alerts: dict[str, Any]) -> list[int]:
    return sorted((t["days"] for t in alerts["thresholds"] if t["enabled"]), reverse=True)


# ---------------- SMTP ----------------
def _env_smtp() -> dict[str, Any]:
    security = (settings.smtp_security or ("STARTTLS" if settings.smtp_use_tls else "NONE")).upper()
    return {
        "smtp_host": settings.smtp_host,
        "smtp_port": settings.smtp_port,
        "smtp_security": security,
        "smtp_username": settings.smtp_username,
        "smtp_from_email": settings.smtp_from,
        "smtp_from_name": "",
    }


async def get_smtp_config(db: AsyncSession) -> tuple[SmtpConfig, str, str | None]:
    """Configuration SMTP effective. Renvoie (config avec mot de passe déchiffré, source, avertissement)."""
    stored = await _stored(db, "smtp_")
    env = _env_smtp()
    values = {k: _val(stored.get(k), env[k]) for k in env}
    warning = None
    password = settings.smtp_password
    pw_row = stored.get("smtp_password")
    if pw_row is not None and pw_row.value:
        decrypted = crypto.decrypt(pw_row.value)
        if decrypted is None:
            warning = "Le mot de passe SMTP enregistré est illisible (clé de chiffrement modifiée) : ressaisissez-le."
            password = ""
        else:
            password = decrypted
    source = "database" if any(k in stored for k in SMTP_KEYS) else ("environment" if env["smtp_host"] else "none")
    cfg = SmtpConfig(
        host=values["smtp_host"] or "",
        port=int(values["smtp_port"] or 587),
        security=values["smtp_security"] or "NONE",
        username=values["smtp_username"] or "",
        password=password or "",
        from_email=values["smtp_from_email"] or "",
        from_name=values["smtp_from_name"] or "",
    )
    return cfg, source, warning


async def smtp_public(db: AsyncSession) -> dict[str, Any]:
    """Vue API de la configuration SMTP : jamais de mot de passe."""
    cfg, source, warning = await get_smtp_config(db)
    return {
        "host": cfg.host,
        "port": cfg.port,
        "security": cfg.security,
        "username": cfg.username,
        "from_email": cfg.from_email or None,
        "from_name": cfg.from_name,
        "password_set": bool(cfg.password),
        "configured": cfg.configured,
        "source": source,
        "warning": warning,
    }


async def save_smtp(db: AsyncSession, body: SmtpIn, user_email: str | None) -> list[str]:
    before, _, _ = await get_smtp_config(db)
    await _put(db, "smtp_host", body.host, user_email)
    await _put(db, "smtp_port", body.port, user_email)
    await _put(db, "smtp_security", body.security, user_email)
    await _put(db, "smtp_username", body.username, user_email)
    await _put(db, "smtp_from_email", str(body.from_email) if body.from_email else "", user_email)
    await _put(db, "smtp_from_name", body.from_name, user_email)
    changed = [
        k
        for k, new, old in (
            ("host", body.host, before.host),
            ("port", body.port, before.port),
            ("security", body.security, before.security),
            ("username", body.username, before.username),
            ("from_email", str(body.from_email or ""), before.from_email),
            ("from_name", body.from_name, before.from_name),
        )
        if new != old
    ]
    if body.clear_password:
        await _put(db, "smtp_password", None, user_email, secret=True)
        changed.append("password (supprimé)")
    elif body.password:
        await _put(db, "smtp_password", body.password, user_email, secret=True)
        changed.append("password (remplacé)")
    await db.commit()
    return changed


async def effective_smtp_from_draft(db: AsyncSession, draft: SmtpIn) -> SmtpConfig:
    """Configuration à tester : valeurs du formulaire, mot de passe enregistré si aucun nouveau n'est saisi."""
    current, _, _ = await get_smtp_config(db)
    password = "" if draft.clear_password else (draft.password or current.password)
    return SmtpConfig(
        host=draft.host,
        port=draft.port,
        security=draft.security,
        username=draft.username,
        password=password,
        from_email=str(draft.from_email) if draft.from_email else "",
        from_name=draft.from_name,
    )

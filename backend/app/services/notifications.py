"""Alertes d'échéance J-90 / J-60 / J-30 / J-7 avec historique anti-doublon."""

import logging
import smtplib
from email.message import EmailMessage

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.models import Notification
from app.services.dashboard import load_all, renewal_items

log = logging.getLogger(__name__)


def threshold_for(days: int | None, thresholds: list[int]) -> int | None:
    """Plus petit seuil atteint (ex. 25 jours → J-30). Expiré → 0."""
    if days is None:
        return None
    if days <= 0:
        return 0
    reached = [t for t in thresholds if days <= t]
    return min(reached) if reached else None


def smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, settings.smtp_from, ", ".join(recipients)
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)


async def pending_alerts(db: AsyncSession) -> list[dict]:
    assets, contracts = await load_all(db)
    thresholds = settings.alert_threshold_list
    out = []
    for it in renewal_items(assets, contracts):
        t = threshold_for(it["days_remaining"], thresholds)
        if t is not None:
            out.append({**it, "threshold": t})
    return out


async def run_alerts(db: AsyncSession) -> dict:
    alerts = await pending_alerts(db)
    existing = {(n.target_type, n.target_id, n.threshold, n.due_date) for n in (await db.execute(select(Notification))).scalars()}
    new = [a for a in alerts if (a["kind"], a["id"], a["threshold"], a["end_date"]) not in existing]
    recipients = settings.alert_recipient_list
    if not new:
        return {"checked": len(alerts), "new": 0, "delivery_status": None, "recipients": recipients}

    status, error = "NON_ENVOYE", None
    if not recipients:
        error = "Aucun destinataire configuré (ALERT_RECIPIENTS)"
    elif not smtp_configured():
        error = "SMTP non configuré (SMTP_HOST / SMTP_FROM)"
    else:
        lines = [
            f"- [{('EXPIRÉ' if a['threshold'] == 0 else 'J-' + str(a['threshold']))}] {a['type']} {a['reference']} — {a['name']} "
            f"(échéance {a['end_date']:%d/%m/%Y}, {a['days_remaining']} j, responsable : {a['owner'] or '-'})"
            for a in sorted(new, key=lambda x: x["days_remaining"])
        ]
        body = "Bonjour,\n\nLes échéances suivantes nécessitent une action :\n\n" + "\n".join(lines) + "\n\n-- Suivi Licences SI"
        try:
            await run_in_threadpool(_send_email, recipients, f"[Suivi SI] {len(new)} échéance(s) à traiter", body)
            status = "ENVOYE"
        except Exception as exc:  # noqa: BLE001
            status, error = "ERREUR", str(exc)[:500]
            log.exception("Échec envoi email d'alerte")

    for a in new:
        db.add(
            Notification(
                target_type=a["kind"],
                target_id=a["id"],
                target_reference=a["reference"],
                target_name=(a["name"] or "")[:255],
                threshold=a["threshold"],
                due_date=a["end_date"],
                days_remaining=a["days_remaining"],
                recipients=", ".join(recipients) or None,
                delivery_status=status,
                error=error,
            )
        )
    await db.commit()
    return {"checked": len(alerts), "new": len(new), "delivery_status": status, "error": error, "recipients": recipients}

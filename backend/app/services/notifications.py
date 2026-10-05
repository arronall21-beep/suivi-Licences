"""Alertes d'échéance (J-90 / J-60 / J-30 / J-7 par défaut) avec historique anti-doublon.

Seuils, alerte « expiré » et destinataires viennent des paramètres (Administration → Paramètres).
Une alerte est identifiée par (type, id, seuil, date d'échéance) : une seule notification par échéance
et par seuil, quel que soit le nombre d'exécutions du contrôle.
"""

import logging
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.models import Notification, User
from app.services import app_settings, inbox, mailer
from app.services.dashboard import load_all, renewal_items

log = logging.getLogger(__name__)


def threshold_for(days: int | None, thresholds: list[int], include_expired: bool = True) -> int | None:
    """Plus petit seuil atteint (ex. 25 jours → J-30). Expiré → 0 (si activé)."""
    if days is None:
        return None
    if days <= 0:
        return 0 if include_expired else None
    reached = [t for t in thresholds if days <= t]
    return min(reached) if reached else None


def threshold_label(threshold: int) -> str:
    return "EXPIRÉ" if threshold == 0 else f"J-{threshold}"


async def pending_alerts(db: AsyncSession, alerts_cfg: dict | None = None) -> list[dict]:
    cfg = alerts_cfg or await app_settings.get_alerts(db)
    thresholds = app_settings.enabled_thresholds(cfg)
    assets, contracts = await load_all(db)
    out = []
    for it in renewal_items(assets, contracts):
        t = threshold_for(it["days_remaining"], thresholds, cfg["notify_expired"])
        if t is not None:
            out.append({**it, "threshold": t})
    return out


def _inbox_kind(a: dict) -> tuple[str, str]:
    """(type de notification interne, libellé) selon la nature de l'élément et le seuil."""
    expired = a["threshold"] == 0
    if a["kind"] == "CONTRACT":
        return ("CONTRACT_EXPIRED", "Contrat expiré") if expired else ("CONTRACT_EXPIRING", "Contrat arrivant à échéance")
    if a["type"] == "LICENCE":
        if expired:
            return "LICENSE_EXPIRED", "Licence expirée"
        if a["threshold"] <= lifecycle.config.critical_days:
            return "LICENSE_CRITICAL", "Licence critique"
        return "LICENSE_EXPIRING", "Licence arrivant à échéance"
    if a["type"] == "CERTIFICAT":
        return (
            ("CERTIFICATE_EXPIRED", "Certificat expiré")
            if expired
            else ("CERTIFICATE_EXPIRING", "Certificat arrivant à échéance")
        )
    return ("ASSET_EXPIRED", "Actif expiré") if expired else ("ASSET_EXPIRING", "Actif arrivant à échéance")


def _priority(threshold: int) -> str:
    if threshold <= 7:
        return "HIGH"
    return "MEDIUM" if threshold <= lifecycle.config.critical_days else "LOW"


async def _create_inbox_entries(db: AsyncSession, new: list[dict]) -> None:
    for a in new:
        kind, label = _inbox_kind(a)
        when = "expiré" if a["threshold"] == 0 else f"échéance le {a['end_date']:%d/%m/%Y} ({a['days_remaining']} j)"
        link = f"/actifs/fiche/{a['id']}" if a["kind"] == "ASSET" else f"/contrats?focus={a['id']}"
        await inbox.create_notification(
            db,
            kind,
            f"{label} : {a['reference']} — {a['name']}",
            f"{when}. Responsable : {a['owner'] or 'non renseigné'}.",
            priority=_priority(a["threshold"]),
            link=link,
            entity_type=a["kind"],
            entity_id=a["id"],
            dedupe_key=f"alert:{a['kind']}:{a['id']}:{a['threshold']}:{a['end_date']}",
        )


async def _resolve_recipients(db: AsyncSession, cfg: dict, new: list[dict]) -> tuple[dict[str, list[dict]], int]:
    """Associe chaque adresse aux alertes qu'elle doit recevoir. Renvoie aussi le nb de responsables non résolus."""
    general = await app_settings.get_general(db)
    rcpt = cfg["recipients"]
    plan: dict[str, list[dict]] = defaultdict(list)
    shared: set[str] = set()
    if rcpt.get("notify_admin") and general.get("admin_email"):
        shared.add(general["admin_email"].lower())
    shared.update(e.lower() for e in rcpt.get("custom", []))
    for email in shared:
        plan[email] = list(new)
    unresolved = 0
    if rcpt.get("notify_owner"):
        users = (await db.execute(select(User).where(User.is_active.is_(True)))).scalars().all()
        by_name: dict[str, str] = {}
        for u in users:
            for key in (
                u.email,
                u.full_name,
                f"{u.first_name or ''} {u.last_name or ''}".strip(),
                f"{u.last_name or ''} {u.first_name or ''}".strip(),
            ):
                if key:
                    by_name[key.lower()] = u.email.lower()
        for a in new:
            owner = (a.get("owner") or "").strip().lower()
            email = by_name.get(owner)
            if email is None:
                unresolved += 1
            elif email not in shared:
                plan[email].append(a)
    return plan, unresolved


def _digest(alerts: list[dict], org: str) -> str:
    lines = [
        f"- [{threshold_label(a['threshold'])}] {a['type']} {a['reference']} — {a['name']} "
        f"(échéance {a['end_date']:%d/%m/%Y}, {a['days_remaining']} j, responsable : {a['owner'] or '-'})"
        for a in sorted(alerts, key=lambda x: x["days_remaining"])
    ]
    return "Bonjour,\n\nLes échéances suivantes nécessitent une action :\n\n" + "\n".join(lines) + f"\n\n-- {org}"


async def run_alerts(db: AsyncSession) -> dict:
    cfg = await app_settings.get_alerts(db)
    alerts = await pending_alerts(db, cfg)
    existing = {(n.target_type, n.target_id, n.threshold, n.due_date) for n in (await db.execute(select(Notification))).scalars()}
    new = [a for a in alerts if (a["kind"], a["id"], a["threshold"], a["end_date"]) not in existing]
    if not new:
        return {"checked": len(alerts), "new": 0, "delivery_status": None, "recipients": []}

    general = await app_settings.get_general(db)
    smtp_cfg, _, _ = await app_settings.get_smtp_config(db)
    plan, unresolved = await _resolve_recipients(db, cfg, new)
    recipients = sorted(plan)

    status, error = "NON_ENVOYE", None
    if not recipients:
        error = "Aucun destinataire configuré (Administration → Paramètres → Alertes)"
    elif not smtp_cfg.configured:
        error = "SMTP non configuré (Administration → SMTP)"
    else:
        failures = []
        for email, items in plan.items():
            if not items:
                continue
            ok, err = await mailer.send_email(
                smtp_cfg,
                [email],
                f"[{general['org_name']}] {len(items)} échéance(s) à traiter",
                _digest(items, general["app_name"]),
            )
            if not ok:
                failures.append(err)
        status, error = ("ERREUR", failures[0]) if failures else ("ENVOYE", None)

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
    await _create_inbox_entries(db, new)
    await db.commit()
    return {
        "checked": len(alerts),
        "new": len(new),
        "delivery_status": status,
        "error": error,
        "recipients": recipients,
        "owners_unresolved": unresolved,
    }


async def last_email_alert(db: AsyncSession) -> Notification | None:
    stmt = select(Notification).where(Notification.delivery_status == "ENVOYE").order_by(Notification.id.desc()).limit(1)
    return (await db.execute(stmt)).scalar_one_or_none()


__all__ = ["run_alerts", "pending_alerts", "threshold_for", "threshold_label", "last_email_alert"]

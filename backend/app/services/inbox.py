"""Notifications internes (cloche). Création idempotente via `dedupe_key`."""

from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppNotification, AppNotificationRead, User

PRIORITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


async def create_notification(
    db: AsyncSession,
    kind: str,
    title: str,
    message: str | None = None,
    priority: str = "MEDIUM",
    link: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    audience: str = "ALL",
    dedupe_key: str | None = None,
) -> AppNotification | None:
    """Crée la notification (commit à la charge de l'appelant). Renvoie None si dedupe_key existe déjà."""
    if dedupe_key:
        exists = (await db.execute(select(AppNotification.id).where(AppNotification.dedupe_key == dedupe_key))).first()
        if exists:
            return None
    n = AppNotification(
        kind=kind,
        title=title[:255],
        message=message,
        priority=priority,
        link=link,
        entity_type=entity_type,
        entity_id=entity_id,
        audience=audience,
        dedupe_key=dedupe_key,
    )
    db.add(n)
    await db.flush()
    return n


def audience_filter(user: User):
    """Un ADMIN voit toutes les notifications ; les autres rôles, uniquement celles destinées à tous."""
    return True if user.role == "ADMIN" else AppNotification.audience == "ALL"


async def unread_count(db: AsyncSession, user: User) -> int:
    read = select(AppNotificationRead.notification_id).where(AppNotificationRead.user_id == user.id)
    stmt = select(func.count()).select_from(AppNotification).where(and_(audience_filter(user), AppNotification.id.not_in(read)))
    return (await db.execute(stmt)).scalar_one()


async def notify_password_reset_request(db: AsyncSession, user: User) -> None:
    name = user.full_name or user.email
    await create_notification(
        db,
        "PASSWORD_RESET_REQUEST",
        f"Demande de réinitialisation de mot de passe : {name}",
        f"{user.email} a demandé la réinitialisation de son mot de passe depuis l'écran de connexion.",
        priority="MEDIUM",
        link=f"/admin/utilisateurs?q={user.email}",
        entity_type="USER",
        entity_id=user.id,
        audience="ADMIN",
        dedupe_key=f"pwdreset:{user.id}:{date.today().isoformat()}",
    )
    await db.commit()


__all__ = ["create_notification", "audience_filter", "unread_count", "notify_password_reset_request"]

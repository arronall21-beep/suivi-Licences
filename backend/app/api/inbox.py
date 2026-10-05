from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.api.deps import DB, CurrentUser
from app.models import AppNotification, AppNotificationRead
from app.services.inbox import audience_filter, unread_count

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _out(n: AppNotification, read: bool) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "priority": n.priority,
        "title": n.title,
        "message": n.message,
        "link": n.link,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "created_at": n.created_at,
        "read": read,
    }


@router.get("")
async def list_inbox(
    db: DB,
    user: CurrentUser,
    unread_only: bool = False,
    priority: str | None = Query(None, pattern="^(HIGH|MEDIUM|LOW)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    read_ids = select(AppNotificationRead.notification_id).where(AppNotificationRead.user_id == user.id)
    cond = [audience_filter(user)]
    if unread_only:
        cond.append(AppNotification.id.not_in(read_ids))
    if priority:
        cond.append(AppNotification.priority == priority)
    where = and_(*cond)
    total = (await db.execute(select(func.count()).select_from(AppNotification).where(where))).scalar_one()
    rows = (
        await db.execute(
            select(AppNotification, AppNotification.id.in_(read_ids))
            .where(where)
            .order_by(AppNotification.created_at.desc(), AppNotification.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
    ).all()
    return {
        "items": [_out(n, bool(is_read)) for n, is_read in rows],
        "total": total,
        "page": page,
        "size": size,
        "unread": await unread_count(db, user),
    }


@router.get("/unread-count")
async def get_unread_count(db: DB, user: CurrentUser):
    return {"unread": await unread_count(db, user)}


@router.post("/read-all")
async def read_all(db: DB, user: CurrentUser):
    ids = (await db.execute(select(AppNotification.id).where(audience_filter(user)))).scalars().all()
    if ids:
        stmt = pg_insert(AppNotificationRead).values([{"notification_id": i, "user_id": user.id} for i in ids])
        await db.execute(stmt.on_conflict_do_nothing())
        await db.commit()
    return {"unread": 0}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: int, db: DB, user: CurrentUser):
    n = await db.get(AppNotification, notification_id)
    if n is None or not (user.role == "ADMIN" or n.audience == "ALL"):
        raise HTTPException(404, "Notification introuvable")
    await db.execute(pg_insert(AppNotificationRead).values(notification_id=n.id, user_id=user.id).on_conflict_do_nothing())
    await db.commit()
    return {"unread": await unread_count(db, user)}

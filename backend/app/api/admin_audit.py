from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, or_, select

from app.api.deps import DB, AdminUser
from app.models import AuditLog
from app.services.audit import ACTION_LABELS

router = APIRouter(prefix="/admin/audit", tags=["admin"])


def _out(a: AuditLog) -> dict:
    return {
        "id": a.id,
        "created_at": a.created_at,
        "user_email": a.user_email,
        "action": a.action,
        "action_label": ACTION_LABELS.get(a.action, a.action),
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "entity_label": a.entity_label,
        "result": a.result,
        "details": a.details,
        "ip_address": a.ip_address,
    }


@router.get("")
async def list_audit(
    db: DB,
    _: AdminUser,
    q: str | None = None,
    action: str | None = None,
    user: str | None = None,
    entity_type: str | None = None,
    result: str | None = Query(None, pattern="^(SUCCESS|FAILURE)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=200),
):
    cond = []
    if q:
        like = f"%{q.strip()}%"
        cond.append(
            or_(
                AuditLog.entity_label.ilike(like),
                AuditLog.details.ilike(like),
                AuditLog.user_email.ilike(like),
                AuditLog.entity_id.ilike(like),
                AuditLog.ip_address.ilike(like),
            )
        )
    if action:
        cond.append(AuditLog.action == action)
    if user:
        cond.append(AuditLog.user_email.ilike(f"%{user.strip()}%"))
    if entity_type:
        cond.append(AuditLog.entity_type == entity_type)
    if result:
        cond.append(AuditLog.result == result)
    if date_from:
        cond.append(AuditLog.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        cond.append(AuditLog.created_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc))
    where = and_(*cond) if cond else True
    total = (await db.execute(select(func.count()).select_from(AuditLog).where(where))).scalar_one()
    rows = (
        (await db.execute(select(AuditLog).where(where).order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size)))
        .scalars()
        .all()
    )
    return {"items": [_out(a) for a in rows], "total": total, "page": page, "size": size}


@router.get("/actions")
async def audit_actions(db: DB, _: AdminUser):
    return [{"value": k, "label": v} for k, v in ACTION_LABELS.items()]

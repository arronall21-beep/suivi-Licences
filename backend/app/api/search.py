from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentUser
from app.models import Asset, Contract, User, Vendor

router = APIRouter(tags=["search"])
LIMIT = 8


@router.get("/search")
async def global_search(db: DB, user: CurrentUser, q: str = Query(..., min_length=2, max_length=100)):
    """Recherche globale : actifs, contrats, fournisseurs (et utilisateurs pour les administrateurs)."""
    like = f"%{q.strip()}%"
    assets = (
        (
            await db.execute(
                select(Asset)
                .outerjoin(Vendor, Asset.vendor_id == Vendor.id)
                .where(
                    or_(
                        Asset.reference.ilike(like),
                        Asset.name.ilike(like),
                        Vendor.name.ilike(like),
                        Asset.internal_owner.ilike(like),
                        Asset.serial_number.ilike(like),
                        Asset.server_app_target.ilike(like),
                    )
                )
                .order_by(Asset.reference)
                .limit(LIMIT)
            )
        )
        .unique()
        .scalars()
        .all()
    )
    contracts = (
        (
            await db.execute(
                select(Contract)
                .outerjoin(Vendor, Contract.vendor_id == Vendor.id)
                .where(
                    or_(
                        Contract.reference.ilike(like),
                        Contract.market_ref.ilike(like),
                        Contract.scope.ilike(like),
                        Contract.internal_owner.ilike(like),
                        Vendor.name.ilike(like),
                    )
                )
                .order_by(Contract.reference)
                .limit(LIMIT)
            )
        )
        .unique()
        .scalars()
        .all()
    )
    vendors = (
        (
            await db.execute(
                select(Vendor)
                .where(or_(Vendor.name.ilike(like), Vendor.reference.ilike(like), Vendor.contact_person.ilike(like)))
                .order_by(Vendor.name)
                .limit(LIMIT)
            )
        )
        .scalars()
        .all()
    )
    users: list[User] = []
    if user.role == "ADMIN":
        users = (
            (
                await db.execute(
                    select(User)
                    .where(or_(User.email.ilike(like), User.full_name.ilike(like), User.department.ilike(like)))
                    .order_by(User.email)
                    .limit(LIMIT)
                )
            )
            .scalars()
            .all()
        )
    return {
        "query": q,
        "assets": [
            {
                "id": a.id,
                "label": f"{a.reference} — {a.name}",
                "sub": f"{a.category} · {a.vendor_name or '—'}",
                "status": a.status,
                "link": f"/actifs/fiche/{a.id}",
            }
            for a in assets
        ],
        "contracts": [
            {
                "id": c.id,
                "label": f"{c.reference} — {c.scope or c.type or ''}".strip(" —"),
                "sub": c.vendor_name or "—",
                "status": c.lifecycle_status,
                "link": f"/contrats?focus={c.id}",
            }
            for c in contracts
        ],
        "vendors": [
            {
                "id": v.id,
                "label": f"{v.reference} — {v.name}",
                "sub": v.contact_person or "—",
                "link": f"/actifs?vendor_id={v.id}",
            }
            for v in vendors
        ],
        "users": [
            {
                "id": u.id,
                "label": u.full_name or u.email,
                "sub": f"{u.email} · {u.role}",
                "link": f"/admin/utilisateurs?q={u.email}",
            }
            for u in users
        ],
    }

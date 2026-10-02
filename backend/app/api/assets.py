from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser, get_or_404
from app.core import lifecycle
from app.models import Asset, Contract, Vendor
from app.schemas import AssetDetailOut, AssetIn, AssetPage

router = APIRouter(prefix="/assets", tags=["assets"])

EFFECTIVE_END = func.coalesce(Asset.end_date, Asset.support_end_date, Asset.warranty_end_date)
SORTS = {
    "reference": Asset.reference,
    "name": Asset.name,
    "category": Asset.category,
    "vendor": Vendor.name,
    "owner": Asset.internal_owner,
    "department": Asset.user_department,
    "end_date": EFFECTIVE_END,
    "days_remaining": EFFECTIVE_END,
    "status": EFFECTIVE_END,
    "criticality": Asset.criticality,
    "annual_cost": Asset.annual_cost,
    "updated_at": Asset.updated_at,
}


def _status_condition(status: str):
    if status == lifecycle.INCONNU:
        return EFFECTIVE_END.is_(None)
    lo, hi = lifecycle.status_date_range(status)
    conds = []
    if lo is not None:
        conds.append(EFFECTIVE_END >= lo)
    if hi is not None:
        conds.append(EFFECTIVE_END <= hi)
    return and_(*conds)


@router.get("", response_model=AssetPage)
async def list_assets(
    db: DB,
    _: CurrentUser,
    q: str | None = None,
    reference: str | None = None,
    name: str | None = None,
    category: str | None = None,
    status: list[str] | None = Query(None),
    criticality: str | None = None,
    department: str | None = None,
    vendor_id: int | None = None,
    contract_id: int | None = None,
    sort: str = "end_date",
    order: str = "asc",
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=500),
):
    stmt = select(Asset).outerjoin(Vendor, Asset.vendor_id == Vendor.id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Asset.reference.ilike(like),
                Asset.name.ilike(like),
                Vendor.name.ilike(like),
                Asset.internal_owner.ilike(like),
                Asset.serial_number.ilike(like),
            )
        )
    if reference:
        stmt = stmt.where(Asset.reference.ilike(f"%{reference.strip()}%"))
    if name:
        stmt = stmt.where(Asset.name.ilike(f"%{name.strip()}%"))
    if category:
        stmt = stmt.where(Asset.category == category.upper())
    if status:
        valid = [s for s in status if s in lifecycle.STATUSES]
        if valid:
            stmt = stmt.where(or_(*[_status_condition(s) for s in valid]))
    if criticality:
        stmt = stmt.where(Asset.criticality == criticality)
    if department:
        stmt = stmt.where(Asset.user_department == department)
    if vendor_id:
        stmt = stmt.where(Asset.vendor_id == vendor_id)
    if contract_id:
        stmt = stmt.where(Asset.contract_id == contract_id)

    total = (await db.execute(select(func.count()).select_from(stmt.with_only_columns(Asset.id).subquery()))).scalar_one()
    col = SORTS.get(sort, EFFECTIVE_END)
    col = col.desc().nulls_last() if order == "desc" else col.asc().nulls_last()
    stmt = stmt.order_by(col, Asset.id).offset((page - 1) * size).limit(size)
    items = (await db.execute(stmt)).unique().scalars().all()
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/options")
async def filter_options(db: DB, _: CurrentUser):
    async def distinct(column):
        rows = await db.execute(select(column).where(column.isnot(None)).distinct().order_by(column))
        return [r[0] for r in rows if r[0]]

    return {
        "departments": await distinct(Asset.user_department),
        "criticalities": await distinct(Asset.criticality),
        "owners": await distinct(Asset.internal_owner),
        "statuses": [{"value": s, "label": lifecycle.STATUS_LABELS[s]} for s in lifecycle.STATUSES],
        "categories": ["LICENCE", "CERTIFICAT", "MATERIEL", "APPLICATION"],
    }


@router.get("/{asset_id}", response_model=AssetDetailOut)
async def get_asset(asset_id: int, db: DB, _: CurrentUser):
    return await get_or_404(db, Asset, asset_id)


async def _validate(db, body: AssetIn, asset: Asset | None = None):
    if body.vendor_id is not None and await db.get(Vendor, body.vendor_id) is None:
        raise HTTPException(422, "Fournisseur inexistant")
    if body.contract_id is not None and await db.get(Contract, body.contract_id) is None:
        raise HTTPException(422, "Contrat inexistant")
    if asset is not None and asset.category == "LICENCE":
        if body.category != "LICENCE" and asset.assignments:
            raise HTTPException(422, "Impossible de changer la catégorie d'une licence ayant des affectations")
        if (body.total_quantity or 0) < asset.assigned_quantity:
            raise HTTPException(422, f"Quantité totale inférieure aux {asset.assigned_quantity} licence(s) déjà affectée(s)")


@router.post("", response_model=AssetDetailOut, status_code=201)
async def create_asset(body: AssetIn, db: DB, _: AdminUser):
    await _validate(db, body)
    a = Asset(**body.model_dump())
    db.add(a)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Référence déjà existante pour cette catégorie") from None
    return await get_or_404(db, Asset, a.id)


@router.put("/{asset_id}", response_model=AssetDetailOut)
async def update_asset(asset_id: int, body: AssetIn, db: DB, _: AdminUser):
    a = await get_or_404(db, Asset, asset_id)
    await _validate(db, body, a)
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Référence déjà existante pour cette catégorie") from None
    db.expire(a)
    return await get_or_404(db, Asset, asset_id)


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(asset_id: int, db: DB, _: AdminUser):
    a = await get_or_404(db, Asset, asset_id)
    await db.delete(a)
    await db.commit()
    return Response(status_code=204)

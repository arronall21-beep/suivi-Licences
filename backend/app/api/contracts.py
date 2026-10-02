from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser, get_or_404
from app.models import Contract, Vendor
from app.schemas import ContractIn, ContractOut

router = APIRouter(prefix="/contracts", tags=["contracts"])


async def _check_vendor(db, vendor_id):
    if vendor_id is not None and await db.get(Vendor, vendor_id) is None:
        raise HTTPException(422, "Fournisseur inexistant")


@router.get("", response_model=list[ContractOut])
async def list_contracts(
    db: DB, _: CurrentUser, q: str | None = None, vendor_id: int | None = None, type: str | None = None, status: str | None = None
):
    stmt = select(Contract).outerjoin(Vendor, Contract.vendor_id == Vendor.id).order_by(Contract.end_date.asc().nulls_last())
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contract.reference.ilike(like),
                Contract.market_ref.ilike(like),
                Contract.scope.ilike(like),
                Vendor.name.ilike(like),
            )
        )
    if vendor_id:
        stmt = stmt.where(Contract.vendor_id == vendor_id)
    if type:
        stmt = stmt.where(Contract.type == type)
    items = (await db.execute(stmt)).unique().scalars().all()
    if status:
        items = [c for c in items if c.lifecycle_status == status]
    return items


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(contract_id: int, db: DB, _: CurrentUser):
    return await get_or_404(db, Contract, contract_id)


@router.post("", response_model=ContractOut, status_code=201)
async def create_contract(body: ContractIn, db: DB, _: AdminUser):
    await _check_vendor(db, body.vendor_id)
    c = Contract(**body.model_dump())
    db.add(c)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Référence contrat déjà existante") from None
    return await get_or_404(db, Contract, c.id)


@router.put("/{contract_id}", response_model=ContractOut)
async def update_contract(contract_id: int, body: ContractIn, db: DB, _: AdminUser):
    c = await get_or_404(db, Contract, contract_id)
    await _check_vendor(db, body.vendor_id)
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Référence contrat déjà existante") from None
    db.expire(c)
    return await get_or_404(db, Contract, contract_id)


@router.delete("/{contract_id}", status_code=204)
async def delete_contract(contract_id: int, db: DB, _: AdminUser):
    c = await get_or_404(db, Contract, contract_id)
    await db.delete(c)
    await db.commit()
    return Response(status_code=204)

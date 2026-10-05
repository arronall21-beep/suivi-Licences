from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, CurrentUser, DeleterUser, WriterUser, get_or_404
from app.models import Asset, Contract, Vendor
from app.schemas import VendorIn, VendorOut
from app.services.references import next_reference

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorOut])
async def list_vendors(db: DB, _: CurrentUser, q: str | None = None):
    stmt = select(Vendor).order_by(func.lower(Vendor.name))
    if q:
        stmt = stmt.where(or_(Vendor.name.ilike(f"%{q}%"), Vendor.reference.ilike(f"%{q}%")))
    return (await db.execute(stmt)).scalars().all()


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(vendor_id: int, db: DB, _: CurrentUser):
    return await get_or_404(db, Vendor, vendor_id)


@router.post("", response_model=VendorOut, status_code=201)
async def create_vendor(body: VendorIn, db: DB, _: WriterUser):
    v = Vendor(**body.model_dump(), reference=await next_reference(db, "VENDOR"))
    db.add(v)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Un fournisseur avec ce nom existe déjà") from None
    await db.refresh(v)
    return v


@router.put("/{vendor_id}", response_model=VendorOut)
async def update_vendor(vendor_id: int, body: VendorIn, db: DB, _: WriterUser):
    v = await get_or_404(db, Vendor, vendor_id)
    for k, val in body.model_dump().items():
        setattr(v, k, val)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Un fournisseur avec ce nom existe déjà") from None
    await db.refresh(v)
    return v


@router.delete("/{vendor_id}", status_code=204)
async def delete_vendor(vendor_id: int, db: DB, _: DeleterUser):
    v = await get_or_404(db, Vendor, vendor_id)
    used = (await db.execute(select(func.count()).select_from(Asset).where(Asset.vendor_id == vendor_id))).scalar_one()
    used += (await db.execute(select(func.count()).select_from(Contract).where(Contract.vendor_id == vendor_id))).scalar_one()
    if used:
        raise HTTPException(409, f"Fournisseur utilisé par {used} actif(s)/contrat(s) : suppression impossible")
    await db.delete(v)
    await db.commit()
    return Response(status_code=204)

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentUser, WriterUser, get_or_404
from app.models import Asset, LicenseAssignment
from app.schemas import AssignmentIn, AssignmentOut
from app.services.licenses import AllocationError, check_allocation

router = APIRouter(prefix="/assignments", tags=["assignments"])


@router.get("", response_model=list[AssignmentOut])
async def list_assignments(db: DB, _: CurrentUser, asset_id: int | None = None, q: str | None = None):
    stmt = select(LicenseAssignment).join(Asset, LicenseAssignment.asset_id == Asset.id).order_by(LicenseAssignment.id.desc())
    if asset_id:
        stmt = stmt.where(LicenseAssignment.asset_id == asset_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                LicenseAssignment.assigned_to_user.ilike(like),
                LicenseAssignment.assigned_to_device.ilike(like),
                LicenseAssignment.assigned_to_department.ilike(like),
                Asset.name.ilike(like),
                Asset.reference.ilike(like),
            )
        )
    return (await db.execute(stmt)).unique().scalars().all()


@router.post("", response_model=AssignmentOut, status_code=201)
async def create_assignment(body: AssignmentIn, db: DB, _: WriterUser):
    if not (body.assigned_to_user or body.assigned_to_device or body.assigned_to_department):
        raise HTTPException(422, "Indiquer un utilisateur, un poste ou une direction")
    try:
        await check_allocation(db, body.asset_id, body.quantity)
    except AllocationError as exc:
        await db.rollback()
        raise HTTPException(422, str(exc)) from None
    a = LicenseAssignment(**body.model_dump())
    db.add(a)
    await db.commit()
    return await get_or_404(db, LicenseAssignment, a.id)


@router.put("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(assignment_id: int, body: AssignmentIn, db: DB, _: WriterUser):
    a = await get_or_404(db, LicenseAssignment, assignment_id)
    try:
        await check_allocation(db, body.asset_id, body.quantity, exclude_assignment_id=assignment_id)
    except AllocationError as exc:
        await db.rollback()
        raise HTTPException(422, str(exc)) from None
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    await db.commit()
    db.expire(a)
    return await get_or_404(db, LicenseAssignment, assignment_id)


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, db: DB, _: WriterUser):
    a = await get_or_404(db, LicenseAssignment, assignment_id)
    await db.delete(a)
    await db.commit()
    return Response(status_code=204)

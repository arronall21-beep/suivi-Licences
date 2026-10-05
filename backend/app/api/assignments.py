from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentUser, WriterUser, get_or_404
from app.models import Asset, LicenseAssignment
from app.schemas import AssignmentIn, AssignmentOut
from app.services.audit import Audit
from app.services.licenses import AllocationError, check_allocation

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _target(a: LicenseAssignment) -> dict:
    return {"cible": a.assigned_to_user or a.assigned_to_device or a.assigned_to_department, "quantite": a.quantity}


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
async def create_assignment(body: AssignmentIn, db: DB, user: WriterUser, audit: Audit):
    if not (body.assigned_to_user or body.assigned_to_device or body.assigned_to_department):
        raise HTTPException(422, "Indiquer un utilisateur, un poste ou une direction")
    try:
        asset = await check_allocation(db, body.asset_id, body.quantity)
    except AllocationError as exc:
        await audit.log(user, "ASSIGNMENT_CREATE", "ASSET", body.asset_id, None, result="FAILURE", details=str(exc))
        await db.rollback()  # après l'audit : le rollback expire l'objet `user`
        raise HTTPException(422, str(exc)) from None
    a = LicenseAssignment(**body.model_dump())
    db.add(a)
    await db.commit()
    await audit.log(user, "ASSIGNMENT_CREATE", "ASSIGNMENT", a.id, f"{asset.reference} × {a.quantity}", details=_target(a))
    return await get_or_404(db, LicenseAssignment, a.id)


@router.put("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(assignment_id: int, body: AssignmentIn, db: DB, user: WriterUser, audit: Audit):
    a = await get_or_404(db, LicenseAssignment, assignment_id)
    try:
        asset = await check_allocation(db, body.asset_id, body.quantity, exclude_assignment_id=assignment_id)
    except AllocationError as exc:
        await audit.log(user, "ASSIGNMENT_UPDATE", "ASSIGNMENT", assignment_id, None, result="FAILURE", details=str(exc))
        await db.rollback()
        raise HTTPException(422, str(exc)) from None
    for k, v in body.model_dump().items():
        setattr(a, k, v)
    await db.commit()
    await audit.log(
        user, "ASSIGNMENT_UPDATE", "ASSIGNMENT", assignment_id, f"{asset.reference} × {body.quantity}", details=_target(a)
    )
    db.expire(a)
    return await get_or_404(db, LicenseAssignment, assignment_id)


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, db: DB, user: WriterUser, audit: Audit):
    a = await get_or_404(db, LicenseAssignment, assignment_id)
    label, target = f"{a.asset_reference} × {a.quantity}", _target(a)
    await db.delete(a)
    await db.commit()
    await audit.log(user, "ASSIGNMENT_DELETE", "ASSIGNMENT", assignment_id, label, details=target)
    return Response(status_code=204)

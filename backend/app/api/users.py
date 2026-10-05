from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, get_or_404
from app.core.permissions import PERMISSION_LABELS, ROLE_DESCRIPTIONS, ROLE_LABELS, ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models import ROLES, User
from app.schemas import PasswordReset, UserCreate, UserOut, UserUpdate
from app.services.audit import Audit, changed_fields

router = APIRouter(tags=["users"])


def _full_name(first: str, last: str) -> str:
    return f"{first} {last}".strip()


async def _other_active_admins(db, user_id: int) -> int:
    stmt = select(func.count()).select_from(User).where(User.role == "ADMIN", User.is_active.is_(True), User.id != user_id)
    return (await db.execute(stmt)).scalar_one()


@router.get("/users")
async def list_users(
    db: DB,
    _: AdminUser,
    q: str | None = None,
    role: str | None = None,
    state: str | None = Query(None, pattern="^(active|inactive)$"),
    page: int = Query(1, ge=1),
    size: int = Query(25, ge=1, le=200),
):
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.email.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                User.full_name.ilike(like),
                User.department.ilike(like),
            )
        )
    if role:
        stmt = stmt.where(User.role == role)
    if state:
        stmt = stmt.where(User.is_active.is_(state == "active"))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(func.lower(User.last_name).nulls_last(), User.email).offset((page - 1) * size).limit(size)
    items = (await db.execute(stmt)).scalars().all()
    return {"items": [UserOut.model_validate(u) for u in items], "total": total, "page": page, "size": size}


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, db: DB, admin: AdminUser, audit: Audit):
    user = User(
        email=str(body.email).lower(),
        first_name=body.first_name,
        last_name=body.last_name,
        full_name=_full_name(body.first_name, body.last_name),
        phone=body.phone,
        department=body.department,
        role=body.role,
        hashed_password=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette adresse email est déjà utilisée") from None
    await db.refresh(user)
    await audit.log(admin, "USER_CREATE", "USER", user.id, user.email, details={"role": user.role})
    return user


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(user_id: int, body: UserUpdate, db: DB, admin: AdminUser, audit: Audit):
    user = await get_or_404(db, User, user_id)
    if user.role == "ADMIN" and body.role != "ADMIN" and user.is_active and await _other_active_admins(db, user.id) == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Impossible de retirer le rôle ADMIN du dernier administrateur actif")
    new_email = str(body.email).lower()
    old_role = user.role
    changed = changed_fields(user, {**body.model_dump(), "email": new_email}, skip=("role",))
    if new_email != user.email:
        user.token_version += 1  # l'email est le sujet du jeton : les sessions en cours sont invalidées
    user.email, user.first_name, user.last_name = new_email, body.first_name, body.last_name
    user.full_name = _full_name(body.first_name, body.last_name)
    user.phone, user.department, user.role = body.phone, body.department, body.role
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Cette adresse email est déjà utilisée") from None
    await db.refresh(user)
    if changed:
        await audit.log(admin, "USER_UPDATE", "USER", user.id, user.email, details={"champs": changed})
    if old_role != user.role:
        await audit.log(admin, "USER_ROLE_CHANGE", "USER", user.id, user.email, details={"de": old_role, "vers": user.role})
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
async def deactivate_user(user_id: int, db: DB, admin: AdminUser, audit: Audit):
    user = await get_or_404(db, User, user_id)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Vous ne pouvez pas désactiver votre propre compte")
    if user.role == "ADMIN" and user.is_active and await _other_active_admins(db, user.id) == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Impossible de désactiver le dernier administrateur actif")
    user.is_active = False
    user.token_version += 1
    await db.commit()
    await db.refresh(user)
    await audit.log(admin, "USER_DEACTIVATE", "USER", user.id, user.email)
    return user


@router.post("/users/{user_id}/reactivate", response_model=UserOut)
async def reactivate_user(user_id: int, db: DB, admin: AdminUser, audit: Audit):
    user = await get_or_404(db, User, user_id)
    user.is_active = True
    await db.commit()
    await db.refresh(user)
    await audit.log(admin, "USER_REACTIVATE", "USER", user.id, user.email)
    return user


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
async def reset_password(user_id: int, body: PasswordReset, db: DB, admin: AdminUser, audit: Audit):
    user = await get_or_404(db, User, user_id)
    user.hashed_password = hash_password(body.password)
    user.token_version += 1  # toutes les sessions de l'utilisateur sont invalidées
    await db.commit()
    await db.refresh(user)
    await audit.log(admin, "USER_PASSWORD_RESET", "USER", user.id, user.email)
    return user


@router.get("/roles")
async def list_roles(db: DB, _: AdminUser):
    counts = dict((await db.execute(select(User.role, func.count()).where(User.is_active.is_(True)).group_by(User.role))).all())
    roles = [
        {
            "role": role,
            "label": ROLE_LABELS[role],
            "description": ROLE_DESCRIPTIONS[role],
            "permissions": sorted(ROLE_PERMISSIONS[role]),
            "active_users": counts.get(role, 0),
        }
        for role in ROLES
    ]
    return {"roles": roles, "permission_labels": PERMISSION_LABELS}

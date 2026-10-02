from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DB, AdminUser, CurrentUser
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import LoginIn, TokenOut, UserCreate, UserOut

router = APIRouter(tags=["auth"])


async def _authenticate(db, email: str, password: str) -> TokenOut:
    user = (await db.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    return TokenOut(access_token=create_access_token(user.email, user.role), role=user.role, email=user.email)


@router.post("/auth/login", response_model=TokenOut)
async def login(body: LoginIn, db: DB):
    return await _authenticate(db, body.email, body.password)


@router.post("/auth/token", response_model=TokenOut, include_in_schema=False)
async def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    """Endpoint OAuth2 (bouton Authorize de Swagger)."""
    return await _authenticate(db, form.username, form.password)


@router.get("/auth/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(db: DB, _: AdminUser):
    return (await db.execute(select(User).order_by(User.id))).scalars().all()


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(body: UserCreate, db: DB, _: AdminUser):
    user = User(email=body.email.lower(), full_name=body.full_name, role=body.role, hashed_password=hash_password(body.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(409, "Cet email existe déjà") from None
    return user

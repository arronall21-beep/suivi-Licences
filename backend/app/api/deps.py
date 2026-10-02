from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token", auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: DB, token: Annotated[str | None, Depends(oauth2)]) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentification requise", headers={"WWW-Authenticate": "Bearer"})
    if not token:
        raise unauthorized
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise unauthorized from None
    user = (await db.execute(select(User).where(User.email == payload.get("sub")))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]


async def get_or_404(db: AsyncSession, model, obj_id: int):
    obj = await db.get(model, obj_id, populate_existing=True)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {obj_id} introuvable")
    return obj

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import has_permission
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
    # L'utilisateur et son rôle sont relus en base à chaque requête : une désactivation, un changement de
    # rôle ou une réinitialisation de mot de passe (token_version) prend effet immédiatement.
    if user is None or not user.is_active or payload.get("tv", 0) != user.token_version:
        raise unauthorized
    return user


def require_permission(permission: str):
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour cette action")
        return user

    return checker


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
# Administrateur uniquement (utilisateurs, paramètres, SMTP, audit, système, alertes)
AdminUser = Annotated[User, Depends(require_admin)]
# Écriture des données métier (actifs, contrats, fournisseurs, affectations) : ADMIN et MANAGER
WriterUser = Annotated[User, Depends(require_permission("data:write"))]
# Suppression d'actifs, contrats, fournisseurs : ADMIN
DeleterUser = Annotated[User, Depends(require_permission("data:delete"))]
# Import Excel : ADMIN
ImporterUser = Annotated[User, Depends(require_permission("import:run"))]


async def get_or_404(db: AsyncSession, model, obj_id: int):
    obj = await db.get(model, obj_id, populate_existing=True)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {obj_id} introuvable")
    return obj

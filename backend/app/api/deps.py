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


def require_permission(permission: str, *, system: bool = False):
    """Dépendance d'autorisation : la permission du rôle est vérifiée côté serveur à chaque requête.

    `system=True` (administration système : comptes, rôles, SMTP, état du système) exige en plus le rôle ADMIN :
    une permission ajoutée à un autre rôle par erreur ne suffit alors pas à ouvrir ces routes.
    La politique est exposée dans `__policy__` pour que les tests puissent vérifier chaque route.
    """

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if system and user.role != "ADMIN":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits administrateur requis")
        if not has_permission(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour cette action")
        return user

    checker.__policy__ = {"permission": permission, "system": system}
    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]  # connecté (identité, configuration d'affichage)

# --- Données métier -------------------------------------------------------------------------------------------
# Lecture (actifs, contrats, fournisseurs, affectations, dashboard, planning, recherche, alertes) : data:read
ReaderUser = Annotated[User, Depends(require_permission("data:read"))]
# Exports Excel : export:run
ExporterUser = Annotated[User, Depends(require_permission("export:run"))]
# Notifications internes personnelles (cloche) : notifications:read
InboxUser = Annotated[User, Depends(require_permission("notifications:read"))]
# Écriture des données métier (actifs, contrats, fournisseurs, affectations) : ADMIN et MANAGER
WriterUser = Annotated[User, Depends(require_permission("data:write"))]
# Suppression d'actifs, contrats, fournisseurs : ADMIN
DeleterUser = Annotated[User, Depends(require_permission("data:delete"))]
# Import Excel : ADMIN
ImporterUser = Annotated[User, Depends(require_permission("import:run"))]

# --- Gouvernance et pilotage (permission seule : pourront être confiées à un rôle métier sans rôle ADMIN) ---------
# Paramètres généraux et seuils d'alerte
SettingsAdmin = Annotated[User, Depends(require_permission("admin:settings"))]
# Journal d'audit (lecture)
AuditReader = Annotated[User, Depends(require_permission("admin:audit"))]
# Déclenchement manuel du contrôle des alertes
AlertsRunner = Annotated[User, Depends(require_permission("alerts:run"))]

# --- Administration système : permission ET rôle ADMIN ------------------------------------------------------------
# Utilisateurs, rôles, réinitialisation de mots de passe
UsersAdmin = Annotated[User, Depends(require_permission("admin:users", system=True))]
# SMTP et secrets associés
SmtpAdmin = Annotated[User, Depends(require_permission("admin:smtp", system=True))]
# État du système (base, planificateur, sauvegardes)
SystemAdmin = Annotated[User, Depends(require_permission("admin:system", system=True))]


async def get_or_404(db: AsyncSession, model, obj_id: int):
    obj = await db.get(model, obj_id, populate_existing=True)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} {obj_id} introuvable")
    return obj

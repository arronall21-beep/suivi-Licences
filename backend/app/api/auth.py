from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.core import ratelimit
from app.core.permissions import permissions_for
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import ForgotPassword, LoginIn, MeOut, PasswordChange, TokenOut, UserOut

router = APIRouter(tags=["auth"])

GENERIC_FORGOT_MESSAGE = (
    "Si un compte actif correspond à cette adresse, l'administrateur a été informé de votre demande. "
    "Il vous contactera pour réinitialiser votre mot de passe."
)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnue"


def token_for(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.email, user.role, user.token_version), role=user.role, email=user.email)


async def _authenticate(db, request: Request, email: str, password: str) -> TokenOut:
    email = email.strip().lower()
    ip = client_ip(request)
    wait = ratelimit.retry_after(ip, email)
    if wait:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Trop de tentatives échouées. Réessayez dans {wait // 60 + 1} minute(s).",
            headers={"Retry-After": str(wait)},
        )
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        ratelimit.register_failure(ip, email)
        request.state.audit_user = email
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte désactivé : contactez l'administrateur")
    ratelimit.reset(ip, email)
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()
    return token_for(user)


@router.post("/auth/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, db: DB):
    return await _authenticate(db, request, body.email, body.password)


@router.post("/auth/token", response_model=TokenOut, include_in_schema=False)
async def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], request: Request, db: DB):
    """Endpoint OAuth2 (bouton Authorize de Swagger)."""
    return await _authenticate(db, request, form.username, form.password)


@router.get("/auth/me", response_model=MeOut)
async def me(user: CurrentUser):
    return MeOut(**UserOut.model_validate(user).model_dump(), permissions=sorted(permissions_for(user.role)))


@router.post("/auth/change-password", response_model=TokenOut)
async def change_password(body: PasswordChange, user: CurrentUser, db: DB):
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le nouveau mot de passe doit être différent de l'actuel")
    user.hashed_password = hash_password(body.new_password)
    user.token_version += 1  # invalide les autres sessions ; la session courante reçoit un nouveau jeton
    await db.commit()
    return token_for(user)


@router.post("/auth/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(body: ForgotPassword, request: Request, db: DB):
    """Mot de passe oublié (assisté) : la demande est signalée aux administrateurs (notification interne).

    La réponse est identique que le compte existe ou non (pas d'énumération de comptes). Un lien de
    réinitialisation envoyé par email n'est pas implémenté en v1.1 : voir docs/ADMIN.md.
    """
    from app.services import inbox

    email = body.email.strip().lower()
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is not None and user.is_active:
        await inbox.notify_password_reset_request(db, user)
    return {"detail": GENERIC_FORGOT_MESSAGE}

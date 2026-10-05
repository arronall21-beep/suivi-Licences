import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.api import assets, assignments, auth, contracts, inbox, reporting, users, vendors
from app.core.config import settings
from app.core.security import hash_password
from app.database import SessionLocal
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.models import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


async def ensure_default_users():
    seeds = (
        (settings.admin_email, settings.admin_password, "ADMIN", "Admin", "Système"),
        (settings.manager_email, settings.manager_password, "MANAGER", "Gestionnaire", "SI"),
        (settings.viewer_email, settings.viewer_password, "VIEWER", "Lecture", "Seule"),
    )
    async with SessionLocal() as db:
        for email, pwd, role, first, last in seeds:
            if not email or not pwd:
                continue
            exists = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
            if exists is None:
                db.add(
                    User(
                        email=email.lower(),
                        first_name=first,
                        last_name=last,
                        full_name=f"{first} {last}",
                        role=role,
                        hashed_password=hash_password(pwd),
                    )
                )
                log.info("Utilisateur %s (%s) créé", email, role)
        await db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_default_users()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Données invalides", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    log.exception("Erreur non gérée", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur"})


api = APIRouter(prefix="/api/v1")


@api.get("/health", tags=["health"])
async def health():
    db_ok = True
    try:
        async with SessionLocal() as db:
            await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unreachable", "version": app.version}


for r in (
    auth.router,
    users.router,
    inbox.router,
    vendors.router,
    contracts.router,
    assets.router,
    assignments.router,
    reporting.router,
):
    api.include_router(r)
app.include_router(api)

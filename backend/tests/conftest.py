import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://suivi:suivi@localhost:5432/suivi_test")
os.environ["ENVIRONMENT"] = "test"
os.environ["SCHEDULER_ENABLED"] = "false"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app, ensure_default_users  # noqa: E402

_schema_ready = False


@pytest.fixture(autouse=True)
async def clean_db():
    global _schema_ready
    async with engine.begin() as conn:
        if not _schema_ready:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            _schema_ready = True
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    await ensure_default_users()
    yield


@pytest.fixture
async def db():
    async with SessionLocal() as session:
        yield session


async def _client(email, password):
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    r = await c.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


@pytest.fixture
async def admin():
    c = await _client("admin@example.com", "admin123")
    yield c
    await c.aclose()


@pytest.fixture
async def viewer():
    c = await _client("viewer@example.com", "viewer123")
    yield c
    await c.aclose()


@pytest.fixture
async def anon():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

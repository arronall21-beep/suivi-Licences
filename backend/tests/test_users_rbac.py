import io

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from app.main import app
from tests.conftest import make_client

API = "/api/v1"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def new_user(email="agent@sbee.bj", role="VIEWER", password="Secret123", **kw):
    return {"first_name": "Awa", "last_name": "Dossou", "email": email, "role": role, "password": password, **kw}


async def login_raw(email, password):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post(f"{API}/auth/login", json={"email": email, "password": password})


# ---------- Gestion des utilisateurs ----------
async def test_admin_creates_users_with_each_role(admin):
    for role in ("ADMIN", "MANAGER", "VIEWER"):
        r = await admin.post(
            f"{API}/users", json=new_user(f"{role.lower()}.new@sbee.bj", role, phone="+22997000000", department="DSI")
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["role"] == role and body["is_active"] and body["department"] == "DSI"
        assert "password" not in body and "hashed_password" not in body
        assert (await login_raw(f"{role.lower()}.new@sbee.bj", "Secret123")).status_code == 200


async def test_duplicate_email_rejected(admin):
    assert (await admin.post(f"{API}/users", json=new_user())).status_code == 201
    r = await admin.post(f"{API}/users", json=new_user("AGENT@sbee.bj"))
    assert r.status_code == 409


@pytest.mark.parametrize("pwd", ["court1", "sanschiffres", "12345678", "agent@sbee.bj"])
async def test_password_policy_enforced(admin, pwd):
    r = await admin.post(f"{API}/users", json=new_user(password=pwd))
    assert r.status_code == 422


async def test_update_and_list_filters(admin):
    u = (await admin.post(f"{API}/users", json=new_user())).json()
    body = {k: u[k] for k in ("first_name", "last_name", "email", "phone", "department")} | {
        "role": "MANAGER",
        "department": "DRH",
    }
    r = await admin.put(f"{API}/users/{u['id']}", json=body)
    assert r.status_code == 200 and r.json()["role"] == "MANAGER" and r.json()["department"] == "DRH"
    managers = (await admin.get(f"{API}/users", params={"role": "MANAGER"})).json()
    assert {x["email"] for x in managers["items"]} == {"manager@example.com", "agent@sbee.bj"}
    assert (await admin.get(f"{API}/users", params={"q": "dossou"})).json()["total"] == 1
    assert (await admin.get(f"{API}/users", params={"state": "inactive"})).json()["total"] == 0


async def test_deactivation_is_immediate_and_reversible(admin):
    u = (await admin.post(f"{API}/users", json=new_user(role="MANAGER"))).json()
    session = await make_client("agent@sbee.bj", "Secret123")
    assert (await session.get(f"{API}/assets")).status_code == 200
    assert (await admin.post(f"{API}/users/{u['id']}/deactivate")).json()["is_active"] is False
    # Le jeton déjà émis est refusé immédiatement et la connexion est bloquée
    assert (await session.get(f"{API}/assets")).status_code == 401
    r = await login_raw("agent@sbee.bj", "Secret123")
    assert r.status_code == 403 and "désactivé" in r.json()["detail"]
    assert (await admin.post(f"{API}/users/{u['id']}/reactivate")).json()["is_active"] is True
    assert (await login_raw("agent@sbee.bj", "Secret123")).status_code == 200
    await session.aclose()


async def test_cannot_lock_out_last_admin(admin):
    me = (await admin.get(f"{API}/auth/me")).json()
    assert (await admin.post(f"{API}/users/{me['id']}/deactivate")).status_code == 409  # soi-même
    body = {k: me[k] for k in ("first_name", "last_name", "email")} | {"role": "VIEWER"}
    r = await admin.put(f"{API}/users/{me['id']}", json=body)
    assert r.status_code == 409 and "dernier administrateur" in r.json()["detail"]
    # Avec un second administrateur, la rétrogradation devient possible
    await admin.post(f"{API}/users", json=new_user("second.admin@sbee.bj", "ADMIN"))
    assert (await admin.put(f"{API}/users/{me['id']}", json=body)).status_code == 200


async def test_admin_reset_password_invalidates_sessions(admin):
    u = (await admin.post(f"{API}/users", json=new_user())).json()
    session = await make_client("agent@sbee.bj", "Secret123")
    assert (await admin.post(f"{API}/users/{u['id']}/reset-password", json={"password": "faible"})).status_code == 422
    assert (await admin.post(f"{API}/users/{u['id']}/reset-password", json={"password": "Nouveau456"})).status_code == 200
    assert (await session.get(f"{API}/assets")).status_code == 401
    assert (await login_raw("agent@sbee.bj", "Secret123")).status_code == 401
    assert (await login_raw("agent@sbee.bj", "Nouveau456")).status_code == 200
    await session.aclose()


async def test_change_own_password(viewer):
    r = await viewer.post(f"{API}/auth/change-password", json={"current_password": "mauvais", "new_password": "Nouveau456"})
    assert r.status_code == 400
    r = await viewer.post(f"{API}/auth/change-password", json={"current_password": "viewer123", "new_password": "Nouveau456"})
    assert r.status_code == 200
    assert (await login_raw("viewer@example.com", "Nouveau456")).status_code == 200
    assert (await viewer.get(f"{API}/assets")).status_code == 401  # ancienne session invalidée


async def test_last_login_and_me_permissions(admin, manager, viewer):
    users = (await admin.get(f"{API}/users")).json()["items"]
    assert all(u["last_login_at"] for u in users)  # les 3 comptes se sont connectés via les fixtures
    perms = {
        name: set((await c.get(f"{API}/auth/me")).json()["permissions"])
        for name, c in (("m", manager), ("v", viewer), ("a", admin))
    }
    assert "data:write" in perms["m"] and "admin:users" not in perms["m"]
    assert "data:write" not in perms["v"] and "data:read" in perms["v"]
    assert {"admin:users", "import:run", "data:delete"} <= perms["a"]


async def test_login_rate_limit(anon):
    for _ in range(5):
        assert (await anon.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "x"})).status_code == 401
    r = await anon.post(f"{API}/auth/login", json={"email": "admin@example.com", "password": "admin123"})
    assert r.status_code == 429 and "Retry-After" in r.headers


async def test_forgot_password_is_generic_and_notifies_admins(anon, admin):
    known = await anon.post(f"{API}/auth/forgot-password", json={"email": "viewer@example.com"})
    unknown = await anon.post(f"{API}/auth/forgot-password", json={"email": "personne@sbee.bj"})
    assert known.status_code == unknown.status_code == 202 and known.json() == unknown.json()
    inbox = (await admin.get(f"{API}/inbox")).json()
    assert [n["kind"] for n in inbox["items"]] == ["PASSWORD_RESET_REQUEST"]


# ---------- RBAC : matrice rôle × endpoint ----------
def tiny_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "Licences_Logicielles"
    ws.append(["ID", "Logiciel", "Nb licences"])
    ws.append(["LIC-001", "Office", 5])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def test_rbac_matrix(admin, manager, viewer, anon):
    asset = {"category": "LICENCE", "name": "Office", "total_quantity": 10}
    # Anonyme
    assert (await anon.get(f"{API}/assets")).status_code == 401
    assert (await anon.get(f"{API}/users")).status_code == 401

    # VIEWER : lecture seule
    assert (await viewer.get(f"{API}/assets")).status_code == 200
    assert (await viewer.get(f"{API}/dashboard")).status_code == 200
    assert (await viewer.get(f"{API}/export/excel")).status_code == 200
    for method, url, kw in [
        ("post", "/assets", {"json": asset}),
        ("post", "/vendors", {"json": {"name": "V"}}),
        ("post", "/contracts", {"json": {"scope": "x"}}),
        ("post", "/assignments", {"json": {"asset_id": 1, "assigned_to_user": "x", "quantity": 1}}),
        ("post", "/import/excel", {"files": {"file": ("f.xlsx", tiny_workbook(), XLSX)}}),
        ("post", "/alerts/run", {}),
        ("get", "/users", {}),
        ("get", "/roles", {}),
        ("get", "/admin/settings/general", {}),
        ("get", "/admin/settings/alerts", {}),
        ("get", "/admin/settings/smtp", {}),
        ("post", "/admin/settings/smtp/test-email", {"json": {}}),
    ]:
        r = await getattr(viewer, method)(f"{API}{url}", **kw)
        assert r.status_code == 403, (method, url, r.status_code)

    # MANAGER : données métier oui, administration / import / suppression non
    created = await manager.post(f"{API}/assets", json=asset)
    assert created.status_code == 201
    aid = created.json()["id"]
    assert (await manager.put(f"{API}/assets/{aid}", json={**asset, "name": "Office 365"})).status_code == 200
    assert (await manager.post(f"{API}/vendors", json={"name": "V"})).status_code == 201
    assert (await manager.post(f"{API}/contracts", json={"scope": "x"})).status_code == 201
    a = await manager.post(f"{API}/assignments", json={"asset_id": aid, "assigned_to_user": "x", "quantity": 2})
    assert a.status_code == 201
    assert (await manager.delete(f"{API}/assignments/{a.json()['id']}")).status_code == 204  # désaffectation
    assert (await manager.delete(f"{API}/assets/{aid}")).status_code == 403
    for method, url, kw in [
        ("post", "/import/excel", {"files": {"file": ("f.xlsx", tiny_workbook(), XLSX)}}),
        ("post", "/alerts/run", {}),
        ("get", "/users", {}),
        ("post", "/users", {"json": new_user()}),
        ("get", "/admin/settings/general", {}),
        ("put", "/admin/settings/general", {"json": {}}),
        ("get", "/admin/settings/smtp", {}),
    ]:
        r = await getattr(manager, method)(f"{API}{url}", **kw)
        assert r.status_code == 403, (method, url, r.status_code)

    # ADMIN : tout
    assert (await admin.post(f"{API}/import/excel", files={"file": ("f.xlsx", tiny_workbook(), XLSX)})).status_code == 200
    assert (await admin.get(f"{API}/users")).status_code == 200
    assert (await admin.delete(f"{API}/assets/{aid}")).status_code == 204

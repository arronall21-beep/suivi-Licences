"""LOT 1.1 (D2) : les routes d'administration système restent fermées aux rôles métier, MÊME s'ils reçoivent par
erreur une permission d'administration. La frontière repose sur `require_permission(..., system=True)` : la
permission ET le rôle ADMIN.

Chaque test comporte un témoin positif (la permission injectée ouvre bien une route de gouvernance) afin de prouver
que l'injection est effective et que le refus des routes système ne vient pas d'une injection sans effet.
"""

import types

import pytest
from fastapi import HTTPException
from sqlalchemy import update

from app.api.deps import require_permission
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import create_access_token
from app.models import User
from tests.test_access_matrix import _api_routes, _policy_of

API = "/api/v1"
ANY_ID = 999999
SYSTEM_MESSAGE = "Droits administrateur requis"

# Routes d'administration système (liste écrite à la main : le test échoue si elle diverge de ce que les routes déclarent)
SYSTEM_ROUTES = {
    ("GET", f"{API}/users"),
    ("POST", f"{API}/users"),
    ("PUT", f"{API}/users/{{user_id}}"),
    ("POST", f"{API}/users/{{user_id}}/deactivate"),
    ("POST", f"{API}/users/{{user_id}}/reactivate"),
    ("POST", f"{API}/users/{{user_id}}/reset-password"),
    ("GET", f"{API}/roles"),
    ("GET", f"{API}/admin/settings/smtp"),
    ("PUT", f"{API}/admin/settings/smtp"),
    ("POST", f"{API}/admin/settings/smtp/test-connection"),
    ("POST", f"{API}/admin/settings/smtp/test-email"),
    ("GET", f"{API}/admin/system"),
}
# Routes de gouvernance (permission seule, volontairement) : servent de témoin positif
GOVERNANCE_WITNESSES = [f"{API}/admin/audit", f"{API}/admin/settings/general"]


def all_admin_permissions() -> frozenset[str]:
    return frozenset(ROLE_PERMISSIONS["ADMIN"])


def grant_everything(monkeypatch, role: str):
    monkeypatch.setitem(ROLE_PERMISSIONS, role, all_admin_permissions())


async def call(client, method: str, template: str, headers=None):
    path = template.replace("{user_id}", str(ANY_ID))
    kw = {} if method == "GET" else {"json": {}}
    return await client.request(method, path, headers=headers, **kw)


async def assert_system_routes_closed(client, who: str, headers=None):
    failures = []
    for method, template in sorted(SYSTEM_ROUTES):
        r = await call(client, method, template, headers)
        if r.status_code != 403 or r.json().get("detail") != SYSTEM_MESSAGE:
            failures.append(f"{who} {method} {template} -> {r.status_code} {r.text[:80]}")
    assert not failures, "\n".join(failures)


async def assert_governance_open(client, who: str, headers=None):
    """Témoin : l'injection est effective (ces routes ne demandent que la permission)."""
    for path in GOVERNANCE_WITNESSES:
        r = await client.get(path, headers=headers)
        assert r.status_code == 200, (who, path, r.status_code)


def test_system_routes_declare_system_policy():
    """Les routes déclarées `system=True` sont exactement la liste attendue (aucune oubliée, aucune en trop)."""
    declared = {(m, p) for m, p, route in _api_routes() if (pol := _policy_of(route)) is not None and pol[1]}
    assert declared == SYSTEM_ROUTES, {
        "en_trop": sorted(declared - SYSTEM_ROUTES),
        "manquantes": sorted(SYSTEM_ROUTES - declared),
    }


async def test_manager_with_injected_admin_permissions_cannot_use_system_routes(monkeypatch, manager):
    grant_everything(monkeypatch, "MANAGER")
    me = (await manager.get(f"{API}/auth/me")).json()
    assert {"admin:users", "admin:smtp", "admin:system"} <= set(me["permissions"])  # l'injection est bien visible
    await assert_governance_open(manager, "MANAGER")
    await assert_system_routes_closed(manager, "MANAGER")


async def test_viewer_with_injected_admin_permissions_cannot_use_system_routes(monkeypatch, viewer):
    grant_everything(monkeypatch, "VIEWER")
    await assert_governance_open(viewer, "VIEWER")
    await assert_system_routes_closed(viewer, "VIEWER")


async def test_each_system_permission_alone_is_not_enough(monkeypatch, manager):
    for permission in ("admin:users", "admin:smtp", "admin:system"):
        monkeypatch.setitem(ROLE_PERMISSIONS, "MANAGER", frozenset(ROLE_PERMISSIONS["MANAGER"] | {permission}))
        await assert_system_routes_closed(manager, f"MANAGER+{permission}")


async def test_future_business_role_cannot_use_system_routes(db, monkeypatch, anon):
    """Tout rôle métier ajouté plus tard (ici « OPERATEUR ») est refusé sur les routes système, permissions injectées comprises."""
    await db.execute(update(User).where(User.email == "viewer@example.com").values(role="OPERATEUR"))
    await db.commit()
    monkeypatch.setitem(ROLE_PERMISSIONS, "OPERATEUR", all_admin_permissions())
    login = await anon.post(f"{API}/auth/login", json={"email": "viewer@example.com", "password": "viewer123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    await assert_governance_open(anon, "OPERATEUR", headers)
    await assert_system_routes_closed(anon, "OPERATEUR", headers)


async def test_forged_admin_claim_with_injected_permissions_is_still_refused(monkeypatch, anon):
    grant_everything(monkeypatch, "MANAGER")
    forged = {"Authorization": f"Bearer {create_access_token('manager@example.com', 'ADMIN', 0)}"}
    await assert_system_routes_closed(anon, "MANAGER (jeton ADMIN falsifié)", forged)


async def test_admin_needs_the_permission_in_addition_to_the_role(monkeypatch, admin):
    """Les deux conditions s'appliquent : retirer une permission à ADMIN ferme la route correspondante."""
    for removed, path in (
        ("admin:users", f"{API}/users"),
        ("admin:smtp", f"{API}/admin/settings/smtp"),
        ("admin:system", f"{API}/admin/system"),
    ):
        assert (await admin.get(path)).status_code == 200, path  # avec la permission : autorisé
        monkeypatch.setitem(ROLE_PERMISSIONS, "ADMIN", frozenset(ROLE_PERMISSIONS["ADMIN"] - {removed}))
        r = await admin.get(path)
        assert r.status_code == 403 and r.json()["detail"] == "Droits insuffisants pour cette action", path
        monkeypatch.undo()


@pytest.mark.parametrize("role", ["MANAGER", "VIEWER", "OPERATEUR", "INCONNU"])
async def test_dependency_rejects_non_admin_roles_even_with_permission(monkeypatch, role):
    """Test de la dépendance elle-même (en complément des tests d'intégration ci-dessus)."""
    monkeypatch.setitem(ROLE_PERMISSIONS, role, all_admin_permissions())
    checker = require_permission("admin:users", system=True)
    assert checker.__policy__ == {"permission": "admin:users", "system": True}
    with pytest.raises(HTTPException) as exc:
        await checker(user=types.SimpleNamespace(role=role))
    assert exc.value.status_code == 403 and exc.value.detail == SYSTEM_MESSAGE
    assert (await checker(user=types.SimpleNamespace(role="ADMIN"))).role == "ADMIN"

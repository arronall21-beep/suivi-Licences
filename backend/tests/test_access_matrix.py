"""Matrice d'accès (LOT 1) : droits effectifs de chaque rôle sur CHAQUE route de l'API.

- `test_effective_access_matrix` fige les droits effectifs ADMIN / MANAGER / VIEWER / anonyme. Il doit donner
  le même résultat avant et après toute refonte des dépendances d'autorisation.
- `test_every_route_is_listed` échoue si une route est ajoutée sans politique explicite (route oubliée).
- `test_declared_policies` vérifie que chaque route déclare bien la permission attendue (et pas seulement un rôle).
- Les autres tests couvrent l'absence d'escalade (jeton altéré, rôle inconnu, audience des notifications).
"""

import jwt
from sqlalchemy import update

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.permissions import ROLE_PERMISSIONS
from app.core.security import create_access_token
from app.main import app
from app.models import User

API = "/api/v1"
ANY_ID = 999999  # identifiant inexistant : une requête autorisée finit en 404/422, jamais en 401/403

# Qui a le droit d'appeler la route (droits effectifs constatés avant le LOT 1)
ALLOWED = {
    "public": {"anon", "VIEWER", "MANAGER", "ADMIN"},
    "auth": {"VIEWER", "MANAGER", "ADMIN"},
    "writer": {"MANAGER", "ADMIN"},
    "admin": {"ADMIN"},
}

# (méthode, chemin complet) -> catégorie de droits effectifs
ROUTES: dict[tuple[str, str], str] = {}


def _add(category: str, *routes: str):
    for r in routes:
        method, path = r.split(" ", 1)
        ROUTES[(method, path)] = category


_add("public", "GET /api/docs", "GET /api/openapi.json", f"GET {API}/health", f"GET {API}/public/config")
# Routes intégrées de FastAPI, publiques (redoc_url par défaut ; redirection OAuth de Swagger) : aucune donnée métier
_add("public", "GET /redoc", "GET /docs/oauth2-redirect")
_add("public", f"POST {API}/auth/login", f"POST {API}/auth/token", f"POST {API}/auth/forgot-password")
_add(
    "auth",
    f"GET {API}/auth/me",
    f"POST {API}/auth/change-password",
    f"GET {API}/config",
    f"GET {API}/assets",
    f"GET {API}/assets/options",
    f"GET {API}/assets/{{asset_id}}",
    f"GET {API}/contracts",
    f"GET {API}/contracts/{{contract_id}}",
    f"GET {API}/vendors",
    f"GET {API}/vendors/{{vendor_id}}",
    f"GET {API}/assignments",
    f"GET {API}/dashboard",
    f"GET {API}/renewals",
    f"GET {API}/search",
    f"GET {API}/alerts",
    f"GET {API}/notifications",
    f"GET {API}/export/excel",
    f"GET {API}/export/licences",
    f"GET {API}/export/contrats",
    f"GET {API}/export/echeances",
    f"GET {API}/export/planning",
    f"GET {API}/inbox",
    f"GET {API}/inbox/unread-count",
    f"POST {API}/inbox/read-all",
    f"POST {API}/inbox/{{notification_id}}/read",
)
_add(
    "writer",
    f"POST {API}/assets",
    f"PUT {API}/assets/{{asset_id}}",
    f"POST {API}/contracts",
    f"PUT {API}/contracts/{{contract_id}}",
    f"POST {API}/vendors",
    f"PUT {API}/vendors/{{vendor_id}}",
    f"POST {API}/assignments",
    f"PUT {API}/assignments/{{assignment_id}}",
    f"DELETE {API}/assignments/{{assignment_id}}",
)
_add(
    "admin",
    f"DELETE {API}/assets/{{asset_id}}",
    f"DELETE {API}/contracts/{{contract_id}}",
    f"DELETE {API}/vendors/{{vendor_id}}",
    f"POST {API}/import/excel",
    f"GET {API}/import/history",
    f"GET {API}/import/history/{{log_id}}",
    f"POST {API}/alerts/run",
    f"GET {API}/users",
    f"POST {API}/users",
    f"PUT {API}/users/{{user_id}}",
    f"POST {API}/users/{{user_id}}/deactivate",
    f"POST {API}/users/{{user_id}}/reactivate",
    f"POST {API}/users/{{user_id}}/reset-password",
    f"GET {API}/roles",
    f"GET {API}/admin/settings/general",
    f"PUT {API}/admin/settings/general",
    f"GET {API}/admin/settings/alerts",
    f"PUT {API}/admin/settings/alerts",
    f"GET {API}/admin/settings/smtp",
    f"PUT {API}/admin/settings/smtp",
    f"POST {API}/admin/settings/smtp/test-connection",
    f"POST {API}/admin/settings/smtp/test-email",
    f"GET {API}/admin/audit",
    f"GET {API}/admin/audit/actions",
    f"GET {API}/admin/system",
)

# Politique déclarée attendue : (permission, réservé au rôle ADMIN en plus de la permission)
DECLARED: dict[tuple[str, str], tuple[str | None, bool]] = {}


def _declare(permission: str | None, system: bool, *routes: str):
    for r in routes:
        method, path = r.split(" ", 1)
        DECLARED[(method, f"{API}{path}")] = (permission, system)


_declare(None, False, "GET /auth/me", "POST /auth/change-password", "GET /config")
_declare(
    "data:read",
    False,
    "GET /assets",
    "GET /assets/options",
    "GET /assets/{asset_id}",
    "GET /contracts",
    "GET /contracts/{contract_id}",
    "GET /vendors",
    "GET /vendors/{vendor_id}",
    "GET /assignments",
    "GET /dashboard",
    "GET /renewals",
    "GET /search",
    "GET /alerts",
    "GET /notifications",
)
_declare(
    "export:run",
    False,
    "GET /export/excel",
    "GET /export/licences",
    "GET /export/contrats",
    "GET /export/echeances",
    "GET /export/planning",
)
_declare(
    "notifications:read",
    False,
    "GET /inbox",
    "GET /inbox/unread-count",
    "POST /inbox/read-all",
    "POST /inbox/{notification_id}/read",
)
_declare(
    "data:write",
    False,
    "POST /assets",
    "PUT /assets/{asset_id}",
    "POST /contracts",
    "PUT /contracts/{contract_id}",
    "POST /vendors",
    "PUT /vendors/{vendor_id}",
    "POST /assignments",
    "PUT /assignments/{assignment_id}",
    "DELETE /assignments/{assignment_id}",
)
_declare("data:delete", False, "DELETE /assets/{asset_id}", "DELETE /contracts/{contract_id}", "DELETE /vendors/{vendor_id}")
_declare("import:run", False, "POST /import/excel", "GET /import/history", "GET /import/history/{log_id}")
_declare("alerts:run", False, "POST /alerts/run")
_declare(
    "admin:users",
    True,
    "GET /users",
    "POST /users",
    "PUT /users/{user_id}",
    "POST /users/{user_id}/deactivate",
    "POST /users/{user_id}/reactivate",
    "POST /users/{user_id}/reset-password",
    "GET /roles",
)
_declare(
    "admin:settings",
    False,
    "GET /admin/settings/general",
    "PUT /admin/settings/general",
    "GET /admin/settings/alerts",
    "PUT /admin/settings/alerts",
)
_declare(
    "admin:smtp",
    True,
    "GET /admin/settings/smtp",
    "PUT /admin/settings/smtp",
    "POST /admin/settings/smtp/test-connection",
    "POST /admin/settings/smtp/test-email",
)
_declare("admin:audit", False, "GET /admin/audit", "GET /admin/audit/actions")
_declare("admin:system", True, "GET /admin/system")


def _api_routes():
    for r in app.routes:
        if not hasattr(r, "methods"):
            continue
        for m in sorted(r.methods - {"HEAD", "OPTIONS"}):
            yield m, r.path, r


def _policy_of(route) -> tuple[str | None, bool] | None:
    """Politique déclarée par les dépendances de la route : (permission, système) ; None si aucune authentification."""
    found: list[dict] = []
    authenticated = False
    if getattr(route, "dependant", None) is None:  # route intégrée (documentation) : aucune dépendance
        return None

    def walk(dep):
        nonlocal authenticated
        for d in dep.dependencies:
            if d.call is get_current_user:
                authenticated = True
            pol = getattr(d.call, "__policy__", None)
            if pol is not None:
                found.append(pol)
            walk(d)

    walk(route.dependant)
    if found:
        perms = [p for p in found if p["permission"]]
        pol = perms[0] if perms else found[0]
        return pol["permission"], pol["system"]
    return (None, False) if authenticated else None


# --------------------------------------------------------------------------------------------------------------------


async def test_every_route_is_listed():
    actual = {(m, p) for m, p, _ in _api_routes()}
    assert actual == set(ROUTES), {"non_listees": sorted(actual - set(ROUTES)), "disparues": sorted(set(ROUTES) - actual)}


async def test_effective_access_matrix(anon, viewer, manager, admin):
    clients = {"anon": anon, "VIEWER": viewer, "MANAGER": manager, "ADMIN": admin}
    mismatches = []
    for (method, template), category in sorted(ROUTES.items()):
        path = template
        for name in (
            "{asset_id}",
            "{contract_id}",
            "{vendor_id}",
            "{assignment_id}",
            "{user_id}",
            "{log_id}",
            "{notification_id}",
        ):
            path = path.replace(name, str(ANY_ID))
        if path.endswith("/search"):
            path += "?q=ab"
        for who, client in clients.items():
            kw = {} if method == "GET" else {"json": {}}
            r = await client.request(method, path, **kw)
            authorized = r.status_code not in (401, 403)
            expected = who in ALLOWED[category]
            if authorized != expected:
                mismatches.append(
                    f"{who:8} {method:6} {template} -> {r.status_code} (attendu {'autorisé' if expected else 'refusé'})"
                )
            if who == "anon" and category != "public" and r.status_code != 401:
                mismatches.append(f"anon     {method:6} {template} -> {r.status_code} (401 attendu)")
    assert not mismatches, "\n".join(mismatches)


async def test_declared_policies():
    """Chaque route protégée déclare sa permission : plus de contrôle fondé sur le seul nom de rôle."""
    problems = []
    for method, path, route in _api_routes():
        category = ROUTES.get((method, path))
        if category == "public":
            if _policy_of(route) is not None:
                problems.append(f"{method} {path} : route publique mais authentifiée")
            continue
        expected = DECLARED.get((method, path))
        got = _policy_of(route)
        if expected is None:
            problems.append(f"{method} {path} : politique attendue non décrite")
        elif got != expected:
            problems.append(f"{method} {path} : déclaré {got}, attendu {expected}")
    assert not problems, "\n".join(problems)


def test_role_permission_sets_are_frozen():
    """Ajouts depuis la matrice d'origine : `notifications:admin` (LOT 1) et `notifications:security` (LOT 1.1), ADMIN seul ;
    `secrets:read` (correctif de sécurité), ADMIN et MANAGER, jamais VIEWER."""
    read = {"data:read", "export:run", "notifications:read"}
    assert ROLE_PERMISSIONS["VIEWER"] == frozenset(read)
    assert ROLE_PERMISSIONS["MANAGER"] == frozenset(read | {"data:write", "secrets:read"})
    assert ROLE_PERMISSIONS["ADMIN"] == frozenset(
        read
        | {"data:write", "secrets:read", "data:delete", "import:run", "alerts:run"}
        | {"admin:users", "admin:settings", "admin:smtp", "admin:audit", "admin:system"}
        | {"notifications:admin", "notifications:security"}
    )
    assert set(ROLE_PERMISSIONS) == {"ADMIN", "MANAGER", "VIEWER"}  # le LOT 1 ne crée aucun rôle


# --- absence d'escalade ---------------------------------------------------------------------------------------------


async def test_forged_role_claim_is_ignored(manager, anon):
    """Un jeton signé avec un rôle ADMIN mais pour un compte MANAGER n'élève pas les droits (rôle relu en base)."""
    token = create_access_token("manager@example.com", "ADMIN", 0)
    r = await anon.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    r = await anon.get(f"{API}/admin/audit", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


async def test_tampered_or_foreign_token_rejected(anon):
    good = create_access_token("admin@example.com", "ADMIN", 0)
    forged = jwt.encode({"sub": "admin@example.com", "role": "ADMIN", "tv": 0}, "autre-cle", algorithm="HS256")
    unsigned = good.rsplit(".", 1)[0] + ".x"
    for token in (forged, unsigned, "n-importe-quoi"):
        r = await anon.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, token[:12]
    none_alg = jwt.encode({"sub": "admin@example.com", "role": "ADMIN", "tv": 0}, "", algorithm="none")
    assert (await anon.get(f"{API}/users", headers={"Authorization": f"Bearer {none_alg}"})).status_code == 401
    assert settings.jwt_algorithm == "HS256"


async def test_account_with_unknown_role_has_no_access(db, anon):
    """Un compte dont le rôle n'existe pas dans la matrice n'obtient AUCUN droit, même en lecture."""
    await db.execute(update(User).where(User.email == "viewer@example.com").values(role="ROLE_INCONNU"))
    await db.commit()
    login = await anon.post(f"{API}/auth/login", json={"email": "viewer@example.com", "password": "viewer123"})
    assert login.status_code == 200
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    for path in ("/assets", "/dashboard", "/export/excel", "/inbox", "/search?q=ab", "/users", "/admin/audit"):
        assert (await anon.get(f"{API}{path}", headers=h)).status_code == 403, path
    me = await anon.get(f"{API}/auth/me", headers=h)  # l'identité reste consultable
    assert me.status_code == 200 and me.json()["permissions"] == []


async def test_admin_audience_notifications_are_not_visible_to_other_roles(admin, manager, viewer, anon):
    await anon.post(f"{API}/auth/forgot-password", json={"email": "viewer@example.com"})  # notification d'audience ADMIN
    seen_by_admin = (await admin.get(f"{API}/inbox")).json()["items"]
    assert any(n["kind"] == "PASSWORD_RESET_REQUEST" for n in seen_by_admin)
    for c in (manager, viewer):
        assert (await c.get(f"{API}/inbox")).json()["items"] == []
        assert (await c.post(f"{API}/inbox/{seen_by_admin[0]['id']}/read")).status_code == 404
    assert (await admin.post(f"{API}/inbox/{seen_by_admin[0]['id']}/read")).status_code == 200


async def test_user_search_is_reserved_to_user_admins(admin, manager):
    assert (await admin.get(f"{API}/search", params={"q": "example"})).json()["users"]
    assert (await manager.get(f"{API}/search", params={"q": "example"})).json()["users"] == []

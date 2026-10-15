"""LOT 1.1 (D1) : audiences des notifications internes.

Les demandes de réinitialisation de mot de passe (sécurité des comptes) ne doivent être visibles que des titulaires
de `notifications:security`. La permission `notifications:admin` (imports, pilotage) ne doit jamais les ouvrir, ni en
lecture (liste, compteur, « tout lire ») ni en marquage « lu ».
"""

from sqlalchemy import select

from app.core.permissions import ROLE_PERMISSIONS
from app.models import AppNotification, AppNotificationRead, User
from app.services import inbox

API = "/api/v1"
SECURITY = "PASSWORD_RESET_REQUEST"


def grant(monkeypatch, role: str, *permissions: str):
    """Accorde artificiellement des permissions à un rôle (restauré en fin de test)."""
    monkeypatch.setitem(ROLE_PERMISSIONS, role, frozenset(ROLE_PERMISSIONS[role] | set(permissions)))


async def seed(db) -> dict[str, int]:
    """Cinq notifications couvrant tous les cas, dont deux lignes de sécurité « historiques » (audience ADMIN / ALL)."""
    spec = {
        "alerte": ("LICENSE_EXPIRED", "ALL"),
        "import": ("IMPORT_DONE", "ADMIN"),
        "import_erreur": ("IMPORT_ERROR", "ADMIN"),
        "reset_historique": (SECURITY, "ADMIN"),  # lignes déjà en base avant le LOT 1.1
        "reset_mal_classe": (SECURITY, "ALL"),  # erreur de saisie d'audience : doit rester invisible
        "reset_nouveau": (SECURITY, inbox.AUDIENCE_SECURITY),
    }
    ids = {}
    for key, (kind, audience) in spec.items():
        n = await inbox.create_notification(db, kind, f"{kind} ({key})", "x@sbee.bj", audience=audience, dedupe_key=key)
        ids[key] = n.id
    await db.commit()
    return ids


async def titles(client) -> set[str]:
    r = await client.get(f"{API}/inbox", params={"size": 100})
    assert r.status_code == 200
    return {n["title"] for n in r.json()["items"]}


def keys_of(ids: dict[str, int], seen_titles: set[str]) -> set[str]:
    return {k for k in ids if any(t.endswith(f"({k})") for t in seen_titles)}


async def test_default_roles_visibility(db, admin, manager, viewer):
    ids = await seed(db)
    # ADMIN : visibilité complète, identique à celle d'avant le lot
    assert keys_of(ids, await titles(admin)) == set(ids)
    # MANAGER et VIEWER : seulement les notifications destinées à tous, jamais la sécurité ni les imports
    for client in (manager, viewer):
        assert keys_of(ids, await titles(client)) == {"alerte"}


async def test_business_admin_permission_never_opens_security_notifications(db, monkeypatch, manager):
    ids = await seed(db)
    grant(monkeypatch, "MANAGER", "notifications:admin")  # permission d'administration MÉTIER injectée
    seen = keys_of(ids, await titles(manager))
    assert seen == {"alerte", "import", "import_erreur"}  # imports visibles, sécurité JAMAIS
    assert not seen & {"reset_historique", "reset_mal_classe", "reset_nouveau"}


async def test_security_permission_opens_only_security_notifications(db, monkeypatch, manager):
    ids = await seed(db)
    grant(monkeypatch, "MANAGER", "notifications:security")
    assert keys_of(ids, await titles(manager)) == {"alerte", "reset_historique", "reset_mal_classe", "reset_nouveau"}


async def test_both_permissions_see_everything(db, monkeypatch, manager):
    ids = await seed(db)
    grant(monkeypatch, "MANAGER", "notifications:admin", "notifications:security")
    assert keys_of(ids, await titles(manager)) == set(ids)


async def test_mark_read_cannot_bypass_audience(db, monkeypatch, manager):
    ids = await seed(db)
    grant(monkeypatch, "MANAGER", "notifications:admin")
    for key in ("reset_historique", "reset_mal_classe", "reset_nouveau"):
        assert (await manager.post(f"{API}/inbox/{ids[key]}/read")).status_code == 404, key
    assert (await manager.post(f"{API}/inbox/{ids['import']}/read")).status_code == 200  # notification métier autorisée
    assert (await manager.post(f"{API}/inbox/{ids['alerte']}/read")).status_code == 200
    manager_id = (await db.execute(select(User.id).where(User.email == "manager@example.com"))).scalar_one()
    read = set(
        (await db.execute(select(AppNotificationRead.notification_id).where(AppNotificationRead.user_id == manager_id))).scalars()
    )
    assert read == {ids["import"], ids["alerte"]}


async def test_read_all_and_unread_count_respect_audience(db, monkeypatch, manager, viewer):
    ids = await seed(db)
    # sans permission supplémentaire : seul l'alerte « tous » compte
    assert (await viewer.get(f"{API}/inbox/unread-count")).json()["unread"] == 1
    grant(monkeypatch, "MANAGER", "notifications:admin")
    assert (await manager.get(f"{API}/inbox/unread-count")).json()["unread"] == 3  # alerte + 2 imports, pas la sécurité
    assert (await manager.post(f"{API}/inbox/read-all")).status_code == 200
    manager_id = (await db.execute(select(User.id).where(User.email == "manager@example.com"))).scalar_one()
    read = set(
        (await db.execute(select(AppNotificationRead.notification_id).where(AppNotificationRead.user_id == manager_id))).scalars()
    )
    assert read == {ids["alerte"], ids["import"], ids["import_erreur"]}  # aucune ligne de sécurité marquée
    assert (await manager.get(f"{API}/inbox/unread-count")).json()["unread"] == 0


async def test_password_reset_request_is_security_scoped_and_leaks_nothing(db, anon, admin, manager, viewer):
    await anon.post(f"{API}/auth/forgot-password", json={"email": "viewer@example.com"})
    row = (await db.execute(select(AppNotification).where(AppNotification.kind == SECURITY))).scalar_one()
    assert row.audience == inbox.AUDIENCE_SECURITY
    seen_by_admin = (await admin.get(f"{API}/inbox")).json()["items"]
    assert [n["kind"] for n in seen_by_admin] == [SECURITY]
    for client in (manager, viewer):
        r = await client.get(f"{API}/inbox")
        assert r.json()["items"] == [] and "viewer@example.com" not in r.text
        assert (await client.get(f"{API}/inbox/unread-count")).json()["unread"] == 0
        assert (await client.post(f"{API}/inbox/{row.id}/read")).status_code == 404


async def test_import_notifications_keep_working_for_admin_only(admin, manager):
    """Comportement existant préservé : l'import d'un fichier invalide notifie les seuls habilités."""
    r = await admin.post(f"{API}/import/excel", files={"file": ("x.txt", b"nope", "text/plain")})
    assert r.status_code == 415
    assert "IMPORT_ERROR" in {n["kind"] for n in (await admin.get(f"{API}/inbox")).json()["items"]}
    assert (await manager.get(f"{API}/inbox")).json()["items"] == []

"""Corrections de suivi de la revue RBAC : adresse IP du client (limitation des connexions) et recherche globale.

Les tests s'exécutent sans nginx : l'effet de `TRUSTED_PROXY_COUNT` est vérifié en simulant l'en-tête X-Forwarded-For tel que
nginx le produit (`$proxy_add_x_forwarded_for` : valeur reçue du client, suivie de l'adresse vue par nginx). La configuration
nginx réelle n'est pas exercée ici.
"""

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings, settings
from app.core.http import client_ip
from app.core.permissions import ROLE_PERMISSIONS, has_system_permission

API = "/api/v1"
EMAIL = "admin@example.com"
PEER = "127.0.0.1"  # adresse de la connexion dans les tests (ASGITransport)


def request_with(forwarded: str | None, peer: str | None = PEER) -> Request:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    return Request({"type": "http", "headers": headers, "client": (peer, 1234) if peer else None})


async def bad_login(client, email: str = EMAIL, forwarded: str | None = None) -> int:
    headers = {} if forwarded is None else {"X-Forwarded-For": forwarded}
    r = await client.post(f"{API}/auth/login", json={"email": email, "password": "mauvais-mot-de-passe"}, headers=headers)
    return r.status_code


def trust(monkeypatch, count: int):
    monkeypatch.setattr(settings, "trusted_proxy_count", count)


# --- client_ip : unités ---------------------------------------------------------------------------------------------


def test_without_trusted_proxy_the_header_is_ignored(monkeypatch):
    trust(monkeypatch, 0)
    assert client_ip(request_with("203.0.113.9")) == PEER
    assert client_ip(request_with("1.1.1.1, 2.2.2.2")) == PEER
    assert client_ip(request_with(None, peer=None)) == "inconnue"


def test_one_proxy_uses_the_entry_added_by_that_proxy(monkeypatch):
    trust(monkeypatch, 1)
    assert client_ip(request_with("203.0.113.9")) == "203.0.113.9"
    # tout ce que le client a écrit à gauche est ignoré
    assert client_ip(request_with("6.6.6.6, 7.7.7.7, 203.0.113.9")) == "203.0.113.9"


def test_two_proxies_use_the_second_entry_from_the_right(monkeypatch):
    trust(monkeypatch, 2)
    assert client_ip(request_with("6.6.6.6, 198.51.100.7, 10.0.0.2")) == "198.51.100.7"
    assert client_ip(request_with("203.0.113.9")) == PEER  # moins d'entrées que de proxies : on ne devine pas


@pytest.mark.parametrize(
    "header",
    [None, "", "   ", ",", " , ,", "garbage", "999.1.1.1", "1.2.3.4:8080", "unknown", "a, b", "x" * 500, "203.0.113.9; for=evil"],
)
def test_missing_or_malformed_header_falls_back_to_the_connection_address(monkeypatch, header):
    trust(monkeypatch, 1)
    assert client_ip(request_with(header)) == PEER


def test_addresses_are_normalized(monkeypatch):
    trust(monkeypatch, 1)
    assert client_ip(request_with("2001:DB8:0:0:0:0:0:1")) == client_ip(request_with("2001:db8::1")) == "2001:db8::1"
    assert client_ip(request_with("::ffff:203.0.113.9")) == "203.0.113.9"
    assert client_ip(request_with(" 203.0.113.9 ")) == "203.0.113.9"


def test_proxy_count_setting_is_validated():
    assert Settings.model_fields["trusted_proxy_count"].default == 0  # sûr par défaut : aucun en-tête n'est cru
    with pytest.raises(ValidationError):
        Settings(trusted_proxy_count=-1)
    with pytest.raises(ValidationError):
        Settings(trusted_proxy_count=11)


# --- limitation des connexions : comportement de bout en bout -------------------------------------------------------


async def test_spoofed_forwarded_for_cannot_bypass_the_limit_without_proxy(monkeypatch, anon):
    trust(monkeypatch, 0)
    codes = [await bad_login(anon, forwarded=f"10.9.{i}.1") for i in range(12)]
    assert codes == [401] * 5 + [429] * 7  # le seuil est atteint malgré 12 valeurs différentes
    assert await bad_login(anon, forwarded="10.9.200.1") == 429


async def test_spoofed_entries_on_the_left_cannot_bypass_the_limit_behind_one_proxy(monkeypatch, anon):
    trust(monkeypatch, 1)
    # nginx ajoute l'adresse réelle à droite ; le client fait varier ce qu'il écrit à gauche
    codes = [await bad_login(anon, forwarded=f"10.9.{i}.1, 203.0.113.9") for i in range(12)]
    assert codes == [401] * 5 + [429] * 7


async def test_distinct_real_clients_do_not_share_a_limit_behind_one_proxy(monkeypatch, anon):
    trust(monkeypatch, 1)
    assert [await bad_login(anon, forwarded="203.0.113.1") for _ in range(6)] == [401] * 5 + [429]
    assert await bad_login(anon, forwarded="203.0.113.2") == 401  # autre client : compteur indépendant
    assert await bad_login(anon, email="viewer@example.com", forwarded="203.0.113.1") == 401  # autre compte


async def test_two_proxies_limit_on_the_client_entry(monkeypatch, anon):
    trust(monkeypatch, 2)
    # le client réel est l'avant-dernière entrée ; le dernier saut peut varier sans changer le compteur
    codes = [await bad_login(anon, forwarded=f"6.6.6.6, 198.51.100.7, 10.0.0.{i}") for i in range(7)]
    assert codes == [401] * 5 + [429] * 2
    assert await bad_login(anon, forwarded="6.6.6.6, 198.51.100.8, 10.0.0.1") == 401


async def test_missing_header_is_limited_on_the_connection_address(monkeypatch, anon):
    trust(monkeypatch, 1)
    assert [await bad_login(anon) for _ in range(7)] == [401] * 5 + [429] * 2


@pytest.mark.parametrize("junk", ["garbage", "999.9.9.9", ",,,", "1.2.3.4:80"])
async def test_malformed_values_all_land_in_the_connection_bucket(monkeypatch, anon, junk):
    trust(monkeypatch, 1)
    codes = [await bad_login(anon, forwarded=f"{junk}{i}" if junk != ",,," else junk) for i in range(8)]
    assert codes == [401] * 5 + [429] * 3


async def test_normal_login_behaviour_is_unchanged(monkeypatch, anon):
    trust(monkeypatch, 1)
    for _ in range(4):
        assert await bad_login(anon, forwarded="203.0.113.5") == 401
    ok = await anon.post(
        f"{API}/auth/login", json={"email": EMAIL, "password": "admin123"}, headers={"X-Forwarded-For": "203.0.113.5"}
    )
    assert ok.status_code == 200
    # une connexion réussie remet le compteur à zéro
    assert [await bad_login(anon, forwarded="203.0.113.5") for _ in range(5)] == [401] * 5


async def test_audit_log_records_the_validated_address(monkeypatch, anon, admin):
    async def last_login_ip(email: str) -> str:
        items = (await admin.get(f"{API}/admin/audit", params={"user": email, "action": "LOGIN_SUCCESS", "size": 1})).json()[
            "items"
        ]
        return items[0]["ip_address"]

    creds = {"email": "viewer@example.com", "password": "viewer123"}
    trust(monkeypatch, 0)
    await anon.post(f"{API}/auth/login", json=creds, headers={"X-Forwarded-For": "6.6.6.6"})
    assert await last_login_ip(creds["email"]) == PEER  # l'en-tête falsifié n'est pas journalisé
    trust(monkeypatch, 1)
    await anon.post(f"{API}/auth/login", json=creds, headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.50"})
    assert await last_login_ip(creds["email"]) == "203.0.113.50"


# --- recherche globale : même politique que GET /users -------------------------------------------------------------


def test_system_permission_helper_matches_the_dependency_policy():
    assert has_system_permission("ADMIN", "admin:users")
    assert not has_system_permission("ADMIN", "permission-inexistante")
    assert not has_system_permission("MANAGER", "admin:users")
    assert not has_system_permission("INCONNU", "admin:users")


@pytest.mark.parametrize("role", ["MANAGER", "VIEWER"])
async def test_search_hides_accounts_from_a_non_admin_role_holding_admin_users(monkeypatch, role, admin):
    from tests.conftest import make_client

    monkeypatch.setitem(ROLE_PERMISSIONS, role, frozenset(ROLE_PERMISSIONS[role] | {"admin:users"}))
    creds = {"MANAGER": ("manager@example.com", "manager123"), "VIEWER": ("viewer@example.com", "viewer123")}[role]
    client = await make_client(*creds)
    try:
        # la permission est bien présente, mais /users la refuse faute du rôle ADMIN
        assert "admin:users" in (await client.get(f"{API}/auth/me")).json()["permissions"]
        assert (await client.get(f"{API}/users")).status_code == 403
        # /search doit suivre la même règle : aucun compte n'est renvoyé, le reste de la recherche fonctionne
        r = await client.get(f"{API}/search", params={"q": "example"})
        assert r.status_code == 200
        assert r.json()["users"] == []
        assert "example.com" not in r.text
        assert set(r.json()) >= {"assets", "contracts", "vendors"}
    finally:
        await client.aclose()


async def test_search_still_returns_accounts_to_a_real_admin(admin):
    r = await admin.get(f"{API}/search", params={"q": "example"})
    assert r.status_code == 200 and len(r.json()["users"]) >= 1

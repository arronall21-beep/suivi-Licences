import smtplib
from datetime import date, timedelta

import pytest
from sqlalchemy import text

from app.core import lifecycle
from app.services import mailer
from tests.conftest import make_client

API = "/api/v1"
SECRET = "S3cr3t-SMTP-pwd!"


def iso(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


GENERAL = {
    "org_name": "SBEE",
    "app_name": "Gestion du Patrimoine SI",
    "currency": "XOF",
    "timezone": "Africa/Porto-Novo",
    "admin_email": "dsi@sbee.bj",
    "critical_days": 30,
    "alert_days": 90,
}


# ---------- Paramètres généraux ----------
async def test_general_defaults_and_public_config(admin, viewer, anon):
    g = (await admin.get(f"{API}/admin/settings/general")).json()
    assert (g["org_name"], g["app_name"], g["currency"], g["currency_label"]) == (
        "SBEE",
        "Gestion du Patrimoine SI",
        "XOF",
        "FCFA",
    )
    assert (g["critical_days"], g["alert_days"]) == (30, 90)
    public = (await anon.get(f"{API}/public/config")).json()
    assert public["org_name"] == "SBEE" and public["version"] == "1.1.0" and "admin_email" not in public
    cfg = (await viewer.get(f"{API}/config")).json()
    assert cfg["currency"] == "XOF" and cfg["alert_thresholds"] == [90, 60, 30, 7]


async def test_general_update_and_permissions(admin, manager, viewer):
    body = {**GENERAL, "org_name": "SBEE Bénin", "currency": "eur"}
    r = await admin.put(f"{API}/admin/settings/general", json=body)
    assert r.status_code == 200 and r.json()["org_name"] == "SBEE Bénin" and r.json()["currency"] == "EUR"
    assert (await admin.get(f"{API}/admin/settings/general")).json()["currency_label"] == "€"
    assert (await viewer.get(f"{API}/config")).json()["org_name"] == "SBEE Bénin"
    for client in (manager, viewer):
        assert (await client.get(f"{API}/admin/settings/general")).status_code == 403
        assert (await client.put(f"{API}/admin/settings/general", json=GENERAL)).status_code == 403


@pytest.mark.parametrize(
    "patch",
    [
        {"critical_days": 90, "alert_days": 90},
        {"critical_days": 0},
        {"timezone": "Mars/Olympus"},
        {"currency": "FRANC"},
        {"org_name": " "},
    ],
)
async def test_general_validation(admin, patch):
    r = await admin.put(f"{API}/admin/settings/general", json={**GENERAL, **patch})
    assert r.status_code == 422


async def test_thresholds_drive_lifecycle(admin):
    await admin.post(f"{API}/assets", json={"category": "LICENCE", "name": "A20", "end_date": iso(20)})
    await admin.post(f"{API}/assets", json={"category": "LICENCE", "name": "A50", "end_date": iso(50)})

    async def statuses():
        items = (await admin.get(f"{API}/assets", params={"size": 50})).json()["items"]
        return {a["name"]: a["status"] for a in items}

    assert await statuses() == {"A20": "CRITIQUE", "A50": "ALERTE"}
    r = await admin.put(f"{API}/admin/settings/general", json={**GENERAL, "critical_days": 10, "alert_days": 40})
    assert r.status_code == 200
    assert (lifecycle.config.critical_days, lifecycle.config.alert_days) == (10, 40)
    assert await statuses() == {"A20": "ALERTE", "A50": "OK"}
    # le filtre SQL par statut suit les mêmes seuils
    only_alert = (await admin.get(f"{API}/assets", params={"status": "ALERTE"})).json()
    assert [a["name"] for a in only_alert["items"]] == ["A20"]
    dash = (await admin.get(f"{API}/dashboard")).json()
    assert dash["deadlines"]["warning"] == 1 and dash["thresholds"] == {"critical_days": 10, "alert_days": 40}


# ---------- Configuration des alertes ----------
async def test_alert_config_roundtrip_and_effect(admin, manager):
    cfg = (await admin.get(f"{API}/admin/settings/alerts")).json()
    assert [(t["days"], t["enabled"]) for t in cfg["thresholds"]] == [(90, True), (60, True), (30, True), (7, True)]
    await admin.post(f"{API}/assets", json={"category": "LICENCE", "name": "L50", "end_date": iso(50)})  # seuil J-60
    await admin.post(f"{API}/assets", json={"category": "LICENCE", "name": "L-expiré", "end_date": iso(-3)})
    assert {a["threshold"] for a in (await admin.get(f"{API}/alerts")).json()["items"]} == {0, 60}

    body = {
        "thresholds": [
            {"days": 90, "enabled": True},
            {"days": 60, "enabled": False},
            {"days": 30, "enabled": True},
            {"days": 7, "enabled": True},
        ],
        "notify_expired": False,
        "recipients": {"notify_owner": True, "notify_admin": False, "custom": ["achats@sbee.bj"]},
    }
    assert (await admin.put(f"{API}/admin/settings/alerts", json=body)).status_code == 200
    saved = (await admin.get(f"{API}/admin/settings/alerts")).json()
    assert saved["notify_expired"] is False and saved["recipients"]["custom"] == ["achats@sbee.bj"]
    alerts = (await admin.get(f"{API}/alerts")).json()
    assert alerts["thresholds"] == [90, 30, 7] and alerts["notify_owner"] is True
    assert {a["threshold"] for a in alerts["items"]} == {90}  # J-60 désactivé → 50 j tombe dans J-90 ; expiré désactivé
    assert (await manager.put(f"{API}/admin/settings/alerts", json=body)).status_code == 403


async def test_alert_config_validation(admin):
    base = {"thresholds": [{"days": 30, "enabled": True}], "notify_expired": True, "recipients": {"custom": []}}
    dup = {**base, "thresholds": [{"days": 30, "enabled": True}, {"days": 30, "enabled": False}]}
    assert (await admin.put(f"{API}/admin/settings/alerts", json=dup)).status_code == 422
    bad = {**base, "recipients": {"custom": ["pas-un-email"]}}
    assert (await admin.put(f"{API}/admin/settings/alerts", json=bad)).status_code == 422


# ---------- SMTP ----------
SMTP_FORM = {
    "host": "smtp.sbee.bj",
    "port": 587,
    "security": "STARTTLS",
    "username": "alertes@sbee.bj",
    "password": SECRET,
    "from_email": "alertes@sbee.bj",
    "from_name": "SBEE — Patrimoine SI",
}


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    fail_login = False

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.calls, self.sent = host, port, [], []
        FakeSMTP.instances.append(self)

    def ehlo(self):
        self.calls.append("ehlo")

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append(("login", user, password))
        if FakeSMTP.fail_login:
            raise smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    def noop(self):
        self.calls.append("noop")

    def send_message(self, msg):
        self.sent.append(msg)

    def quit(self):
        self.calls.append("quit")

    def close(self):
        self.calls.append("close")


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances, FakeSMTP.fail_login = [], False
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(mailer.smtplib, "SMTP_SSL", FakeSMTP)
    return FakeSMTP


async def test_smtp_not_configured_by_default(admin):
    s = (await admin.get(f"{API}/admin/settings/smtp")).json()
    assert s["configured"] is False and s["password_set"] is False and s["source"] == "none"
    r = await admin.post(f"{API}/admin/settings/smtp/test-email", json={})
    assert r.json()["ok"] is False and "non configuré" in r.json()["message"]
    r = await admin.post(f"{API}/admin/settings/smtp/test-connection", json={"host": ""})
    assert r.json()["ok"] is False and "non configuré" in r.json()["message"]


async def test_smtp_password_is_encrypted_and_never_exposed(admin, db):
    r = await admin.put(f"{API}/admin/settings/smtp", json=SMTP_FORM)
    assert r.status_code == 200
    body = r.json()
    assert body["configured"] and body["password_set"] and body["source"] == "database"
    assert "password" not in body and SECRET not in r.text
    assert SECRET not in (await admin.get(f"{API}/admin/settings/smtp")).text

    stored = (await db.execute(text("SELECT value, is_secret FROM app_settings WHERE key = 'smtp_password'"))).one()
    assert stored.is_secret and SECRET not in stored.value and stored.value.startswith("gAAAA")  # jeton Fernet
    dump = (await db.execute(text("SELECT string_agg(coalesce(value, ''), ' ') FROM app_settings"))).scalar()
    assert SECRET not in dump

    # mot de passe omis = conservé ; clear_password = supprimé
    keep = {**SMTP_FORM, "password": None, "host": "smtp2.sbee.bj"}
    assert (await admin.put(f"{API}/admin/settings/smtp", json=keep)).json()["password_set"] is True
    cleared = {**SMTP_FORM, "password": None, "clear_password": True}
    assert (await admin.put(f"{API}/admin/settings/smtp", json=cleared)).json()["password_set"] is False


async def test_smtp_connection_and_email(admin, fake_smtp):
    await admin.put(f"{API}/admin/settings/smtp", json=SMTP_FORM)
    # Test avec mot de passe enregistré (champ vide dans le formulaire)
    r = await admin.post(f"{API}/admin/settings/smtp/test-connection", json={**SMTP_FORM, "password": None})
    assert r.json() == {"ok": True, "message": "Connexion réussie à smtp.sbee.bj:587"}
    smtp = fake_smtp.instances[-1]
    assert "starttls" in smtp.calls and ("login", "alertes@sbee.bj", SECRET) in smtp.calls

    r = await admin.post(f"{API}/admin/settings/smtp/test-email", json={**SMTP_FORM, "password": None, "to": "dest@sbee.bj"})
    assert r.json()["ok"] is True and r.json()["to"] == "dest@sbee.bj"
    msg = fake_smtp.instances[-1].sent[0]
    assert msg["To"] == "dest@sbee.bj" and "alertes@sbee.bj" in msg["From"] and "Email de test" in msg["Subject"]
    # sans destinataire explicite : l'email de l'administrateur connecté
    r = await admin.post(f"{API}/admin/settings/smtp/test-email", json={**SMTP_FORM, "password": None})
    assert r.json()["to"] == "admin@example.com"


async def test_smtp_modes_and_errors(admin, fake_smtp):
    ssl_form = {**SMTP_FORM, "security": "SSL", "port": 465}
    assert (await admin.post(f"{API}/admin/settings/smtp/test-connection", json=ssl_form)).json()["ok"] is True
    assert "starttls" not in fake_smtp.instances[-1].calls
    none_form = {**SMTP_FORM, "security": "NONE", "username": "", "password": None, "port": 25}
    assert (await admin.post(f"{API}/admin/settings/smtp/test-connection", json=none_form)).json()["ok"] is True
    assert not any(isinstance(c, tuple) for c in fake_smtp.instances[-1].calls)  # pas d'authentification

    fake_smtp.fail_login = True
    r = await admin.post(f"{API}/admin/settings/smtp/test-connection", json=SMTP_FORM)
    assert r.json()["ok"] is False and "Authentification refusée" in r.json()["message"]
    assert SECRET not in r.text  # le secret ne fuit jamais dans les erreurs


async def test_smtp_permissions(manager, viewer):
    for client in (manager, viewer):
        assert (await client.get(f"{API}/admin/settings/smtp")).status_code == 403
        assert (await client.put(f"{API}/admin/settings/smtp", json=SMTP_FORM)).status_code == 403
        assert (await client.post(f"{API}/admin/settings/smtp/test-connection", json=SMTP_FORM)).status_code == 403
        assert (await client.post(f"{API}/admin/settings/smtp/test-email", json=SMTP_FORM)).status_code == 403


# ---------- Alertes : envoi et destinataires ----------
async def test_alert_emails_use_ui_config_and_stay_idempotent(admin, fake_smtp):
    await admin.put(f"{API}/admin/settings/smtp", json=SMTP_FORM)
    await admin.put(f"{API}/admin/settings/general", json={**GENERAL, "admin_email": "dsi@sbee.bj"})
    alerts = {
        "thresholds": [{"days": 90, "enabled": True}, {"days": 7, "enabled": True}],
        "notify_expired": True,
        "recipients": {"notify_owner": True, "notify_admin": True, "custom": ["achats@sbee.bj"]},
    }
    await admin.put(f"{API}/admin/settings/alerts", json=alerts)
    await admin.post(
        f"{API}/users",
        json={"first_name": "Awa", "last_name": "Dossou", "email": "awa@sbee.bj", "role": "MANAGER", "password": "Secret123"},
    )
    await admin.post(
        f"{API}/assets", json={"category": "LICENCE", "name": "Logiciel Awa", "end_date": iso(5), "internal_owner": "Awa Dossou"}
    )
    await admin.post(
        f"{API}/assets",
        json={"category": "CERTIFICAT", "name": "cert.sbee.bj", "end_date": iso(60), "internal_owner": "Webmaster"},
    )

    run1 = (await admin.post(f"{API}/alerts/run")).json()
    assert run1["new"] == 2 and run1["delivery_status"] == "ENVOYE"
    assert sorted(run1["recipients"]) == ["achats@sbee.bj", "awa@sbee.bj", "dsi@sbee.bj"] and run1["owners_unresolved"] == 1
    sent = {m["To"]: m.get_content() for i in fake_smtp.instances for m in i.sent}
    assert (
        "Logiciel Awa" in sent["awa@sbee.bj"] and "cert.sbee.bj" not in sent["awa@sbee.bj"]
    )  # le responsable ne reçoit que ses alertes
    assert "Logiciel Awa" in sent["dsi@sbee.bj"] and "cert.sbee.bj" in sent["dsi@sbee.bj"]
    assert "cert.sbee.bj" in sent["achats@sbee.bj"]

    before = sum(len(i.sent) for i in fake_smtp.instances)
    run2 = (await admin.post(f"{API}/alerts/run")).json()
    assert run2["new"] == 0 and sum(len(i.sent) for i in fake_smtp.instances) == before  # aucun doublon


async def test_alert_run_without_smtp_is_recorded_and_notifies_in_app(admin):
    await admin.post(f"{API}/assets", json={"category": "CERTIFICAT", "name": "expired.sbee.bj", "end_date": iso(-2)})
    run = (await admin.post(f"{API}/alerts/run")).json()
    assert run["delivery_status"] == "NON_ENVOYE" and "SMTP non configuré" in run["error"]
    history = (await admin.get(f"{API}/notifications")).json()
    assert len(history) == 1 and history[0]["delivery_status"] == "NON_ENVOYE"
    inbox = (await admin.get(f"{API}/inbox")).json()
    assert inbox["items"][0]["kind"] == "CERTIFICATE_EXPIRED" and inbox["items"][0]["priority"] == "HIGH"
    assert inbox["items"][0]["link"].startswith("/actifs/fiche/")


async def test_secret_never_in_settings_listing(admin, fake_smtp):
    await admin.put(f"{API}/admin/settings/smtp", json=SMTP_FORM)
    for path in ("general", "alerts", "smtp"):
        assert SECRET not in (await admin.get(f"{API}/admin/settings/{path}")).text
    assert SECRET not in (await admin.get(f"{API}/config")).text
    # make_client reste utilisable après tous ces changements de configuration
    assert (await make_client("admin@example.com", "admin123")) is not None

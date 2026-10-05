"""Envoi d'emails SMTP (NONE / STARTTLS / SSL) et tests de connexion. Aucun secret n'est journalisé."""

import logging
import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from starlette.concurrency import run_in_threadpool

log = logging.getLogger(__name__)
TIMEOUT = 10


@dataclass
class SmtpConfig:
    host: str = ""
    port: int = 587
    security: str = "STARTTLS"
    username: str = ""
    password: str = ""
    from_email: str = ""
    from_name: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.host and self.from_email)

    @property
    def sender(self) -> str:
        return formataddr((self.from_name, self.from_email)) if self.from_name else self.from_email


def friendly_error(exc: Exception) -> str:
    """Message d'erreur lisible, sans jamais exposer d'identifiants."""
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Authentification refusée par le serveur (utilisateur ou mot de passe incorrect)"
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "Adresse expéditeur refusée par le serveur"
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "Adresse destinataire refusée par le serveur"
    if isinstance(exc, smtplib.SMTPNotSupportedError):
        return "Fonction non supportée par le serveur (vérifiez le mode de sécurité : STARTTLS / SSL/TLS / aucun)"
    if isinstance(exc, ssl.SSLError):
        return "Erreur TLS/SSL : vérifiez le port et le mode de sécurité"
    if isinstance(exc, socket.gaierror):
        return "Serveur SMTP introuvable (nom d'hôte inconnu)"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return f"Délai dépassé ({TIMEOUT} s) : serveur injoignable ou port filtré"
    if isinstance(exc, ConnectionRefusedError):
        return "Connexion refusée : vérifiez l'hôte et le port"
    if isinstance(exc, smtplib.SMTPServerDisconnected):
        return "Le serveur a fermé la connexion : vérifiez le port et le mode de sécurité"
    if isinstance(exc, smtplib.SMTPException | OSError):
        return f"Erreur SMTP : {type(exc).__name__}"
    return "Erreur inattendue lors de la connexion SMTP"


def _connect(cfg: SmtpConfig) -> smtplib.SMTP:
    if cfg.security == "SSL":
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=TIMEOUT, context=ssl.create_default_context())
    else:
        smtp = smtplib.SMTP(cfg.host, cfg.port, timeout=TIMEOUT)
    try:
        smtp.ehlo()
        if cfg.security == "STARTTLS":
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if cfg.username:
            smtp.login(cfg.username, cfg.password)
    except Exception:
        try:
            smtp.close()
        except Exception:  # noqa: BLE001
            pass
        raise
    return smtp


def test_connection_sync(cfg: SmtpConfig) -> None:
    smtp = _connect(cfg)
    try:
        smtp.noop()
    finally:
        try:
            smtp.quit()
        except Exception:  # noqa: BLE001
            pass


def send_email_sync(cfg: SmtpConfig, recipients: list[str], subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = subject, cfg.sender, ", ".join(recipients)
    msg.set_content(body)
    smtp = _connect(cfg)
    try:
        smtp.send_message(msg)
    finally:
        try:
            smtp.quit()
        except Exception:  # noqa: BLE001
            pass


async def test_connection(cfg: SmtpConfig) -> tuple[bool, str]:
    if not cfg.host:
        return False, "SMTP non configuré : renseignez le serveur"
    try:
        await run_in_threadpool(test_connection_sync, cfg)
        return True, f"Connexion réussie à {cfg.host}:{cfg.port}"
    except Exception as exc:  # noqa: BLE001
        log.warning("Test SMTP échoué : %s", type(exc).__name__)
        return False, friendly_error(exc)


async def send_email(cfg: SmtpConfig, recipients: list[str], subject: str, body: str) -> tuple[bool, str | None]:
    if not cfg.configured:
        return False, "SMTP non configuré"
    try:
        await run_in_threadpool(send_email_sync, cfg, recipients, subject, body)
        return True, None
    except Exception as exc:  # noqa: BLE001
        log.warning("Envoi email échoué : %s", type(exc).__name__)
        return False, friendly_error(exc)

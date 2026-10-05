"""Journal d'audit minimal. Chaque entrée est écrite dans sa propre transaction : elle est conservée
même si l'action métier échoue ou est annulée, et n'enregistre jamais de secret (mots de passe, clés)."""

import json
import logging
from typing import Annotated, Any

from fastapi import Depends, Request

from app.core.http import client_ip
from app.database import SessionLocal
from app.models import AuditLog, User

log = logging.getLogger(__name__)

ACTION_LABELS = {
    "LOGIN_SUCCESS": "Connexion réussie",
    "LOGIN_FAILURE": "Connexion échouée",
    "PASSWORD_CHANGE": "Changement de mot de passe",
    "PASSWORD_RESET_REQUEST": "Demande de réinitialisation",
    "USER_CREATE": "Création utilisateur",
    "USER_UPDATE": "Modification utilisateur",
    "USER_ROLE_CHANGE": "Modification de rôle",
    "USER_DEACTIVATE": "Désactivation utilisateur",
    "USER_REACTIVATE": "Réactivation utilisateur",
    "USER_PASSWORD_RESET": "Réinitialisation mot de passe",
    "SETTINGS_UPDATE": "Modification paramètres",
    "ALERTS_CONFIG_UPDATE": "Modification config. alertes",
    "SMTP_UPDATE": "Modification SMTP",
    "SMTP_TEST_CONNECTION": "Test connexion SMTP",
    "SMTP_TEST_EMAIL": "Email de test SMTP",
    "IMPORT_EXCEL": "Import Excel",
    "EXPORT_EXCEL": "Export Excel",
    "ALERTS_RUN": "Contrôle des alertes",
    "ASSET_CREATE": "Création actif",
    "ASSET_UPDATE": "Modification actif",
    "ASSET_DELETE": "Suppression actif",
    "CONTRACT_CREATE": "Création contrat",
    "CONTRACT_UPDATE": "Modification contrat",
    "CONTRACT_DELETE": "Suppression contrat",
    "VENDOR_CREATE": "Création fournisseur",
    "VENDOR_UPDATE": "Modification fournisseur",
    "VENDOR_DELETE": "Suppression fournisseur",
    "ASSIGNMENT_CREATE": "Affectation licence",
    "ASSIGNMENT_UPDATE": "Modification affectation",
    "ASSIGNMENT_DELETE": "Désaffectation licence",
}


class Auditor:
    def __init__(self, request: Request):
        self.request = request

    async def log(
        self,
        user: User | str | None,
        action: str,
        entity_type: str | None = None,
        entity_id: Any = None,
        label: str | None = None,
        result: str = "SUCCESS",
        details: Any = None,
    ) -> None:
        email = user.email if isinstance(user, User) else user
        if details is not None and not isinstance(details, str):
            details = json.dumps(details, ensure_ascii=False, default=str)
        try:
            async with SessionLocal() as db:
                db.add(
                    AuditLog(
                        user_id=user.id if isinstance(user, User) else None,
                        user_email=email,
                        action=action,
                        entity_type=entity_type,
                        entity_id=None if entity_id is None else str(entity_id),
                        entity_label=(label or "")[:255] or None,
                        result=result,
                        details=details,
                        ip_address=client_ip(self.request),
                    )
                )
                await db.commit()
        except Exception:  # noqa: BLE001 - l'audit ne doit jamais faire échouer l'action
            log.exception("Écriture du journal d'audit impossible (%s)", action)


def get_auditor(request: Request) -> Auditor:
    return Auditor(request)


Audit = Annotated[Auditor, Depends(get_auditor)]


def changed_fields(obj: Any, data: dict, skip: tuple[str, ...] = ()) -> list[str]:
    """Noms des champs dont la valeur va changer (jamais les valeurs elles-mêmes)."""

    def norm(v):
        return float(v) if hasattr(v, "as_tuple") else v

    return [k for k, v in data.items() if k not in skip and norm(getattr(obj, k, None)) != v]

"""Logique centralisée du cycle de vie (jours restants, statut, priorité).

Toute la règle métier d'échéance vit ici : ne pas la dupliquer ailleurs.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

EXPIRE = "EXPIRE"
CRITIQUE = "CRITIQUE"
ALERTE = "ALERTE"
OK = "OK"
INCONNU = "INCONNU"

STATUSES = [EXPIRE, CRITIQUE, ALERTE, OK, INCONNU]

STATUS_LABELS = {
    EXPIRE: "EXPIRÉ",
    CRITIQUE: "CRITIQUE",
    ALERTE: "ALERTE",
    OK: "OK",
    INCONNU: "NON DÉFINI",
}


class LifecycleConfig:
    """Seuils et fuseau, modifiables par l'administrateur (Paramètres généraux).

    Valeurs par défaut : CRITIQUE ≤ 30 j, ALERTE ≤ 90 j. Rechargées au démarrage et à chaque
    enregistrement des paramètres (processus unique).
    """

    critical_days = 30
    alert_days = 90
    timezone = "UTC"


config = LifecycleConfig()

HIGH_CRITICALITIES = {"Critique", "Haute"}


def today() -> date:
    try:
        return datetime.now(ZoneInfo(config.timezone)).date()
    except Exception:  # fuseau invalide : repli sur la date locale du serveur
        return date.today()


def days_remaining(end_date: date | None, ref: date | None = None) -> int | None:
    if end_date is None:
        return None
    return (end_date - (ref or today())).days


def status_from_days(days: int | None) -> str:
    if days is None:
        return INCONNU
    if days <= 0:
        return EXPIRE
    if days <= config.critical_days:
        return CRITIQUE
    if days <= config.alert_days:
        return ALERTE
    return OK


def compute_status(end_date: date | None, ref: date | None = None) -> str:
    return status_from_days(days_remaining(end_date, ref))


def status_date_range(status: str, ref: date | None = None) -> tuple[date | None, date | None]:
    """Intervalle [min, max] de end_date correspondant à un statut (pour filtrer en SQL)."""
    t = ref or today()
    if status == EXPIRE:
        return None, t
    if status == CRITIQUE:
        return t + timedelta(days=1), t + timedelta(days=config.critical_days)
    if status == ALERTE:
        return t + timedelta(days=config.critical_days + 1), t + timedelta(days=config.alert_days)
    if status == OK:
        return t + timedelta(days=config.alert_days + 1), None
    raise ValueError(status)


def priority(status: str, criticality: str | None = None) -> str:
    high = criticality in HIGH_CRITICALITIES
    if status in (EXPIRE, CRITIQUE):
        return "P1"
    if status == ALERTE:
        return "P1" if high else "P2"
    if status == OK:
        return "P3"
    return "P3"


def renewal_start_date(end_date: date | None, notice_period_days: int | None) -> date | None:
    if end_date is None:
        return None
    return end_date - timedelta(days=notice_period_days or 0)

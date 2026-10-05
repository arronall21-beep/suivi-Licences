from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

Security = Literal["NONE", "STARTTLS", "SSL"]

CURRENCY_LABELS = {"XOF": "FCFA", "XAF": "FCFA", "EUR": "€", "USD": "$", "GBP": "£"}


def currency_label(code: str) -> str:
    return CURRENCY_LABELS.get(code.upper(), code.upper())


class GeneralSettings(BaseModel):
    org_name: str = Field(min_length=1, max_length=120)
    app_name: str = Field(min_length=1, max_length=120)
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")
    timezone: str = Field(min_length=1, max_length=64)
    admin_email: EmailStr | None = None
    critical_days: int = Field(ge=1, le=3650)
    alert_days: int = Field(ge=1, le=3650)

    @field_validator("org_name", "app_name", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("currency")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            raise ValueError("Fuseau horaire inconnu (ex. Africa/Porto-Novo)") from None
        return v

    @model_validator(mode="after")
    def _order(self):
        if self.critical_days >= self.alert_days:
            raise ValueError("Le seuil critique doit être strictement inférieur au seuil d'alerte")
        return self


class ThresholdIn(BaseModel):
    days: int = Field(ge=1, le=365)
    enabled: bool = True


class AlertRecipients(BaseModel):
    notify_owner: bool = False
    notify_admin: bool = True
    custom: list[EmailStr] = Field(default_factory=list, max_length=20)


class AlertSettings(BaseModel):
    thresholds: list[ThresholdIn] = Field(max_length=10)
    notify_expired: bool = True
    recipients: AlertRecipients

    @field_validator("thresholds")
    @classmethod
    def _unique(cls, v: list[ThresholdIn]) -> list[ThresholdIn]:
        days = [t.days for t in v]
        if len(set(days)) != len(days):
            raise ValueError("Seuils en double")
        return sorted(v, key=lambda t: -t.days)


class SmtpIn(BaseModel):
    host: str = Field(default="", max_length=255)
    port: int = Field(default=587, ge=1, le=65535)
    security: Security = "STARTTLS"
    username: str = Field(default="", max_length=255)
    # None = conserver le mot de passe enregistré ; chaîne non vide = le remplacer
    password: str | None = Field(default=None, max_length=500)
    clear_password: bool = False
    from_email: EmailStr | None = None
    from_name: str = Field(default="", max_length=120)

    @field_validator("host", "username", "from_name", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v


class SmtpTestEmail(SmtpIn):
    to: EmailStr | None = None

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Suivi Licences SI"
    environment: str = "development"

    database_url: str = "postgresql+asyncpg://suivi:suivi@localhost:5432/suivi_licences"

    secret_key: str = "change-me-in-env"
    access_token_expire_minutes: int = 60 * 8
    jwt_algorithm: str = "HS256"

    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"
    manager_email: str = "manager@example.com"
    manager_password: str = "manager123"
    viewer_email: str = "viewer@example.com"
    viewer_password: str = "viewer123"

    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    max_upload_mb: int = 10

    # Valeurs par défaut des paramètres généraux (modifiables ensuite dans Administration → Paramètres)
    organization_name: str = "SBEE"
    application_name: str = "Gestion du Patrimoine SI"
    currency: str = "XOF"
    default_timezone: str = "Africa/Porto-Novo"
    critical_days: int = 30
    alert_days: int = 90

    # Chiffrement des secrets stockés en base (mot de passe SMTP). Par défaut dérivée de SECRET_KEY.
    settings_encryption_key: str = ""
    # Répertoire où sont déposées les sauvegardes de la base (lecture seule, pour l'affichage du dernier backup)
    backup_dir: str = "/backups"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    smtp_security: str = ""  # NONE | STARTTLS | SSL ; vide = déduit de SMTP_USE_TLS
    alert_recipients: str = ""
    alert_thresholds: str = "90,60,30,7"

    scheduler_enabled: bool = True
    alert_hour: int = 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def alert_recipient_list(self) -> list[str]:
        return [r.strip() for r in self.alert_recipients.split(",") if r.strip()]

    @property
    def alert_threshold_list(self) -> list[int]:
        return sorted({int(t) for t in self.alert_thresholds.split(",") if t.strip()}, reverse=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

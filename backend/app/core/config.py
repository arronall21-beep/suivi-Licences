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

    # Devise des montants (code ISO + libellé affiché dans l'export Excel)
    currency: str = "XOF"
    currency_label: str = "FCFA"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
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

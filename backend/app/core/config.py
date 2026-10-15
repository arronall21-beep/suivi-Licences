from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Environnements où la documentation interactive de l'API peut être servie (tout autre nom, dont « production », la désactive)
DOCS_ENVIRONMENTS = frozenset({"development", "dev", "local", "test", "testing"})


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

    # Nombre de reverse proxies de confiance placés devant l'application (nginx = 1). 0 : aucun en-tête de transfert
    # n'est cru et l'adresse du client est celle de la connexion. Ne jamais dépasser le nombre réel de proxies : un client
    # peut écrire n'importe quoi dans X-Forwarded-For, seules les entrées ajoutées par ses propres proxies sont fiables.
    trusted_proxy_count: int = Field(default=0, ge=0, le=10)

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
    def api_docs_enabled(self) -> bool:
        """Documentation interactive (Swagger, ReDoc, schéma OpenAPI) : jamais hors des environnements de développement/test."""
        return self.environment.strip().lower() in DOCS_ENVIRONMENTS

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

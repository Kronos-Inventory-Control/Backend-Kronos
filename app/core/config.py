from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación, leída desde el archivo .env."""

    app_name: str = "Kronos Inventory Control API"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str

    # --- CORS ---
    # Orígenes (frontends) autorizados a llamar a la API, separados por coma.
    # En el .env se escribe: CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Autenticación (JWT) ---
    # En el .env se escriben en mayúsculas: JWT_SECRET_KEY, JWT_ALGORITHM, etc.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120  # vencimiento absoluto del token
    session_inactivity_minutes: int = 30  # inactividad máxima de la sesión

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Lista limpia de orígenes permitidos (sin espacios ni barra final)."""
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

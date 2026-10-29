"""Configuración centralizada con Pydantic Settings v2."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ERPmini - Planta Industrial de Soplado e Inyección"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/erpmini"

    # Seguridad
    SECRET_KEY: str = "industrial-secret-key-erpmini-change-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_scheme(cls, v: str) -> str:
        """Convierte automáticamente postgres:// o postgresql:// de Railway/Easypanel a postgresql+asyncpg://."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()

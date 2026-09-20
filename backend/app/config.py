from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    migrations_database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15

    cors_origins: str = ""

    # Deployment is cross-origin: frontend on Vercel/Netlify, backend on
    # Render/Railway. That requires SameSite=None + Secure cookies, which in
    # turn require HTTPS. "local" opts into a relaxed dev-only cookie mode
    # (SameSite=Lax, no Secure) so login works over plain http://localhost.
    # Defaults to "production" so a deploy that forgets to set ENVIRONMENT
    # gets the strict/safe behavior, not a silent downgrade.
    environment: Literal["local", "production"] = "production"

    @property
    def is_local(self) -> bool:
        return self.environment == "local"

    @property
    def cookie_samesite(self) -> str:
        return "lax" if self.is_local else "none"

    @property
    def cookie_secure(self) -> bool:
        return not self.is_local

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must be an explicit allowlist — wildcard is never allowed.")
        return origins


settings = Settings()

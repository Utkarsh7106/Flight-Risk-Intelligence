from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    migrations_database_url: str | None = None

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30

    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        if "*" in origins:
            raise ValueError("CORS_ORIGINS must be an explicit allowlist — wildcard is never allowed.")
        return origins


settings = Settings()

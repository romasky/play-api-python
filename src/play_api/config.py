"""Runtime configuration — pydantic-settings reads `.env` and the process environment
(environment variables win, exactly like dotenv + process.env in the JS port)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "https://www.play-qa.com"
    # One deadline for connect + read, in SECONDS (httpx convention). No separate connect timeout on purpose.
    request_timeout: float = 20.0
    # Published on purpose in the play-qa.com UI (RolePermissionMatrix); overridable for other deployments.
    admin_seed_code: str = "play-qa-admin"


settings = Settings()

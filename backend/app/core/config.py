"""Centralized settings. All configuration enters through this module.

Server-only values are SecretStr: they never appear in repr/str/logs and must
be read explicitly with .get_secret_value() at the call site (docs/auth.md #5,
OWASP A02). Public config (app_env, supabase_url, anon key, CORS origins) is
safe to surface.
"""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Public config ---
    app_env: str = "development"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # Comma-separated explicit origins — never "*" (credentials + wildcard is
    # invalid CORS anyway, and wildcard is forbidden by the milestone spec).
    cors_origins: str = "http://localhost:3000"

    # --- SERVER-ONLY secrets ---
    supabase_service_role_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()

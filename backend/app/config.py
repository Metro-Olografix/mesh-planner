from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://meshplanner:meshplanner@db:5432/meshplanner"
    oidc_issuer: str = ""             # e.g. https://auth.example.com (no trailing slash)
    oidc_client_id: str = ""          # your OIDC application client ID
    oidc_audience: str = ""           # optional: enforce aud claim (Auth0, Okta, Keycloak)
    public_access: bool = False       # allow unauthenticated read-only access
    custom_assets_dir: str = "/app/custom"  # mount custom logo/favicon here
    splat_path: str = "/app"
    tile_cache_dir: str = "/app/.splat_tiles"
    tile_cache_gb: float = 2.0
    log_level: str = "INFO"           # DEBUG | INFO | WARNING | ERROR

    class Config:
        env_file = ".env"


settings = Settings()

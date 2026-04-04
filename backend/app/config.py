from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://meshplanner:meshplanner@db:5432/meshplanner"
    zitadel_domain: str = ""          # e.g. https://auth.olografix.org
    zitadel_client_id: str = ""       # your Zitadel application client ID
    splat_path: str = "/app"
    tile_cache_dir: str = "/app/.splat_tiles"
    tile_cache_gb: float = 2.0
    log_level: str = "INFO"           # DEBUG | INFO | WARNING | ERROR

    class Config:
        env_file = ".env"


settings = Settings()

import logging
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import AsyncSessionLocal, Base, engine
from app.services.hardware_seed import seed_hardware
from app.api import coverage, events, hardware, nodes, pathfinder
import app.models  # noqa: F401 — registers models with Base.metadata

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting up — creating tables and seeding hardware profiles..."
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Lightweight migrations: add columns introduced after initial deploy
        await conn.execute(text(
            "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS "
            "sim_radius_km FLOAT NOT NULL DEFAULT 10.0"
        ))
        await conn.execute(text(
            "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS "
            "environment VARCHAR NOT NULL DEFAULT 'auto'"
        ))
        await conn.execute(text(
            "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS "
            "lora_preset VARCHAR NOT NULL DEFAULT 'MEDIUM_FAST'"
        ))
        # Add 'draft' value to the nodestatus enum if it's a native PG enum
        await conn.execute(text(
            "DO $$ BEGIN "
            "  ALTER TYPE nodestatus ADD VALUE IF NOT EXISTS 'draft'; "
            "EXCEPTION WHEN undefined_object THEN NULL; "
            "END $$"
        ))
    async with AsyncSessionLocal() as db:
        await seed_hardware(db)
    logger.info("Ready.")
    yield
    await engine.dispose()


app = FastAPI(
    title="Mesh Planner API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)
app.include_router(hardware.router)
app.include_router(coverage.router)
app.include_router(pathfinder.router)
app.include_router(events.router)


def _find_custom_asset(name: str) -> Path | None:
    """Return the path of the first matching custom asset file, or None."""
    base = Path(settings.custom_assets_dir)
    for ext in ("", ".png", ".svg", ".webp", ".jpg", ".jpeg", ".ico", ".gif"):
        p = base / f"{name}{ext}"
        if p.is_file():
            return p
    return None


@app.get("/api/config", include_in_schema=False)
async def get_config():
    """Public endpoint — returns frontend auth config from backend env vars."""
    return JSONResponse(
        content={
            "oidcAuthority": settings.oidc_issuer,
            "oidcClientId": settings.oidc_client_id,
            "publicAccess": settings.public_access,
            "customLogo": _find_custom_asset("logo") is not None,
            "customFavicon": _find_custom_asset("favicon") is not None,
        },
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/custom/logo", include_in_schema=False)
async def custom_logo():
    """Serve a custom logo from the custom assets directory."""
    path = _find_custom_asset("logo")
    if not path:
        raise HTTPException(status_code=404, detail="No custom logo configured")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/custom/favicon", include_in_schema=False)
async def custom_favicon():
    """Serve a custom favicon from the custom assets directory."""
    path = _find_custom_asset("favicon")
    if not path:
        raise HTTPException(status_code=404, detail="No custom favicon configured")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

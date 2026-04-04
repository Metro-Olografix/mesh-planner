import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/api/config", include_in_schema=False)
async def get_config():
    """Public endpoint — returns frontend auth config from backend env vars."""
    return {
        "zitadelAuthority": settings.zitadel_domain,
        "zitadelClientId": settings.zitadel_client_id,
    }

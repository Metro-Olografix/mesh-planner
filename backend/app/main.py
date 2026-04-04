import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
    title="Metro Olografix Mesh Planner",
    description=(
        "Collaborative Meshtastic node deployment planner"
        " for Metro Olografix"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten to your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nodes.router)
app.include_router(hardware.router)
app.include_router(coverage.router)
app.include_router(pathfinder.router)
app.include_router(events.router)

# Serve static assets (JS, CSS, images) from the built frontend
app.mount(
    "/assets",
    StaticFiles(directory="app/ui/assets"),
    name="assets",
)


# SPA catch-all: any path not matched by the API or /assets returns
# index.html so that Vue Router can handle client-side navigation.
@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str) -> FileResponse:
    return FileResponse("app/ui/index.html")

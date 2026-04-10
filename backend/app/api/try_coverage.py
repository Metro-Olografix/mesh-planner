"""
Public coverage simulation endpoint for unauthenticated users.
No auth, no persistence — GeoTIFF is returned directly in the response.
"""

import asyncio
import io
import logging
import threading
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.database import get_db
from app.models.hardware_profile import HardwareProfile
from app.models.coverage_request import CoveragePredictionRequest
from app.services.clutter import resolve_clutter_height
from app.services.pathfinder import COVERAGE_DYNAMIC_RANGE_DB
from app.services.splat import Splat

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/try", tags=["try"])

_splat = Splat(
    splat_path=settings.splat_path,
    cache_dir=settings.tile_cache_dir,
    cache_size_gb=settings.tile_cache_gb,
)

# ── Concurrency guard ────────────────────────────────────────────────────────
# Limits simultaneous SPLAT! processes spawned by this endpoint.
# NOTE: in-process only — does not coordinate across multiple workers/replicas.
_semaphore = asyncio.Semaphore(settings.try_max_concurrent)

# ── Rate limiter (in-memory sliding window by client IP) ─────────────────────
# Sufficient for a single-process deployment. If you run multiple uvicorn
# workers or replicas, replace this with a shared Redis counter.
_rate_lock = threading.Lock()
_rate_buckets: dict[str, list[float]] = {}


def _check_rate_limit(ip: str) -> None:
    now = time.monotonic()
    cutoff = now - 3600.0
    with _rate_lock:
        timestamps = [t for t in _rate_buckets.get(ip, []) if t > cutoff]
        if len(timestamps) >= settings.try_rate_limit_per_hour:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit reached. You can run up to "
                    f"{settings.try_rate_limit_per_hour} simulations per hour."
                ),
                headers={"Retry-After": "3600"},
            )
        timestamps.append(now)
        _rate_buckets[ip] = timestamps


# ── Request model ────────────────────────────────────────────────────────────
class TrySimulationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    hardware_id: str
    height_m: float = Field(default=3.0, ge=1.0, le=30.0)
    environment: Literal["auto", "urban", "suburban", "rural", "open"] = "auto"
    lora_preset: Literal[
        "SHORT_FAST",
        "SHORT_SLOW",
        "MEDIUM_FAST",
        "MEDIUM_SLOW",
        "LONG_FAST",
        "LONG_SLOW",
        "VERY_LONG_SLOW",
    ] = "MEDIUM_FAST"


# ── Endpoint ─────────────────────────────────────────────────────────────────
@router.post("/simulate")
async def try_simulate(
    body: TrySimulationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Run a constrained SPLAT! RF propagation simulation and return the
    GeoTIFF directly. No authentication or persistence required.
    Radius is capped at try_max_radius_km (default 3 km).
    """
    # Honour X-Forwarded-For from a reverse proxy
    forwarded = request.headers.get("X-Forwarded-For")
    client_ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )
    _check_rate_limit(client_ip)

    result = await db.execute(
        select(HardwareProfile).where(HardwareProfile.id == body.hardware_id)
    )
    hw = result.scalar_one_or_none()
    if not hw:
        raise HTTPException(404, f"Hardware profile '{body.hardware_id}' not found")

    clutter_m = resolve_clutter_height(body.environment, body.lat, body.lon)
    logger.info(
        "Try simulate: ip=%s hw=%s env=%s preset=%s → clutter=%.1fm",
        client_ip,
        body.hardware_id,
        body.environment,
        body.lora_preset,
        clutter_m,
    )

    req = CoveragePredictionRequest(
        lat=body.lat,
        lon=body.lon,
        tx_height=max(body.height_m, 1.0),
        tx_power=hw.tx_power_dbm,
        tx_gain=hw.default_antenna_gain_dbi,
        frequency_mhz=hw.frequency_mhz,
        rx_height=1.5,
        rx_gain=2.0,
        signal_threshold=hw.rx_sensitivity_dbm,
        clutter_height=clutter_m,
        radius=settings.try_max_radius_km * 1000,
        colormap="plasma",
        min_dbm=hw.rx_sensitivity_dbm,
        max_dbm=hw.rx_sensitivity_dbm + COVERAGE_DYNAMIC_RANGE_DB,
        high_resolution=False,
    )

    async with _semaphore:
        loop = asyncio.get_running_loop()
        try:
            geotiff = await loop.run_in_executor(None, _splat.coverage_prediction, req)
        except Exception as exc:
            logger.error("Try simulation failed for ip=%s: %s", client_ip, exc)
            raise HTTPException(500, "Simulation failed. Please try again.")

    return StreamingResponse(
        io.BytesIO(geotiff),
        media_type="image/tiff",
        headers={"Content-Disposition": "attachment; filename=coverage.tif"},
    )

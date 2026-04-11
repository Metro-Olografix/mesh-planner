"""
Coverage API: trigger SPLAT! simulations per node and serve the resulting GeoTIFF.
"""

import asyncio
import io
import logging
import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.auth import get_current_user
from app.config import settings
from app.database import get_db, AsyncSessionLocal
from app.models.coverage_cache import CoverageCache
from app.models.node import Node
from app.models.coverage_request import CoveragePredictionRequest
from app.services.clutter import resolve_clutter_height
from app.services.pathfinder import COVERAGE_DYNAMIC_RANGE_DB
from app.services.splat import Splat
from app.services.sse import sse_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/coverage", tags=["coverage"])

_splat = Splat(
    splat_path=settings.splat_path,
    cache_dir=settings.tile_cache_dir,
    cache_size_gb=settings.tile_cache_gb,
)


async def _get_node_with_coverage(db: AsyncSession, node_id: UUID) -> Node:
    result = await db.execute(
        select(Node)
        .where(Node.id == node_id)
        .options(selectinload(Node.hardware), selectinload(Node.coverage))
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(404, "Node not found")
    return node


async def _run_splat(node_id: UUID) -> None:
    """Background task: run SPLAT! and persist GeoTIFF to the coverage_cache table."""
    async with AsyncSessionLocal() as db:
        node = await _get_node_with_coverage(db, node_id)
        hw = node.hardware
        gain = (
            node.antenna_gain_dbi
            if node.antenna_gain_dbi is not None
            else hw.default_antenna_gain_dbi
        )

        environment = getattr(node, "environment", "auto") or "auto"
        clutter_m = resolve_clutter_height(environment, node.lat, node.lon)
        logger.info(
            "Node %s: environment=%s → clutter_height=%.1f m",
            node.name,
            environment,
            clutter_m,
        )

        high_res = getattr(node, "high_resolution", True)
        req = CoveragePredictionRequest(
            lat=node.lat,
            lon=node.lon,
            tx_height=node.height_m,
            tx_power=hw.tx_power_dbm,
            tx_gain=gain,
            frequency_mhz=hw.frequency_mhz,
            rx_height=1.5,
            rx_gain=2.0,
            signal_threshold=hw.rx_sensitivity_dbm,
            clutter_height=clutter_m,
            radius=(node.sim_radius_km or 10.0) * 1000,
            colormap="plasma",
            min_dbm=hw.rx_sensitivity_dbm,
            max_dbm=hw.rx_sensitivity_dbm + COVERAGE_DYNAMIC_RANGE_DB,
            high_resolution=high_res,
        )

        cache = node.coverage
        if cache is None:
            cache = CoverageCache(id=uuid.uuid4(), node_id=node_id)
            db.add(cache)

        cache.status = "processing"
        await db.commit()

        try:
            # Run the blocking SPLAT! subprocess in a thread pool so the
            # async event loop stays responsive during the computation.
            loop = asyncio.get_running_loop()
            geotiff = await loop.run_in_executor(None, _splat.coverage_prediction, req)
            cache.geotiff = geotiff
            cache.status = "completed"
            cache.computed_at = datetime.utcnow()
            cache.invalidated = False
            logger.info("Coverage computed for node %s", node_id)
        except Exception as exc:
            cache.status = "failed"
            logger.error("SPLAT! failed for node %s: %s", node_id, exc)

        await db.commit()
        await sse_manager.broadcast(
            "coverage_updated",
            {
                "id": str(node_id),
                "name": node.name,
                "status": cache.status,
            },
        )


@router.post("/{node_id}/invalidate", status_code=200)
async def invalidate_coverage(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Mark the coverage cache as invalidated, forcing a recompute on next request."""
    node = await _get_node_with_coverage(db, node_id)
    if node.coverage:
        node.coverage.invalidated = True
        await db.commit()
        logger.info("Coverage invalidated for node %s by user", node_id)
    else:
        logger.info(
            "Invalidate requested for node %s but no coverage cache exists", node_id
        )
    return {"status": "invalidated", "node_id": str(node_id)}


@router.post("/{node_id}/invalidate_and_recompute", status_code=202)
async def invalidate_and_recompute(
    node_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Invalidate existing coverage and immediately enqueue a fresh SPLAT! computation."""
    node = await _get_node_with_coverage(db, node_id)
    if node.coverage:
        node.coverage.invalidated = True
        await db.commit()
        logger.info("Coverage invalidated and recompute enqueued for node %s", node_id)
    background_tasks.add_task(_run_splat, node_id)
    return {"status": "queued", "node_id": str(node_id)}


@router.post("/{node_id}/compute", status_code=202)
async def trigger_coverage(
    node_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Enqueue a SPLAT! coverage computation for a node."""
    await _get_node_with_coverage(db, node_id)  # 404 if not found
    background_tasks.add_task(_run_splat, node_id)
    return {"status": "queued", "node_id": str(node_id)}


@router.get("/{node_id}/status")
async def coverage_status(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    node = await _get_node_with_coverage(db, node_id)
    if not node.coverage:
        return {"status": "none"}
    return {
        "status": node.coverage.status,
        "invalidated": node.coverage.invalidated,
        "computed_at": node.coverage.computed_at,
    }


@router.get("/{node_id}/geotiff")
async def get_geotiff(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Stream the GeoTIFF coverage raster for a node."""
    node = await _get_node_with_coverage(db, node_id)
    if not node.coverage or not node.coverage.geotiff:
        raise HTTPException(404, "Coverage data not available — trigger /compute first")
    return StreamingResponse(
        io.BytesIO(node.coverage.geotiff),
        media_type="image/tiff",
        headers={"Content-Disposition": f"attachment; filename={node_id}.tif"},
    )


@router.post("/recompute_all", status_code=202)
async def recompute_all_coverage(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Invalidate and recompute coverage for ALL nodes."""
    result = await db.execute(select(Node).options(selectinload(Node.coverage)))
    nodes = result.scalars().all()
    count = 0
    for n in nodes:
        if n.coverage:
            n.coverage.invalidated = True
        background_tasks.add_task(_run_splat, n.id)
        count += 1
    await db.commit()
    logger.info("Recompute-all triggered for %d nodes", count)
    return {"status": "queued", "nodes_queued": count}

from datetime import datetime
from uuid import UUID

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, get_display_name, get_optional_user
from app.database import get_db
from app.models.node import Node
from app.models.node_event import NodeEvent
from app.schemas.node import NodeCreate, NodeOut, NodePublicOut, NodeUpdate
from app.services.sse import sse_manager
from app.utils.privacy import fuzz_coords

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nodes", tags=["nodes"])

# Fields that invalidate the coverage cache when changed
_RF_FIELDS = {"lat", "lon", "height_m", "hardware_id", "antenna_gain_dbi", "sim_radius_km", "environment", "lora_preset", "high_resolution"}



async def _load_node(db: AsyncSession, node_id: UUID) -> Node:
    result = await db.execute(
        select(Node)
        .where(Node.id == node_id)
        .options(selectinload(Node.hardware), selectinload(Node.coverage))
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def _serialize(node: Node) -> NodeOut:
    cov_status: str | None = None
    if node.coverage:
        cov_status = "invalidated" if node.coverage.invalidated else node.coverage.status
    return NodeOut.model_validate({**node.__dict__, "coverage_status": cov_status})


def _serialize_public(node: Node) -> NodePublicOut:
    cov_status: str | None = None
    if node.coverage:
        cov_status = "invalidated" if node.coverage.invalidated else node.coverage.status
    fuzzed_lat, fuzzed_lon = fuzz_coords(node.lat, node.lon, str(node.id))
    return NodePublicOut.model_validate(
        {**node.__dict__, "lat": fuzzed_lat, "lon": fuzzed_lon, "coverage_status": cov_status}
    )


@router.get("/")
async def list_nodes(
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    result = await db.execute(
        select(Node)
        .options(selectinload(Node.hardware), selectinload(Node.coverage))
        .order_by(Node.created_at.desc())
    )
    nodes = result.scalars().all()
    if user is None:
        # Public mode: no drafts, fuzz coords, strip sensitive fields
        public_nodes = [n for n in nodes if n.status != "draft"]
        logger.info("Listed %d nodes (public/unauthenticated)", len(public_nodes))
        return [_serialize_public(n) for n in public_nodes]
    user_sub = user["sub"]
    visible = [
        n for n in nodes
        if n.status != "draft" or n.created_by == user_sub
    ]
    logger.info(
        "Listed %d nodes (%d visible to %s)", len(nodes), len(visible), user_sub
    )
    return [_serialize(n) for n in visible]


@router.post("/", response_model=NodeOut, status_code=201)
async def create_node(
    payload: NodeCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    by = await get_display_name(user["_access_token"], user)
    logger.info("Creating node '%s' by %s", payload.name, by)
    node = Node(**payload.model_dump(), created_by=user["sub"])
    db.add(node)
    db.add(NodeEvent(event_type="node_created", node_id=str(node.id), node_name=payload.name, by=by))
    await db.commit()
    node = await _load_node(db, node.id)
    logger.info("Node created: id=%s name='%s' by=%s", node.id, node.name, by)
    await sse_manager.broadcast("node_created", {"id": str(node.id), "name": node.name, "by": by})
    return _serialize(node)


@router.get("/{node_id}")
async def get_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    logger.debug("Fetching node %s", node_id)
    node = await _load_node(db, node_id)
    if user is None:
        if node.status == "draft":
            raise HTTPException(status_code=404, detail="Node not found")
        return _serialize_public(node)
    return _serialize(node)


@router.patch("/{node_id}", response_model=NodeOut)
async def update_node(
    node_id: UUID,
    payload: NodeUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    node = await _load_node(db, node_id)
    update_data = payload.model_dump(exclude_none=True)
    by = await get_display_name(user["_access_token"], user)
    logger.info("Updating node %s ('%s') by %s — fields: %s", node_id, node.name, by, list(update_data.keys()))

    for key, value in update_data.items():
        setattr(node, key, value)
    node.updated_at = datetime.utcnow()

    # Invalidate coverage if RF-relevant params changed
    if update_data.keys() & _RF_FIELDS and node.coverage:
        logger.info("RF-relevant fields changed for node %s — invalidating coverage cache", node_id)
        node.coverage.invalidated = True

    db.add(NodeEvent(event_type="node_updated", node_id=str(node_id), node_name=node.name, by=by))
    await db.commit()
    node = await _load_node(db, node_id)
    await sse_manager.broadcast("node_updated", {"id": str(node.id), "name": node.name, "by": by})
    return _serialize(node)


@router.delete("/{node_id}", status_code=204)
async def delete_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    node = await _load_node(db, node_id)
    name = node.name
    by = await get_display_name(user["_access_token"], user)
    logger.info("Deleting node %s ('%s') by %s", node_id, name, by)
    db.add(NodeEvent(event_type="node_deleted", node_id=str(node_id), node_name=name, by=by))
    await db.delete(node)
    await db.commit()
    logger.info("Node deleted: id=%s name='%s'", node_id, name)
    await sse_manager.broadcast("node_deleted", {"id": str(node_id), "name": name, "by": by})

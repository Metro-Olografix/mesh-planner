import logging

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models.node import Node
from app.schemas.path import HopInfo, PathRequest, PathResult
from app.services.pathfinder import (
    GraphNode,
    build_snr_matrix,
    find_max_min_snr_path,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/path", tags=["pathfinder"])


@router.post("/find", response_model=PathResult)
async def find_path(
    req: PathRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Load all nodes regardless of status so planned nodes can also be used in simulations
    result = await db.execute(
        select(Node).options(selectinload(Node.hardware), selectinload(Node.coverage))
    )
    nodes = result.scalars().all()

    # Filter out nodes with excluded statuses, but always keep source & destination
    if req.exclude_statuses:
        excluded = set(req.exclude_statuses)
        nodes = [
            n
            for n in nodes
            if n.status.value not in excluded
            or n.id == req.source_node_id
            or n.id == req.destination_node_id
        ]

    src_node = next((n for n in nodes if n.id == req.source_node_id), None)
    dst_node = next((n for n in nodes if n.id == req.destination_node_id), None)

    if not src_node:
        return PathResult(
            found=False,
            hops=[],
            bottleneck_snr_db=None,
            total_relay_hops=0,
            message="Source node not found",
        )
    if not dst_node:
        return PathResult(
            found=False,
            hops=[],
            bottleneck_snr_db=None,
            total_relay_hops=0,
            message="Destination node not found",
        )
    if src_node.id == dst_node.id:
        return PathResult(
            found=False,
            hops=[],
            bottleneck_snr_db=None,
            total_relay_hops=0,
            message="Source and destination must be different nodes",
        )

    # Auto-trigger SPLAT! coverage for nodes that lack it
    from app.api.coverage import _run_splat

    nodes_missing = [
        n
        for n in nodes
        if not (n.coverage and n.coverage.geotiff and not n.coverage.invalidated)
        and not (n.coverage and n.coverage.status == "processing")
    ]
    if nodes_missing:
        for n in nodes_missing:
            background_tasks.add_task(_run_splat, n.id)
        missing_names = ", ".join(n.name for n in nodes_missing)
        logger.info("Auto-triggered coverage for: %s", missing_names)
        return PathResult(
            found=False,
            hops=[],
            bottleneck_snr_db=None,
            total_relay_hops=0,
            message=f"Coverage computation triggered for: {missing_names}. Please retry in 1-2 minutes.",
        )

    # Build graph: every node is a real graph node with its own RF parameters
    graph: list[GraphNode] = []
    node_idx: dict[str, int] = {}
    for i, n in enumerate(nodes):
        hw = n.hardware
        gain = (
            n.antenna_gain_dbi
            if n.antenna_gain_dbi is not None
            else hw.default_antenna_gain_dbi
        )
        graph.append(
            GraphNode(
                idx=i,
                node_id=n.id,
                name=n.name,
                lat=n.lat,
                lon=n.lon,
                tx_dbm=hw.tx_power_dbm,
                tx_gain_dbi=gain,
                rx_gain_dbi=gain,
                rx_sensitivity_dbm=hw.rx_sensitivity_dbm,
                freq_mhz=hw.frequency_mhz,
                lora_preset=getattr(n, "lora_preset", "MEDIUM_FAST") or "MEDIUM_FAST",
            )
        )
        node_idx[str(n.id)] = i

    src_idx = node_idx[str(req.source_node_id)]
    dst_idx = node_idx[str(req.destination_node_id)]

    coverage_data = {
        str(n.id): n.coverage.geotiff
        for n in nodes
        if n.coverage and n.coverage.geotiff and not n.coverage.invalidated
    }

    # Nodes whose coverage is still being computed — path uses Friis fallback
    # for these, so results may be suboptimal.
    nodes_processing = [
        n
        for n in nodes
        if n.coverage
        and n.coverage.status == "processing"
        and not (n.coverage.geotiff and not n.coverage.invalidated)
    ]

    logger.info(
        "Path request: %s → %s (%d nodes in graph)",
        src_node.name,
        dst_node.name,
        len(graph),
    )
    matrix = build_snr_matrix(graph, coverage_data)
    path_indices, bottleneck = find_max_min_snr_path(
        graph, matrix, src_idx=src_idx, dst_idx=dst_idx
    )

    processing_warning = ""
    if nodes_processing:
        processing_names = ", ".join(n.name for n in nodes_processing)
        processing_warning = (
            f" (coverage still computing for: {processing_names}"
            " — results may change once complete)"
        )

    if path_indices is None:
        logger.info(
            "No path found between %s and %s",
            src_node.name,
            dst_node.name,
        )
        return PathResult(
            found=False,
            hops=[],
            bottleneck_snr_db=None,
            total_relay_hops=0,
            message=f"No viable path found between {src_node.name} and {dst_node.name}"
            + processing_warning,
        )

    hops: list[HopInfo] = []
    for k, idx in enumerate(path_indices):
        gn = graph[idx]
        snr = None
        if k < len(path_indices) - 1:
            next_idx = path_indices[k + 1]
            snr = (
                round(matrix[idx][next_idx], 1)
                if matrix[idx][next_idx] is not None
                else None
            )
        hops.append(
            HopInfo(
                node_id=gn.node_id, name=gn.name, lat=gn.lat, lon=gn.lon, snr_db=snr
            )
        )

    relay_count = len(path_indices) - 2  # subtract source and destination
    if relay_count == 0:
        msg = (
            f"Direct link — {src_node.name} ↔ {dst_node.name} "
            f"(SNR: {bottleneck:.1f} dB, no relay needed)"
        )
    else:
        msg = (
            f"Path via {relay_count} relay(s): "
            + " → ".join(graph[i].name for i in path_indices)
            + f" — bottleneck SNR: {bottleneck:.1f} dB"
        )

    logger.info(
        "Path found: %s (bottleneck SNR %.1f dB, %d relay(s))",
        " → ".join(graph[i].name for i in path_indices),
        bottleneck,
        relay_count,
    )
    return PathResult(
        found=True,
        hops=hops,
        bottleneck_snr_db=round(bottleneck, 1),
        total_relay_hops=relay_count,
        message=msg + processing_warning,
    )

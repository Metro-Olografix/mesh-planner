import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

logger = logging.getLogger(__name__)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_optional_user, validate_token
from app.config import settings
from app.database import get_db
from app.models.node_event import NodeEvent
from app.services.sse import sse_manager

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def sse_stream(request: Request, token: str | None = Query(None)):
    """
    Server-Sent Events stream. Broadcasts node changes to all connected clients.

    Authentication: pass the access token as ?token=... query parameter
    (EventSource API does not support custom headers).
    When PUBLIC_ACCESS=true, unauthenticated connections are allowed.
    """
    if token:
        await validate_token(token)
    elif not settings.public_access:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    queue = sse_manager.connect()
    logger.debug("SSE client connected from %s", request.client)

    async def generate():
        try:
            while True:
                if await request.is_disconnected():
                    logger.debug(
                        "SSE client disconnected from %s",
                        request.client,
                    )
                    break
                try:
                    payload = await asyncio.wait_for(
                        queue.get(), timeout=25.0
                    )
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            sse_manager.disconnect(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/events/recent")
async def recent_events(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: dict | None = Depends(get_optional_user),
):
    """Return the most recent node activity events, newest first."""
    result = await db.execute(
        select(NodeEvent)
        .order_by(NodeEvent.timestamp.desc())
        .limit(limit)
    )
    events = result.scalars().all()
    return [
        {
            "type": e.event_type,
            "data": {
                "id": e.node_id,
                "name": e.node_name,
                "by": e.by if user else "someone",
            },
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]

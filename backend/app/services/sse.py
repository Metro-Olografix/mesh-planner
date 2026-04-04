import asyncio
import json
from typing import List


class SSEManager:
    """Broadcast server-sent events to all connected clients."""

    def __init__(self) -> None:
        self._queues: List[asyncio.Queue] = []

    def connect(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues.append(q)
        return q

    def disconnect(self, q: asyncio.Queue) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    async def broadcast(self, event_type: str, data: dict) -> None:
        payload = json.dumps({"type": event_type, "data": data})
        for q in list(self._queues):
            await q.put(payload)


sse_manager = SSEManager()

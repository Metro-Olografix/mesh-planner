from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PathRequest(BaseModel):
    source_node_id: UUID
    destination_node_id: UUID
    exclude_statuses: List[str] = Field(default_factory=list)


class HopInfo(BaseModel):
    node_id: Optional[UUID] = None
    name: str
    lat: float
    lon: float
    snr_db: Optional[float] = None   # estimated SNR on the link FROM this node to the next


class PathResult(BaseModel):
    found: bool
    hops: List[HopInfo]
    bottleneck_snr_db: Optional[float] = None
    total_relay_hops: int
    message: str

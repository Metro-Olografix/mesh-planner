from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.node import NodeStatus


class HardwareProfileOut(BaseModel):
    id: str
    name: str
    manufacturer: str
    tx_power_dbm: float
    frequency_mhz: float
    rx_sensitivity_dbm: float
    default_antenna_gain_dbi: float
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class NodeCreate(BaseModel):
    name: str
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    height_m: float = Field(ge=0.1, default=2.0)
    status: NodeStatus = NodeStatus.planned
    hardware_id: str
    antenna_gain_dbi: Optional[float] = None
    sim_radius_km: float = Field(ge=1, le=100, default=10.0)
    environment: str = "auto"
    lora_preset: str = "MEDIUM_FAST"
    high_resolution: bool = True
    notes: Optional[str] = None


class NodeUpdate(BaseModel):
    name: Optional[str] = None
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    height_m: Optional[float] = Field(None, ge=0.1)
    status: Optional[NodeStatus] = None
    hardware_id: Optional[str] = None
    antenna_gain_dbi: Optional[float] = None
    sim_radius_km: Optional[float] = Field(None, ge=1, le=100)
    environment: Optional[str] = None
    lora_preset: Optional[str] = None
    high_resolution: Optional[bool] = None
    notes: Optional[str] = None


class NodeOut(BaseModel):
    id: UUID
    name: str
    lat: float
    lon: float
    height_m: float
    status: NodeStatus
    hardware_id: str
    antenna_gain_dbi: Optional[float]
    sim_radius_km: float
    environment: str
    lora_preset: str
    high_resolution: bool
    notes: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    hardware: HardwareProfileOut
    coverage_status: Optional[str] = None

    model_config = {"from_attributes": True}


class NodePublicOut(BaseModel):
    """Stripped-down node response for unauthenticated (public) requests.
    Coordinates are fuzzed server-side; sensitive fields are omitted."""

    id: UUID
    name: str
    lat: float
    lon: float
    height_m: float
    status: NodeStatus
    hardware_id: str
    sim_radius_km: float
    environment: str
    lora_preset: str
    high_resolution: bool
    hardware: HardwareProfileOut
    coverage_status: Optional[str] = None

    model_config = {"from_attributes": True}

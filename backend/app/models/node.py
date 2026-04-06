import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class NodeStatus(str, enum.Enum):
    planned = "planned"
    deployed = "deployed"
    draft = "draft"


class Node(Base):
    __tablename__ = "nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    height_m = Column(Float, nullable=False, default=2.0)   # antenna height AGL
    status = Column(Enum(NodeStatus), nullable=False, default=NodeStatus.planned)
    hardware_id = Column(String, ForeignKey("hardware_profiles.id"), nullable=False)
    antenna_gain_dbi = Column(Float, nullable=True)          # overrides hardware default when set
    sim_radius_km = Column(Float, nullable=False, server_default="10", default=10.0)  # SPLAT! radius
    # Clutter environment: auto | urban | suburban | rural | open
    # "auto" queries ESA WorldCover; others use preset heights
    environment = Column(String, nullable=False, server_default="auto", default="auto")
    # LoRa modem preset: SHORT_FAST | SHORT_SLOW | MEDIUM_FAST | MEDIUM_SLOW |
    #                    LONG_FAST | LONG_SLOW | VERY_LONG_SLOW
    lora_preset = Column(String, nullable=False, server_default="MEDIUM_FAST", default="MEDIUM_FAST")
    high_resolution = Column(Boolean, nullable=False, server_default="true", default=True)
    notes = Column(String, nullable=True)
    created_by = Column(String, nullable=False)              # OAuth subject
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hardware = relationship("HardwareProfile", back_populates="nodes")
    coverage = relationship(
        "CoverageCache",
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
    )

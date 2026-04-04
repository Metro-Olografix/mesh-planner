import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class CoverageCache(Base):
    __tablename__ = "coverage_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(
        UUID(as_uuid=True), ForeignKey("nodes.id"), nullable=False, unique=True
    )
    task_id = Column(String, nullable=True)
    # pending | processing | completed | failed
    status = Column(String, nullable=False, default="pending")
    geotiff = Column(LargeBinary, nullable=True)
    computed_at = Column(DateTime, nullable=True)
    # Set to True when node RF params change; result is stale until re-computed
    invalidated = Column(Boolean, default=False)

    node = relationship("Node", back_populates="coverage")

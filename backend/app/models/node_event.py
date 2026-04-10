import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class NodeEvent(Base):
    __tablename__ = "node_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(
        String, nullable=False
    )  # node_created | node_updated | node_deleted
    node_id = Column(String, nullable=True)
    node_name = Column(String, nullable=False)
    by = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

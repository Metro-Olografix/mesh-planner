from sqlalchemy import Boolean, Column, Float, String
from sqlalchemy.orm import relationship

from app.database import Base


class HardwareProfile(Base):
    __tablename__ = "hardware_profiles"

    id = Column(String, primary_key=True)          # slug, e.g. "t-beam-v1"
    name = Column(String, nullable=False)
    manufacturer = Column(String, nullable=False)
    tx_power_dbm = Column(Float, nullable=False)
    frequency_mhz = Column(Float, nullable=False, default=869.525)
    rx_sensitivity_dbm = Column(Float, nullable=False, default=-130.0)
    default_antenna_gain_dbi = Column(Float, nullable=False, default=2.0)
    description = Column(String, nullable=True)
    is_custom = Column(Boolean, default=False)

    nodes = relationship("Node", back_populates="hardware")

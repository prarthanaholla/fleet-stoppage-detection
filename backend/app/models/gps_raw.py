from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Boolean, func, UniqueConstraint
from app.db.base import Base

class GpsRaw(Base):
    __tablename__ = "gps_raw"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    gps_time = Column(DateTime(timezone=True), nullable=False)
    speed = Column(Float, nullable=True)
    processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("vehicle_id", "gps_time", name="unique_vehicle_gps_time"),
    )
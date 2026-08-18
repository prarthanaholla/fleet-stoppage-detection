from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from app.db.base import Base

class GpsMatched(Base):
    __tablename__ = "gps_matched"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    gps_time = Column(DateTime(timezone=True), nullable=False)
    route_distance_m = Column(Float, nullable=True)
    trip_started_at = Column(DateTime(timezone=True), nullable=False)
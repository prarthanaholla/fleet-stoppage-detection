from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from app.db.base import Base

class Trip(Base):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    total_distance_m = Column(Float, nullable=False, default=0)
    stoppage_count = Column(Integer, nullable=False, default=0)
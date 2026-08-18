from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, CheckConstraint
from geoalchemy2 import Geometry
from app.db.base import Base

class Stoppage(Base):
    __tablename__ = "stoppages"

    id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    location = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="SUSPECTED")

    __table_args__ = (
        CheckConstraint(
            "status IN ('SUSPECTED', 'CONFIRMED', 'FALSE_ALARM', 'ACTIVE', 'ENDED')",
            name="valid_status"
        ),
    )
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.db.base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    last_lat = Column(Float)
    last_lng = Column(Float)
    last_seen = Column(DateTime)
    org_id = Column(Integer, ForeignKey("organisations.id"), nullable=False)
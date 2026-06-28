from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.db.base import Base

class GpsRaw(Base):
    __tablename__="gps_raw"

    id=Column(Integer,primary_key=True)
    vehicle_id=Column(Integer,ForeignKey("vehicles.id"),nullable=False)
    gps_time=Column(DateTime,nullable=False)
    lat=Column(Float,nullable=False)
    lon=Column(Float,nullable=False)
    speed=Column(Float)
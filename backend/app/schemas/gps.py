from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GPSPingSchema(BaseModel):
    vehicle_name: str
    lat: float
    lng: float
    gps_time: datetime
    speed: Optional[float] = None
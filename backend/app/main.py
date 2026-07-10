from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.schemas.gps import GPSPingSchema

app = FastAPI()

@app.get("/health")
async def health_check():
    # Check database
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    # Overall status
    overall = "ok" if db_status == "ok" else "unhealthy"

    return {
        "status": overall,
        "database": db_status
    }
@app.post("/api/v1/ingest")
async def ingest_gps(ping: GPSPingSchema):
    return {
        "received": True,
        "vehicle_name": ping.vehicle_name,
        "lat": ping.lat,
        "lng": ping.lng,
        "gps_time": str(ping.gps_time),
        "speed": ping.speed
    }
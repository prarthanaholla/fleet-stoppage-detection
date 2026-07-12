from fastapi import FastAPI
from sqlalchemy import text, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db.session import AsyncSessionLocal
from app.schemas.gps import GPSPingSchema
from app.models.vehicles import Vehicle
from app.models.gps_raw import GpsRaw

app = FastAPI()

@app.get("/health")
async def health_check():
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"
    overall = "ok" if db_status == "ok" else "unhealthy"
    return {"status": overall, "database": db_status}

@app.post("/api/v1/ingest")
async def ingest_gps(ping: GPSPingSchema):
    async with AsyncSessionLocal() as session:
        async with session.begin():

            gps_time = ping.gps_time.replace(tzinfo=None)
            # Step 1 — upsert vehicle
            stmt = pg_insert(Vehicle).values(
                name=ping.vehicle_name,
                last_lat=ping.lat,
                last_lng=ping.lng,
                last_seen=gps_time,
                org_id=1
            ).on_conflict_do_update(
                index_elements=["name"],
                set_={
                    "last_lat": ping.lat,
                    "last_lng": ping.lng,
                    "last_seen": gps_time
                }
            ).returning(Vehicle.id)

            result = await session.execute(stmt)
            vehicle_id = result.scalar_one()

            # Step 2 — insert GPS raw point
            gps_point = GpsRaw(
                vehicle_id=vehicle_id,
                lat=ping.lat,
                lon=ping.lng,
                gps_time=gps_time,
                speed=ping.speed
            )
            session.add(gps_point)

    return {
        "received": True,
        "vehicle_id": vehicle_id,
        "vehicle_name": ping.vehicle_name
    }
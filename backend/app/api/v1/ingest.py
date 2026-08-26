from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.db.session import AsyncSessionLocal
from app.schemas.gps import GPSPingSchema
from app.models.vehicles import Vehicle
from app.models.gps_raw import GpsRaw
from app.auth import decode_access_token, security
from app.workers.pipeline.tasks import process_gps_point
from app.workers.pipeline.dev_tools import trigger_pipeline_now

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/ingest")
@limiter.limit("30/minute")
async def ingest_gps(
    request: Request,
    ping: GPSPingSchema,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    org_id = payload["org_id"]

    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                gps_time = ping.gps_time

                # Step 1 — upsert vehicle
                stmt = pg_insert(Vehicle).values(
                    name=ping.vehicle_name,
                    last_lat=ping.lat,
                    last_lng=ping.lng,
                    last_seen=gps_time,
                    org_id=org_id
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

                # Step 2 — insert GPS raw point (idempotent)
                # ON CONFLICT DO NOTHING handles duplicate pings from device retries
                gps_stmt = pg_insert(GpsRaw).values(
                    vehicle_id=vehicle_id,
                    lat=ping.lat,
                    lon=ping.lng,
                    gps_time=gps_time,
                    speed=ping.speed
                ).on_conflict_do_nothing(
                    index_elements=["vehicle_id", "gps_time"]
                ).returning(GpsRaw.id)

                gps_result = await session.execute(gps_stmt)
                gps_row = gps_result.fetchone()

                if gps_row is None:
                    # Duplicate ping — already processed, silently ignore
                    return {
                        "received": True,
                        "duplicate": True,
                        "vehicle_name": ping.vehicle_name,
                        "status": "duplicate_ignored"
                    }

                point_id = gps_row[0]

        # Step 3 — queue for async pipeline processing
        # Called AFTER transaction commits to ensure row exists in DB
        process_gps_point.delay(point_id)

        return {
            "received": True,
            "duplicate": False,
            "vehicle_id": vehicle_id,
            "vehicle_name": ping.vehicle_name,
            "org_id": org_id,
            "point_id": point_id,
            "status": "queued"
        }

    except SQLAlchemyError as e:
        print(f"[INGEST DB ERROR] {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Database error — ping not saved. Please retry."
        )
    except Exception as e:
        print(f"[INGEST ERROR] {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error — please retry."
        )


@router.post("/trigger-pipeline/{vehicle_id}")
async def trigger_pipeline(
    vehicle_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    trigger_pipeline_now.delay(vehicle_id)
    return {"status": "triggered", "vehicle_id": vehicle_id}
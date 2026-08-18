from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import AsyncSessionLocal
from app.schemas.gps import GPSPingSchema
from app.models.vehicles import Vehicle
from app.models.gps_raw import GpsRaw
from app.auth import decode_access_token, security
from app.workers.pipeline.tasks import process_gps_point
from app.workers.pipeline.dev_tools import trigger_pipeline_now

router = APIRouter()

@router.post("/ingest")
async def ingest_gps(
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
                gps_time = ping.gps_time.replace(tzinfo=None)

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

                gps_point = GpsRaw(
                    vehicle_id=vehicle_id,
                    lat=ping.lat,
                    lon=ping.lng,
                    gps_time=gps_time,
                    speed=ping.speed
                )
                session.add(gps_point)
                await session.flush()
                point_id = gps_point.id

        process_gps_point.delay(point_id)

        return {
            "received": True,
            "vehicle_id": vehicle_id,
            "vehicle_name": ping.vehicle_name,
            "org_id": org_id,
            "point_id": point_id,
            "status": "queued"
        }

    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=500,
            detail="Database error — ping not saved. Please retry."
        )
    except Exception as e:
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
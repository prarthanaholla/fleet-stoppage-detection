from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.auth import decode_access_token, security

router = APIRouter()

@router.get("/vehicles")
async def get_vehicles(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    org_id = payload["org_id"]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT id, name, last_lat, last_lng, last_seen
                FROM vehicles
                WHERE org_id = :org_id
                ORDER BY last_seen DESC
            """),
            {"org_id": org_id}
        )
        rows = result.fetchall()

    return [
        {
            "id": row[0],
            "name": row[1],
            "lat": row[2],
            "lng": row[3],
            "last_seen": str(row[4])
        }
        for row in rows
    ]


@router.get("/stoppages")
async def get_stoppages(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with AsyncSessionLocal() as session:
        # total count
        count_result = await session.execute(
            text("""
                SELECT COUNT(*) FROM stoppages s
                JOIN vehicles v ON s.vehicle_id = v.id
                WHERE s.status = 'CONFIRMED'
            """)
        )
        total = count_result.scalar()

        # paginated results
        result = await session.execute(
            text("""
                SELECT
                    s.id,
                    v.name as vehicle_name,
                    ST_Y(s.location::geometry) as lat,
                    ST_X(s.location::geometry) as lon,
                    s.started_at,
                    s.ended_at,
                    s.duration_seconds,
                    s.status
                FROM stoppages s
                JOIN vehicles v ON s.vehicle_id = v.id
                WHERE s.status = 'CONFIRMED'
                ORDER BY s.started_at DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )
        rows = result.fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": row[0],
                "vehicle_name": row[1],
                "lat": row[2],
                "lng": row[3],
                "started_at": str(row[4]),
                "ended_at": str(row[5]),
                "duration_seconds": row[6],
                "status": row[7]
            }
            for row in rows
        ]
    }


@router.get("/trip-path")
async def get_trip_path(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    limit: int = Query(default=500, le=1000),
    offset: int = Query(default=0, ge=0)
):
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT lat, lon, gps_time
                FROM gps_matched
                ORDER BY gps_time ASC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )
        rows = result.fetchall()

    return [
        {
            "lat": row[0],
            "lng": row[1],
            "time": str(row[2])
        }
        for row in rows
    ]
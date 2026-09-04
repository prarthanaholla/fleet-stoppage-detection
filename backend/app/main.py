from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.dashboard import router as dashboard_router

# Rate limiter — identifies clients by IP address
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()

# Register rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(ingest_router, prefix="/api/v1", tags=["ingest"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])


@app.get("/health")
async def health_check():
    # Check database
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    # Check Redis
    redis_status = "ok"
    try:
        import redis
        import os
        r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
    except Exception:
        redis_status = "down"

    # Check Valhalla
    valhalla_status = "ok"
    try:
        import httpx
        import os
        valhalla_url = os.getenv("VALHALLA_URL", "http://localhost:8002")
        response = httpx.get(f"{valhalla_url}/status", timeout=3)
        # Valhalla returns 404 on root but is still running
        if response.status_code not in [200, 404]:
            valhalla_status = "down"
    except Exception:
        valhalla_status = "down"

    # Overall status
    all_ok = all(s == "ok" for s in [db_status, redis_status, valhalla_status])
    overall = "ok" if all_ok else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "valhalla": valhalla_status
    }
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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(ingest_router, prefix="/api/v1", tags=["ingest"])
app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])


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
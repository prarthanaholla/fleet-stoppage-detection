from fastapi import FastAPI
from sqlalchemy import text
from app.db.session import AsyncSessionLocal
from app.api.v1.auth import router as auth_router
from app.api.v1.ingest import router as ingest_router

app = FastAPI()

app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(ingest_router, prefix="/api/v1", tags=["ingest"])

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
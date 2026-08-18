"""
Development and demo utilities.
NOT for production use.

These tools are separated from production pipeline code (tasks.py)
to maintain clean separation of concerns. In production deployment,
this module can be excluded from Celery's include list.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text

from app.workers.celery_app import celery_app
from app.workers.pipeline.tasks import run_layer2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
engine = create_engine(DATABASE_URL)


@celery_app.task
def trigger_pipeline_now(vehicle_id: int):
    """
    Manually triggers Layer 2 for a vehicle immediately.
    Bypasses the TRIP_BOUNDARY_SECONDS wait time.

    USE CASE: Demo, testing, development only.
    NOT for production use.
    """
    print(f"[DEV] Manual trigger: Layer 2 for vehicle {vehicle_id}")

    with Session(engine) as session:
        result = session.execute(
            text("""
                SELECT MIN(gps_time), MAX(gps_time)
                FROM gps_raw
                WHERE vehicle_id = :vid AND processed = FALSE
            """),
            {"vid": vehicle_id}
        ).fetchone()

        if not result or not result[0]:
            print(f"[DEV] No unprocessed points for vehicle {vehicle_id}")
            return {"status": "no_data", "vehicle_id": vehicle_id}

        first_ping = result[0]
        last_ping = result[1]

    run_layer2.delay(vehicle_id, first_ping.isoformat(), last_ping.isoformat())
    return {"status": "triggered", "vehicle_id": vehicle_id}
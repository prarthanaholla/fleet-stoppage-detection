import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.workers.celery_app import celery_app
from app.workers.pipeline.edp import simplify_with_estc
from app.workers.pipeline.valhalla import match_points, calculate_segments
from app.workers.pipeline.detection import detect_stoppages, check_layer1_threshold

load_dotenv()

# Configuration from .env
LAYER1_DISTANCE_THRESHOLD_M = float(os.getenv("LAYER1_DISTANCE_THRESHOLD_M", 50))
LAYER1_TIME_THRESHOLD_S = float(os.getenv("LAYER1_TIME_THRESHOLD_S", 300))
TRIP_BOUNDARY_SECONDS = float(os.getenv("TRIP_BOUNDARY_SECONDS", 1800))

# Sync database URL for Celery worker
DATABASE_URL = os.getenv("DATABASE_URL", "").replace("+asyncpg", "")
engine = create_engine(DATABASE_URL)


def get_session():
    return Session(engine)


# ─────────────────────────────────────────────────────────────
# MAIN CELERY TASK — runs on every GPS ping
# Only does Layer 1 — Layer 2 handled by beat task
# ─────────────────────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_gps_point(self, point_id: int):
    """
    Runs on every GPS ping.
    Layer 1 only — immediate threshold detection.
    Layer 2 is handled by check_trip_endings beat task.
    """
    try:
        with get_session() as session:

            # Fetch current point
            result = session.execute(
                text("""
                    SELECT id, vehicle_id, lat, lon, gps_time
                    FROM gps_raw WHERE id = :id
                """),
                {"id": point_id}
            ).fetchone()

            if not result:
                return {"status": "not_found", "point_id": point_id}

            current = {
                "id": result[0],
                "vehicle_id": result[1],
                "lat": result[2],
                "lon": result[3],
                "gps_time": result[4],
                "location_time_ms": int(result[4].timestamp() * 1000)
            }

            vehicle_id = current["vehicle_id"]

            # Fetch last point before current
            last_result = session.execute(
                text("""
                    SELECT id, lat, lon, gps_time
                    FROM gps_raw
                    WHERE vehicle_id = :vid
                      AND gps_time < (SELECT gps_time FROM gps_raw WHERE id = :pid)
                    ORDER BY gps_time DESC
                    LIMIT 1
                """),
                {"vid": vehicle_id, "pid": point_id}
            ).fetchone()

            if not last_result:
                return {"status": "first_ping", "point_id": point_id}

            last = {
                "lat": last_result[1],
                "lon": last_result[2],
                "gps_time": last_result[3],
                "location_time_ms": int(last_result[3].timestamp() * 1000)
            }

            # ── LAYER 1: Threshold detection ──────────────────────────────
            is_stopped = check_layer1_threshold(
                current_lat=current["lat"],
                current_lon=current["lon"],
                current_time_ms=current["location_time_ms"],
                last_lat=last["lat"],
                last_lon=last["lon"],
                last_time_ms=last["location_time_ms"],
                distance_threshold_m=LAYER1_DISTANCE_THRESHOLD_M,
                time_threshold_s=LAYER1_TIME_THRESHOLD_S
            )

            if is_stopped:
                print(f"[LAYER 1] Suspected stoppage for vehicle {vehicle_id} at point {point_id}")

                # Check if suspected stoppage already exists nearby
                existing = session.execute(
                    text("""
                        SELECT id FROM stoppages
                        WHERE vehicle_id = :vid
                          AND status = 'SUSPECTED'
                          AND started_at >= :since
                    """),
                    {
                        "vid": vehicle_id,
                        "since": last["gps_time"]
                    }
                ).fetchone()

                if not existing:
                    session.execute(
                        text("""
                            INSERT INTO stoppages
                            (vehicle_id, location, started_at, status)
                            VALUES (
                                :vid,
                                ST_SetSRID(ST_Point(:lon, :lat), 4326),
                                :started_at,
                                'SUSPECTED'
                            )
                        """),
                        {
                            "vid": vehicle_id,
                            "lon": current["lon"],
                            "lat": current["lat"],
                            "started_at": last["gps_time"]
                        }
                    )
                    session.commit()

            return {
                "status": "processed",
                "point_id": point_id,
                "vehicle_id": vehicle_id,
                "layer1_triggered": is_stopped
            }

    except Exception as exc:
        print(f"[ERROR] process_gps_point {point_id}: {exc}")
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────
# BEAT TASK — runs every 5 minutes
# Detects completed trips and runs Layer 2
# ─────────────────────────────────────────────────────────────
@celery_app.task
def check_trip_endings():
    """
    Runs every 5 minutes via Celery Beat.
    Finds vehicles that have gone silent for TRIP_BOUNDARY_SECONDS.
    Runs Layer 2 (full EDP + Valhalla pipeline) on their complete trip.
    """
    print(f"[BEAT] Checking for completed trips...")

    with get_session() as session:
        # Find vehicles whose last ping was > TRIP_BOUNDARY_SECONDS ago
        # AND haven't been processed yet
        cutoff_time = datetime.utcnow() - timedelta(seconds=TRIP_BOUNDARY_SECONDS)

        vehicles = session.execute(
            text("""
                SELECT 
                    vehicle_id,
                    MAX(gps_time) as last_ping,
                    MIN(gps_time) as first_ping,
                    COUNT(*) as point_count
                FROM gps_raw
                WHERE processed = FALSE
                GROUP BY vehicle_id
                HAVING MAX(created_at) < :cutoff
            """),
            {"cutoff": cutoff_time}
        ).fetchall()

        if not vehicles:
            print(f"[BEAT] No completed trips found")
            return

        for row in vehicles:
            vehicle_id = row[0]
            last_ping = row[1]
            first_ping = row[2]
            point_count = row[3]

            print(f"[BEAT] Vehicle {vehicle_id}: {point_count} points, "
                  f"trip {first_ping} → {last_ping}")

            # Run Layer 2 on complete trip
            run_layer2.delay(vehicle_id, first_ping.isoformat(), last_ping.isoformat())


# ─────────────────────────────────────────────────────────────
# LAYER 2 TASK — full EDP + Valhalla pipeline
# ─────────────────────────────────────────────────────────────
@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_layer2(self, vehicle_id: int, first_ping_str: str, last_ping_str: str):
    """
    Full EDP + Valhalla + stoppage detection pipeline.
    Runs on complete trip data after trip ends.
    """
    try:
        first_ping = datetime.fromisoformat(first_ping_str)
        last_ping = datetime.fromisoformat(last_ping_str)

        print(f"[LAYER 2] Starting for vehicle {vehicle_id}")
        print(f"[LAYER 2] Trip: {first_ping} → {last_ping}")

        with get_session() as session:

            # Fetch ALL unprocessed points for this vehicle
            rows = session.execute(
                text("""
                    SELECT lat, lon, gps_time
                    FROM gps_raw
                    WHERE vehicle_id = :vid
                      AND processed = FALSE
                    ORDER BY gps_time ASC
                """),
                {"vid": vehicle_id}
            ).fetchall()

            if len(rows) < 3:
                print(f"[LAYER 2] Not enough points ({len(rows)}) — skipping")
                return

            # Convert to pipeline format
            points = [
                {
                    "lat": row[0],
                    "lon": row[1],
                    "location_time_ms": int(row[2].timestamp() * 1000)
                }
                for row in rows
            ]

            print(f"[LAYER 2] Running EDP on {len(points)} raw points")

            # Step 1 — EDP filtering
            filtered_points = simplify_with_estc(points)
            print(f"[LAYER 2] EDP: {len(points)} → {len(filtered_points)} points")

            if len(filtered_points) < 2:
                print(f"[LAYER 2] Not enough points after EDP")
                _mark_as_processed(session, vehicle_id)
                session.commit()
                return

            # Step 2 — Valhalla map matching
            matched_points = match_points(filtered_points)
            print(f"[LAYER 2] Map matched {len(matched_points)} points")

            if len(matched_points) < 2:
                print(f"[LAYER 2] Not enough matched points")
                _mark_as_processed(session, vehicle_id)
                session.commit()
                return

            # Step 3 — Route distance calculation
            segments = calculate_segments(matched_points)
            print(f"[LAYER 2] Calculated {len(segments)} segments")

            # Step 4 — Stoppage detection
            stoppages = detect_stoppages(segments)
            print(f"[LAYER 2] Detected {len(stoppages)} stoppages")

            # Step 5 — Save matched points to gps_matched
            total_distance_m = 0
            for i, pt in enumerate(matched_points):
                route_dist = segments[i]['route_distance_m'] if i < len(segments) else None
                if route_dist:
                    total_distance_m += route_dist

                session.execute(
                    text("""
                        INSERT INTO gps_matched
                        (vehicle_id, lat, lon, gps_time, route_distance_m, trip_started_at)
                        VALUES (:vid, :lat, :lon, :gps_time, :dist, :trip_start)
                    """),
                    {
                        "vid": vehicle_id,
                        "lat": pt["lat"],
                        "lon": pt["lon"],
                        "gps_time": datetime.utcfromtimestamp(
                            pt["original_time_ms"] / 1000
                        ),
                        "dist": route_dist,
                        "trip_start": first_ping
                    }
                )

            # Step 6 — Save confirmed stoppages
            for s in stoppages:
                started_at = datetime.utcfromtimestamp(s["started_at_ms"] / 1000)
                ended_at = datetime.utcfromtimestamp(s["ended_at_ms"] / 1000)

                # Check if suspected stoppage exists nearby — update it
                existing = session.execute(
                    text("""
                        SELECT id FROM stoppages
                        WHERE vehicle_id = :vid
                          AND status = 'SUSPECTED'
                          AND ABS(EXTRACT(EPOCH FROM (started_at - :started_at))) < 300
                    """),
                    {"vid": vehicle_id, "started_at": started_at}
                ).fetchone()

                if existing:
                    # Update suspected → confirmed
                    session.execute(
                        text("""
                            UPDATE stoppages
                            SET status = 'CONFIRMED',
                                ended_at = :ended_at,
                                duration_seconds = :duration,
                                location = ST_SetSRID(ST_Point(:lon, :lat), 4326)
                            WHERE id = :id
                        """),
                        {
                            "id": existing[0],
                            "ended_at": ended_at,
                            "duration": s["duration_seconds"],
                            "lon": s["lon"],
                            "lat": s["lat"]
                        }
                    )
                else:
                    # Insert new confirmed stoppage
                    session.execute(
                        text("""
                            INSERT INTO stoppages
                            (vehicle_id, location, started_at, ended_at,
                             duration_seconds, status)
                            VALUES (
                                :vid,
                                ST_SetSRID(ST_Point(:lon, :lat), 4326),
                                :started_at, :ended_at, :duration,
                                'CONFIRMED'
                            )
                        """),
                        {
                            "vid": vehicle_id,
                            "lon": s["lon"],
                            "lat": s["lat"],
                            "started_at": started_at,
                            "ended_at": ended_at,
                            "duration": s["duration_seconds"]
                        }
                    )

            # Step 7 — Save trip record
            session.execute(
                text("""
                    INSERT INTO trips
                    (vehicle_id, started_at, ended_at,
                     total_distance_m, stoppage_count, processed)
                    VALUES (:vid, :start, :end, :dist, :count, TRUE)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "vid": vehicle_id,
                    "start": first_ping,
                    "end": last_ping,
                    "dist": round(total_distance_m, 2),
                    "count": len(stoppages)
                }
            )

            # Step 8 — Mark all points as processed
            _mark_as_processed(session, vehicle_id)
            session.commit()

            print(f"[LAYER 2] Complete — {len(stoppages)} stoppages, "
                  f"{round(total_distance_m/1000, 2)}km total")

            return {
                "status": "complete",
                "vehicle_id": vehicle_id,
                "stoppages": len(stoppages),
                "total_distance_km": round(total_distance_m/1000, 2)
            }

    except Exception as exc:
        print(f"[LAYER 2 ERROR] vehicle {vehicle_id}: {exc}")
        raise self.retry(exc=exc)


# ─────────────────────────────────────────────────────────────
# MANUAL TRIGGER — for demo purposes only
# ─────────────────────────────────────────────────────────────
@celery_app.task
def trigger_pipeline_now(vehicle_id: int):
    """
    Manually triggers Layer 2 for a vehicle immediately.
    Used for demo purposes — bypasses the 30-minute wait.
    """
    print(f"[MANUAL TRIGGER] Running Layer 2 for vehicle {vehicle_id}")

    with get_session() as session:
        result = session.execute(
            text("""
                SELECT MIN(gps_time), MAX(gps_time)
                FROM gps_raw
                WHERE vehicle_id = :vid AND processed = FALSE
            """),
            {"vid": vehicle_id}
        ).fetchone()

        if not result or not result[0]:
            print(f"[MANUAL TRIGGER] No unprocessed points for vehicle {vehicle_id}")
            return

        first_ping = result[0]
        last_ping = result[1]

    run_layer2.delay(vehicle_id, first_ping.isoformat(), last_ping.isoformat())
    return {"status": "triggered", "vehicle_id": vehicle_id}


def _mark_as_processed(session, vehicle_id: int):
    """Mark all unprocessed gps_raw points for a vehicle as processed."""
    session.execute(
        text("""
            UPDATE gps_raw SET processed = TRUE
            WHERE vehicle_id = :vid AND processed = FALSE
        """),
        {"vid": vehicle_id}
    )
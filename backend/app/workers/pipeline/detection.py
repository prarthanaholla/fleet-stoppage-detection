import os
from dotenv import load_dotenv

load_dotenv()

BASELINE_SPEED_MPS = float(os.getenv("BASELINE_SPEED_KMPH", 20)) * 1000 / 3600
DISTANCE_THRESHOLD_M = float(os.getenv("DISTANCE_THRESHOLD_M", 10))
TIME_THRESHOLD_S = float(os.getenv("TIME_THRESHOLD_S", 60))


def detect_stoppages(segments: list) -> list:
    """
    Detect stoppages using distance-time inconsistency.

    This is the core Layer 2 algorithm — same logic as original
    stoppage_detection.py but operating on Python dicts instead of files.

    segments: list of dicts with keys:
        start_lat, start_lon, end_lat, end_lon,
        route_distance_m, start_time_ms, end_time_ms

    Returns: list of stoppage dicts with keys:
        lat, lon, started_at_ms, ended_at_ms,
        route_distance_m, duration_seconds
    """
    if not segments:
        return []

    stoppages = []
    start = 0
    end = 1

    while end < len(segments):
        # Sum route distances from start to end
        route_distance = sum(
            segments[i]['route_distance_m']
            for i in range(start, end + 1)
        )

        t1 = segments[start]['start_time_ms']
        t2 = segments[end]['end_time_ms']
        real_time_sec = (t2 - t1) / 1000

        expected_time = route_distance / BASELINE_SPEED_MPS

        if route_distance > DISTANCE_THRESHOLD_M:
            if real_time_sec > expected_time:
                # Actual time >> expected time → stoppage
                stoppages.append({
                    "lat": segments[start]['start_lat'],
                    "lon": segments[start]['start_lon'],
                    "started_at_ms": t1,
                    "ended_at_ms": t2,
                    "route_distance_m": round(route_distance, 2),
                    "duration_seconds": int(real_time_sec)
                })
            start = end
            end += 1
        else:
            # Distance too small — check time threshold
            if real_time_sec > TIME_THRESHOLD_S:
                stoppages.append({
                    "lat": segments[start]['start_lat'],
                    "lon": segments[start]['start_lon'],
                    "started_at_ms": t1,
                    "ended_at_ms": t2,
                    "route_distance_m": round(route_distance, 2),
                    "duration_seconds": int(real_time_sec)
                })
                start = end
            end += 1

    return stoppages


def check_layer1_threshold(
    current_lat: float,
    current_lon: float,
    current_time_ms: int,
    last_lat: float,
    last_lon: float,
    last_time_ms: int,
    distance_threshold_m: float,
    time_threshold_s: float
) -> bool:
    """
    Layer 1 simple threshold check.
    Returns True if vehicle appears to be stopped.

    Uses haversine distance — fast, no Valhalla needed.
    """
    from app.workers.pipeline.edp import haversine

    distance = haversine(current_lat, current_lon, last_lat, last_lon)
    time_gap_s = (current_time_ms - last_time_ms) / 1000

    return distance < distance_threshold_m and time_gap_s > time_threshold_s
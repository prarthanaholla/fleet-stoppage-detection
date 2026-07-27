import os
import json
import requests
import pygeohash as geohash
from dotenv import load_dotenv
from app.services.cache import get_cached_match, set_cached_match

load_dotenv()

VALHALLA_URL = os.getenv("VALHALLA_URL", "http://localhost:8002")


def _get_geohash(lat: float, lon: float, precision: int = 6) -> str:
    """Convert lat/lon to geohash for cache key."""
    return geohash.encode(lat, lon, precision)


def match_points(points: list) -> list:
    """
    Map match GPS points to real roads using Valhalla trace_attributes.
    Checks Redis cache before calling Valhalla.

    points: list of dicts with keys: lat, lon, location_time_ms
    Returns: list of matched dicts with keys: lat, lon, original_time_ms
    """
    if len(points) < 2:
        return points

    # Build cache key from first and last point geohash
    first_hash = _get_geohash(points[0]['lat'], points[0]['lon'])
    last_hash = _get_geohash(points[-1]['lat'], points[-1]['lon'])
    cache_key = f"{first_hash}:{last_hash}:{len(points)}"

    # Check Redis cache first
    cached = get_cached_match(cache_key)
    if cached:
        return cached

    # Build Valhalla request
    locations = [
        {
            "lat": pt['lat'],
            "lon": pt['lon'],
            "time": pt['location_time_ms'] // 1000
        }
        for pt in points
    ]

    payload = {
        "shape": locations,
        "costing": "bicycle",
        "shape_match": "map_snap",
        "use_timestamps": True,
        "trace_options": {
            "gps_accuracy": 5.0,
            "breakage_distance": 200,
            "interpolation_distance": 10,
            "search_radius": 30
        },
        "filters": {
            "attributes": ["matched.point"]
        }
    }

    response = requests.post(
        f"{VALHALLA_URL}/trace_attributes",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Valhalla map matching failed: {response.text}")

    result = response.json()
    matched_points = result["matched_points"]

    # Build result list
    output = []
    for i, pt in enumerate(matched_points):
        output.append({
            "lat": pt["lat"],
            "lon": pt["lon"],
            "original_time_ms": points[i]["location_time_ms"]
        })

    # Cache the result
    set_cached_match(cache_key, output)

    return output


def calculate_route_distance(
    point_a: dict,
    point_b: dict
) -> float:
    """
    Calculate real road distance between two matched points using Valhalla route.

    point_a, point_b: dicts with keys: lat, lon
    Returns: distance in meters
    """
    body = {
        "locations": [
            {"lat": point_a["lat"], "lon": point_a["lon"]},
            {"lat": point_b["lat"], "lon": point_b["lon"]}
        ],
        "costing": "bicycle",
        "directions_options": {"units": "kilometers"}
    }

    response = requests.post(
        f"{VALHALLA_URL}/route",
        json=body,
        timeout=30
    )

    if response.status_code != 200:
        return 0.0

    route = response.json()["trip"]
    dist_meters = route["summary"]["length"] * 1000
    return round(dist_meters, 2)


def calculate_segments(matched_points: list) -> list:
    """
    Calculate route distance for each consecutive pair of matched points.

    matched_points: list of dicts with keys: lat, lon, original_time_ms
    Returns: list of segment dicts with keys:
        start_lat, start_lon, end_lat, end_lon,
        route_distance_m, start_time_ms, end_time_ms
    """
    segments = []

    for i in range(len(matched_points) - 1):
        point_a = matched_points[i]
        point_b = matched_points[i + 1]

        dist = calculate_route_distance(point_a, point_b)

        segments.append({
            "start_lat": point_a["lat"],
            "start_lon": point_a["lon"],
            "end_lat": point_b["lat"],
            "end_lon": point_b["lon"],
            "route_distance_m": dist,
            "start_time_ms": point_a["original_time_ms"],
            "end_time_ms": point_b["original_time_ms"]
        })

    return segments
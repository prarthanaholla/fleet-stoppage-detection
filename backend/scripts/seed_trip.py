import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
VEHICLE_NAME = "Truck A"
EMAIL = "prarthana@porter.in"
PASSWORD = "password123"
GEOJSON_PATH = r"C:\Users\PRARTHANA A R\OneDrive\Documents\fleet-stoppage-detection\backend\scripts\rawgpsdata.geojson"

# Step 1 — Login
print("Logging in...")
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
    "email": EMAIL,
    "password": PASSWORD
})

if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

token = response.json()["access_token"]
print(f"Login successful ✓")

headers = {"Authorization": f"Bearer {token}"}

# Step 2 — Load GeoJSON
print("Loading rawgpsdata.geojson...")
with open(GEOJSON_PATH) as f:
    data = json.load(f)

features = data["features"]
print(f"Loaded {len(features)} GPS points")

# Step 3 — Send each point to ingest endpoint
print("Sending GPS pings to /api/v1/ingest...")
success = 0
failed = 0

for i, feature in enumerate(features):
    lon, lat = feature["geometry"]["coordinates"]
    location_time_ms = feature["properties"]["locationTime"]

    # Convert millisecond timestamp to datetime string
    gps_time = datetime.utcfromtimestamp(location_time_ms / 1000)
    gps_time_str = gps_time.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "vehicle_name": VEHICLE_NAME,
        "lat": lat,
        "lng": lon,
        "gps_time": gps_time_str,
        "speed": None
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/ingest",
            headers=headers,
            json=payload
        )
        if response.status_code == 200:
            success += 1
            point_id = response.json().get("point_id")
            print(f"  Point {i+1}/{len(features)} → point_id={point_id} ✓")
        else:
            failed += 1
            print(f"  Point {i+1}/{len(features)} → FAILED: {response.status_code} {response.text}")
    except Exception as e:
        failed += 1
        print(f"  Point {i+1}/{len(features)} → ERROR: {e}")

print(f"\n{'='*50}")
print(f"Seed complete!")
print(f"Success: {success}/{len(features)}")
print(f"Failed:  {failed}/{len(features)}")
print(f"{'='*50}")
print(f"\nCheck your database:")
print(f"  gps_raw     — should have {success} new rows")
print(f"  stoppages   — Layer 1 suspected stoppages")
print(f"  gps_matched — Layer 2 map matched points")
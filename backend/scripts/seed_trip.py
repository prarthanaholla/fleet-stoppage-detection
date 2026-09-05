import json
import requests
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"
EMAIL = "prarthana@porter.in"  
PASSWORD = "password123"
GEOJSON_PATH = r"C:\Users\PRARTHANA A R\OneDrive\Documents\fleet-stoppage-detection\backend\scripts\rawgpsdata.geojson"

# Three vehicles simulating a small fleet
# Each vehicle gets the same route but with a time offset
# to simulate different trips at different times of day
VEHICLES = [
    {"name": "Truck A", "time_offset_hours": 0},    # original trip time
    {"name": "Truck B", "time_offset_hours": 2},    # 2 hours later
    {"name": "Truck C", "time_offset_hours": 4},    # 4 hours later
]

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

# Step 3 — Seed each vehicle
total_success = 0
total_failed = 0
total_duplicate = 0

for vehicle in VEHICLES:
    vehicle_name = vehicle["name"]
    time_offset = timedelta(hours=vehicle["time_offset_hours"])

    print(f"\n{'='*50}")
    print(f"Seeding {vehicle_name} (offset: +{vehicle['time_offset_hours']} hours)...")
    print(f"{'='*50}")

    success = 0
    failed = 0
    duplicate = 0

    for i, feature in enumerate(features):
        lon, lat = feature["geometry"]["coordinates"]
        location_time_ms = feature["properties"]["locationTime"]

        # Convert ms to datetime and apply time offset
        gps_time = datetime.utcfromtimestamp(location_time_ms / 1000) + time_offset
        gps_time_str = gps_time.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"

        payload = {
            "vehicle_name": vehicle_name,
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
                data_resp = response.json()
                if data_resp.get("duplicate"):
                    duplicate += 1
                    print(f"  Point {i+1}/{len(features)} → duplicate ignored")
                else:
                    success += 1
                    point_id = data_resp.get("point_id")
                    print(f"  Point {i+1}/{len(features)} → point_id={point_id} ✓")
            else:
                failed += 1
                print(f"  Point {i+1}/{len(features)} → FAILED: {response.status_code} {response.text}")
        except Exception as e:
            failed += 1
            print(f"  Point {i+1}/{len(features)} → ERROR: {e}")

    print(f"\n{vehicle_name} complete: Success={success}, Duplicate={duplicate}, Failed={failed}")
    total_success += success
    total_failed += failed
    total_duplicate += duplicate

print(f"\n{'='*50}")
print(f"ALL VEHICLES SEEDED")
print(f"{'='*50}")
print(f"Total success:    {total_success}")
print(f"Total duplicates: {total_duplicate}")
print(f"Total failed:     {total_failed}")
print(f"\nDatabase summary:")
print(f"  gps_raw should have: {total_success} rows")
print(f"  vehicles should have: {len(VEHICLES)} rows")
print(f"\nTrigger Layer 2 for each vehicle from Swagger:")
for v in VEHICLES:
    print(f"  POST /api/v1/trigger-pipeline/{{vehicle_id}} for {v['name']}")
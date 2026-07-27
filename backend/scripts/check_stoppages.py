# scripts/check_stoppages.py
import psycopg2

conn = psycopg2.connect(
    host="localhost", port=5432,
    database="fleetdb", user="postgres", password="password"
)
cursor = conn.cursor()

cursor.execute("""
    SELECT 
        id,
        ST_Y(location::geometry) as lat,
        ST_X(location::geometry) as lon,
        started_at,
        ended_at,
        duration_seconds,
        status
    FROM stoppages
    ORDER BY started_at
""")

rows = cursor.fetchall()
print(f"Total stoppages: {len(rows)}")
print(f"\n{'ID':<5} {'LAT':<12} {'LON':<12} {'DURATION':<12} {'STATUS'}")
print("-" * 60)
for row in rows:
    id, lat, lon, started, ended, duration, status = row
    print(f"{id:<5} {lat:<12.6f} {lon:<12.6f} {str(duration)+'s':<12} {status}")

cursor.execute("SELECT COUNT(*) FROM gps_matched")
matched = cursor.fetchone()[0]
print(f"\ngps_matched rows: {matched}")

cursor.execute("SELECT total_distance_m, stoppage_count FROM trips WHERE vehicle_id = 1")
trip = cursor.fetchone()
if trip:
    print(f"Trip distance: {trip[0]/1000:.2f}km")
    print(f"Trip stoppages: {trip[1]}")

cursor.close()
conn.close()
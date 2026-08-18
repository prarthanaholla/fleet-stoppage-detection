import psycopg2
import time
from datetime import datetime

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)
cursor = conn.cursor()

print("=" * 60)
print("FLEET STOPPAGE DETECTION — PHASE 5 MEASUREMENTS")
print("=" * 60)

# ── 1. EDP Reduction Rate ─────────────────────────────────────
cursor.execute("SELECT COUNT(*) FROM gps_raw WHERE vehicle_id = 1")
raw_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM gps_matched WHERE vehicle_id = 1")
matched_count = cursor.fetchone()[0]

if raw_count > 0:
    reduction = ((raw_count - matched_count) / raw_count) * 100
    print(f"\n1. EDP NOISE REDUCTION")
    print(f"   Raw GPS points:     {raw_count}")
    print(f"   After EDP + match:  {matched_count}")
    print(f"   Noise reduced:      {reduction:.1f}%")

# ── 2. False Positive Rate ────────────────────────────────────
cursor.execute("""
    SELECT status, COUNT(*) 
    FROM stoppages 
    WHERE vehicle_id = 1
    GROUP BY status
""")
rows = cursor.fetchall()
status_counts = {row[0]: row[1] for row in rows}

suspected = status_counts.get('SUSPECTED', 0)
confirmed = status_counts.get('CONFIRMED', 0)
false_alarm = status_counts.get('FALSE_ALARM', 0)
total = suspected + confirmed + false_alarm

print(f"\n2. FALSE POSITIVE RATE (Layer 1 vs Layer 2)")
print(f"   Layer 1 suspected:  {suspected}")
print(f"   Layer 2 confirmed:  {confirmed}")
print(f"   False alarms:       {false_alarm}")
if suspected + confirmed > 0:
    naive_fp = suspected / (suspected + confirmed) * 100 if (suspected + confirmed) > 0 else 0
    print(f"   Naive detection false positive rate: {naive_fp:.1f}%")

# ── 3. Trip Statistics ────────────────────────────────────────
cursor.execute("""
    SELECT total_distance_m, stoppage_count, 
           EXTRACT(EPOCH FROM (ended_at - started_at)) as duration_s
    FROM trips 
    WHERE vehicle_id = 1
    ORDER BY started_at DESC
    LIMIT 1
""")
trip = cursor.fetchone()
if trip:
    dist, stops, duration = trip
    print(f"\n3. TRIP STATISTICS")
    print(f"   Total distance:     {dist/1000:.2f} km")
    print(f"   Stoppages detected: {stops}")
    if duration:
        print(f"   Trip duration:      {duration/3600:.1f} hours")

# ── 4. GiST Index Performance ─────────────────────────────────
print(f"\n4. SPATIAL QUERY PERFORMANCE (GiST index)")

# Without index hint — full scan simulation
start = time.time()
cursor.execute("""
    SELECT id, ST_AsText(location), started_at
    FROM stoppages
    WHERE ST_DWithin(
        location::geography,
        ST_SetSRID(ST_Point(77.5437, 12.9086), 4326)::geography,
        1000
    )
""")
results = cursor.fetchall()
end = time.time()
query_time_ms = (end - start) * 1000

print(f"   ST_DWithin query:   {query_time_ms:.2f}ms")
print(f"   Results found:      {len(results)} stoppages within 1km")

# ── 5. Redis Cache Stats ──────────────────────────────────────
try:
    import redis
    import os
    from dotenv import load_dotenv
    load_dotenv()

    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    info = r.info("stats")
    hits = info.get("keyspace_hits", 0)
    misses = info.get("keyspace_misses", 0)
    total_ops = hits + misses

    print(f"\n5. REDIS CACHE STATISTICS")
    print(f"   Cache hits:         {hits}")
    print(f"   Cache misses:       {misses}")
    if total_ops > 0:
        hit_rate = (hits / total_ops) * 100
        print(f"   Hit rate:           {hit_rate:.1f}%")

    # Count Valhalla cache keys
    valhalla_keys = len(r.keys("valhalla:*"))
    print(f"   Valhalla cached:    {valhalla_keys} route segments")

except Exception as e:
    print(f"\n5. REDIS — could not connect: {e}")

# ── 6. Database Row Counts ────────────────────────────────────
print(f"\n6. DATABASE SUMMARY")
for table in ['gps_raw', 'gps_matched', 'stoppages', 'trips', 'vehicles']:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"   {table:<20} {count} rows")

print("\n" + "=" * 60)
print("RESUME-READY NUMBERS:")
print("=" * 60)
if raw_count > 0 and matched_count > 0:
    print(f"✓ EDP reduces {raw_count} raw GPS points to {matched_count} significant points ({reduction:.0f}% noise reduction)")
print(f"✓ Detected {confirmed} confirmed stoppages on real Bengaluru GPS data")
if trip:
    print(f"✓ {dist/1000:.1f}km trip processed end-to-end via Valhalla road network")
print(f"✓ ST_DWithin spatial query: {query_time_ms:.1f}ms with PostGIS GiST index")
print("=" * 60)


cursor.execute("""
    SELECT 
        MIN(duration_seconds) as min_dur,
        MAX(duration_seconds) as max_dur,
        AVG(duration_seconds) as avg_dur,
        COUNT(*) FILTER (WHERE duration_seconds < 60) as under_1min,
        COUNT(*) FILTER (WHERE duration_seconds >= 60 AND duration_seconds < 300) as one_to_5min,
        COUNT(*) FILTER (WHERE duration_seconds >= 300) as over_5min
    FROM stoppages
    WHERE vehicle_id = 1 AND status = 'CONFIRMED'
""")
row = cursor.fetchone()
print(f"\n7. STOPPAGE DURATION BREAKDOWN")
print(f"   Min duration:    {row[0]}s")
print(f"   Max duration:    {row[1]}s")  
print(f"   Avg duration:    {row[2]:.0f}s")
print(f"   Under 1 minute:  {row[3]}")
print(f"   1-5 minutes:     {row[4]}")
print(f"   Over 5 minutes:  {row[5]}")

cursor.close()
conn.close()
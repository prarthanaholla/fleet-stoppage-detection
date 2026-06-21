import psycopg2
import datetime

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)

cursor = conn.cursor()

# Get a real vehicle_id
cursor.execute("""
SELECT id FROM vehicles WHERE name = %s;
""", ("Truck A",))
vehicle_id = cursor.fetchone()[0]

# Insert a NEARBY stoppage (~a few hundred metres from original point)
cursor.execute("""
INSERT INTO stoppages (vehicle_id, location, started_at, status)
VALUES (%s, ST_SetSRID(ST_Point(%s, %s), 4326), %s, %s);
""",
(
    vehicle_id,
    77.5980,
    12.9740,
    datetime.datetime.now(),
    "ACTIVE"
))

# Insert a FAR AWAY stoppage (Chennai)
cursor.execute("""
INSERT INTO stoppages (vehicle_id, location, started_at, status)
VALUES (%s, ST_SetSRID(ST_Point(%s, %s), 4326), %s, %s);
""",
(
    vehicle_id,
    80.2707,
    13.0827,
    datetime.datetime.now(),
    "ACTIVE"
))

conn.commit()

# Run the ST_DWithin query — find stoppages within 500m of original point
cursor.execute("""
SELECT id, ST_AsText(location), started_at
FROM stoppages
WHERE ST_DWithin(
    location::geography,
    ST_SetSRID(ST_Point(%s, %s), 4326)::geography,
    %s
);
""",
(
    77.5946,
    12.9716,
    500
))

rows = cursor.fetchall()

print("\nStoppages within 500m:")
for row in rows:
    print(row)

cursor.close()
conn.close()
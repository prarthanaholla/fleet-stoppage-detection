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

# Create trips table
cursor.execute("""
CREATE TABLE IF NOT EXISTS trips (
    id SERIAL PRIMARY KEY,

    vehicle_id INTEGER NOT NULL
    REFERENCES vehicles(id),

    started_at TIMESTAMP NOT NULL,

    ended_at TIMESTAMP,

    total_distance_m DOUBLE PRECISION NOT NULL DEFAULT 0,

    stoppage_count INTEGER NOT NULL DEFAULT 0
);
""")

conn.commit()

# Get vehicle id
cursor.execute("""
SELECT id
FROM vehicles
WHERE name = %s;
""", ("Truck A",))

vehicle_id = cursor.fetchone()[0]

# Insert trip
cursor.execute("""
INSERT INTO trips (
    vehicle_id,
    started_at
    
)
VALUES (%s, %s);
""",
(
    vehicle_id,
    datetime.datetime.now()
))

conn.commit()

# Fetch trips
cursor.execute("""
SELECT *
FROM trips;
""")

rows = cursor.fetchall()

print("\nTrips Table:")

for row in rows:
    print(row)

cursor.close()
conn.close()
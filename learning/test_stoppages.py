import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="fleetdb",
    user="postgres",
    password="password"
)

cursor = conn.cursor()

# Enable PostGIS
cursor.execute("""
CREATE EXTENSION IF NOT EXISTS postgis;
""")

# Create stoppages table
cursor.execute("""
CREATE TABLE IF NOT EXISTS stoppages (
    id SERIAL PRIMARY KEY,

    vehicle_id INTEGER NOT NULL
    REFERENCES vehicles(id),

    location GEOMETRY(Point, 4326) NOT NULL,

    started_at TIMESTAMP NOT NULL,

    ended_at TIMESTAMP,

    status VARCHAR(20) NOT NULL
    CHECK (status IN ('ACTIVE', 'ENDED'))
);
""")


# Insert
cursor.execute("""
INSERT INTO stoppages (
    vehicle_id,
    location,
    started_at,
    ended_at,
    status
)
VALUES (
    %s,
    ST_SetSRID(ST_Point(%s, %s), 4326),
    %s,
    %s,
    %s
);
""",
(
    1,
    77.5946,
    12.9716,
    "2026-06-18 10:00:00",
    None,
    "ACTIVE"
))

conn.commit()

# Fetch
cursor.execute("""
SELECT
    id,
    vehicle_id,
    ST_AsText(location),
    started_at,
    ended_at,
    status
FROM stoppages;
""")

rows = cursor.fetchall()

for row in rows:
    print(row)

print("stoppages table created")

cursor.close()
conn.close()